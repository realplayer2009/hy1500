#!/bin/bash
# 把同一套程序(APK)与设定(app.ini)克隆到多台 PA0715-N 面板。
#
# 背景: 现场要连续部署 18 台面板, 每台都要装指定版本的程序并套用同一套
# 现场设定(主题/外扩输入映射/加热器输出对/温控参数/串口参数)。手工一台一台
# 做容易漏配置或漏改属主, 因此固化成脚本。
#
# 用法:
#   scripts/clone_panel.sh 192.168.0.40                     # 单台
#   scripts/clone_panel.sh 192.168.0.40:5555                # 带端口
#   scripts/clone_panel.sh -f panels.txt                    # 批量(每行一个, # 注释)
#   scripts/clone_panel.sh -f panels.txt --no-config        # 只装程序不动配置
#   scripts/clone_panel.sh -f panels.txt --dry-run          # 只查在线状态
#   scripts/clone_panel.sh -f panels.txt --replace          # 签名不同时走换签名流程
#
# 部署包位置: 默认 ~/panel_deploy, 可用环境变量 PANEL_DEPLOY_DIR 覆盖。
#   ~/panel_deploy/RS485Control-arm64-v8a-debug.apk   程序
#   ~/panel_deploy/app.ini                            设定模板
#
# 每台的处理顺序(顺序是必须的, 见下方"属主"说明):
#   连接 → 停应用 → 装 APK → 校验 → 启动一次让应用自建数据目录 → 再停
#   → 备份旧配置 → 推入模板配置 → chown 回应用 uid → 启动 → 读回校验
#
# 保留与备份:
#   - 安装用 install -r, 不动面板上的 data/logs 历史数据
#   - 覆盖配置前先把旧配置备份成 app.ini.bak-<时间戳> 留在面板上
#
set -u

PKG="com.rs485.control"
ACT="com.rs485.control/.MainActivity"
CFG_REMOTE="/data/data/${PKG}/files/config/app.ini"
DEPLOY_DIR="${PANEL_DEPLOY_DIR:-$HOME/panel_deploy}"
APK="${DEPLOY_DIR}/RS485Control-arm64-v8a-debug.apk"
TPL="${DEPLOY_DIR}/app.ini"
DEFAULT_PORT="5555"

PUSH_CONFIG=1
DRY_RUN=0
REPLACE_SIG=0
LIST_FILE=""
declare -a TARGETS=()

die() { printf '\033[31m错误: %s\033[0m\n' "$*" >&2; exit 2; }
info() { printf '%s\n' "$*"; }
ok()   { printf '\033[32m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
bad()  { printf '\033[31m%s\033[0m\n' "$*"; }

# ── 参数解析 ───────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        -f|--file)
            [ $# -ge 2 ] || die "-f 需要跟一个文件名"
            LIST_FILE="$2"; shift 2 ;;
        --no-config) PUSH_CONFIG=0; shift ;;
        --replace)   REPLACE_SIG=1; shift ;;
        --dry-run)   DRY_RUN=1; shift ;;
        -h|--help)   sed -n '2,30p' "$0"; exit 0 ;;
        -*)          die "未知选项: $1 (用 -h 看用法)" ;;
        *)           TARGETS+=("$1"); shift ;;
    esac
done

if [ -n "$LIST_FILE" ]; then
    [ -r "$LIST_FILE" ] || die "读不到列表文件: $LIST_FILE"
    while IFS= read -r line; do
        line="${line%%#*}"                       # 去注释
        line="$(printf '%s' "$line" | tr -d '[:space:]')"
        [ -n "$line" ] && TARGETS+=("$line")
    done < "$LIST_FILE"
fi

[ ${#TARGETS[@]} -gt 0 ] || die "没有目标面板。用法: $0 <IP[:端口]> | -f <列表文件>"

# ── 找 adb ─────────────────────────────────────────────────────────────
find_adb() {
    if command -v adb >/dev/null 2>&1; then command -v adb; return; fi
    for c in /opt/homebrew/bin/adb "$HOME/Library/Android/sdk/platform-tools/adb" \
             /usr/local/bin/adb /usr/bin/adb; do
        [ -x "$c" ] && { printf '%s' "$c"; return; }
    done
    return 1
}
ADB="$(find_adb)" || die "找不到 adb, 请先安装 Android platform-tools"

[ -s "$APK" ] || die "找不到 APK: $APK (设 PANEL_DEPLOY_DIR 指定部署包目录)"
if [ "$PUSH_CONFIG" = 1 ]; then
    [ -s "$TPL" ] || die "找不到配置模板: $TPL"
fi

# 统一成 host:port 形式
normalize() {
    case "$1" in
        *:*) printf '%s' "$1" ;;
        *)   printf '%s:%s' "$1" "$DEFAULT_PORT" ;;
    esac
}

# 在面板上以 root 执行; $2 为要执行的命令
# 在面板上以 root 执行; $2 为要执行的命令。
# 必须经 sh -c: 这块板子的 su 是直接 execvp、不过 shell, 管道/glob/重定向
# 全都不生效。第一版把 "dd ... | od" 整个交给 su, dd 就把 "|" 当成文件名去读,
# ELF 校验永远读到空, 误报"库损坏"; glob 也一样不展开, 报 No such file or directory。
as_root() { "$ADB" -s "$1" shell "su 0 sh -c \"$2\"" 2>/dev/null | tr -d '\r'; }

# 等面板可达, 给若干次重试。面板常被现场人员搬动/重启, 一次性连不上很常见。
wait_reachable() {
    local dev="$1" i
    for i in 1 2 3; do
        "$ADB" connect "$dev" >/dev/null 2>&1
        if [ "$("$ADB" -s "$dev" get-state 2>/dev/null | tr -d '\r')" = "device" ]; then
            return 0
        fi
        sleep 2
    done
    return 1
}

# ── 换签名(面板上已装应用与我们要装的 APK 签名不同) ───────────────────
# install -r 遇到签名不同必然失败(INSTALL_FAILED_UPDATE_INCOMPATIBLE):
# Android 拒绝不同签名覆盖, 没有第二条路。而设备所有者应用连卸载都被禁
# (DELETE_FAILED_INTERNAL_ERROR), 必须先解除设备所有者。
#
# 本函数做"不丢数据换签名": 整包备份 -> 解除设备所有者 -> 重启 -> 卸载 ->
# 装新包 -> 启动一次自建目录 -> 还原历史数据 -> 恢复装机状态。
# 配置不在这里还原, 交给主流程推模板(那才是要克隆的设定)。
#
# 注意: 中间要重启面板。重启后若段上没有 DHCP, 面板会拿不到 IP 就此失联,
# 只能人工 adb connect 后续跑 —— 所以这一步前最好确认网络是通的。
replace_signed() {
    local dev="$1" stamp bk n f uid gid
    stamp="$(date +%Y%m%d-%H%M%S)"
    bk="$DEPLOY_DIR/backup-$stamp"
    mkdir -p "$bk"

    # 1. 整包备份 files 目录(历史数据 + 配置 + assets)
    info "  备份面板数据到 $bk ..."
    if ! "$ADB" -s "$dev" shell "su 0 tar -C /data/data/$PKG/files -cf - . 2>/dev/null" \
         | tar -xf - -C "$bk" 2>/dev/null || [ ! -d "$bk" ]; then
        bad "  ✗ 备份失败, 中止换签名(不冒丢数据的风险)"
        return 1
    fi
    n="$(find "$bk" -type f 2>/dev/null | wc -l | tr -d ' ')"
    info "  已备份 $n 个文件"

    # 2. 备份并解除设备所有者注册。设备所有者状态在
    #    /data/system/device_owner_2.xml(Android 二进制 XML), 删掉再重启即解除;
    #    dpm remove-active-admin 要求应用声明 testOnly, 厂商签的包不满足, 走不通。
    for f in device_owner_2.xml device_policies.xml device_policies_version; do
        "$ADB" -s "$dev" shell "su 0 base64 /data/system/$f" 2>/dev/null \
            | tr -d '\r\n' > "$bk/$f.b64"
    done
    info "  解除设备所有者(注册文件已备份)..."
    "$ADB" -s "$dev" shell \
        "su 0 sh -c 'rm -f /data/system/device_owner_2.xml /data/system/device_policies.xml'" \
        >/dev/null 2>&1

    # 3. 重启后才卸得掉
    info "  重启面板..."
    "$ADB" -s "$dev" reboot >/dev/null 2>&1
    "$ADB" -s "$dev" wait-for-device >/dev/null 2>&1
    sleep 20
    if ! wait_reachable "$dev"; then
        bad "  ✗ 重启后连不上(段上没有 DHCP 就会这样), 请人工 adb connect 后重跑本脚本"
        return 1
    fi
    ok "  ✓ 重启后已连上"

    # 4. 卸载旧签名包 + 装新包
    info "  卸载旧签名包..."
    "$ADB" -s "$dev" uninstall "$PKG" 2>&1 | tr -d '\r'
    info "  安装新包..."
    if ! "$ADB" -s "$dev" install --no-streaming -r "$APK" >/tmp/_clone_install2.log 2>&1; then
        bad "  ✗ 换签名后仍装不上:"
        sed 's/^/      /' /tmp/_clone_install2.log
        return 1
    fi
    ok "  ✓ 新包装好"

    # 5. 启动一次让应用自建 files/data/logs, 再还原历史数据。
    #    顺序不能反: 没启动过就没有那个目录, tar 解不开。
    as_root "$dev" "am start -n $ACT" >/dev/null; sleep 5
    as_root "$dev" "am force-stop $PKG" >/dev/null
    if [ -d "$bk/data/logs" ] && [ -n "$(ls -A "$bk/data/logs" 2>/dev/null)" ]; then
        info "  还原历史数据..."
        (cd "$bk" && tar -cf /tmp/_clone_logs.tar data 2>/dev/null)
        "$ADB" -s "$dev" push /tmp/_clone_logs.tar /data/local/tmp/ >/dev/null 2>&1
        as_root "$dev" \
            "cd /data/data/$PKG/files && tar -xf /data/local/tmp/_clone_logs.tar && rm -f /data/local/tmp/_clone_logs.tar" \
            >/dev/null 2>&1
        rm -f /tmp/_clone_logs.tar
    fi

    # 6. 属主改回应用 uid
    uid="$(as_root "$dev" "stat -c '%u' /data/data/$PKG")"
    gid="$(as_root "$dev" "stat -c '%g' /data/data/$PKG")"
    if [ -n "$uid" ] && [ -n "$gid" ]; then
        as_root "$dev" "chown -R ${uid}:${gid} /data/data/$PKG/files" >/dev/null
        as_root "$dev" "chmod 600 /data/data/$PKG/files/data/logs/*" >/dev/null 2>&1
        # 清掉 macOS AppleDouble 垃圾(._开头)。这些是装机方早前用 Mac 侧
        # 工具还原数据留下的(实测一台面板上有 3 个, 共 163 字节/个), 普通
        # ls 不带 -a 根本看不见。其中 ._YYYY-MM-DD.csv 后缀是 .csv, 虽然
        # 当前应用只匹配合法日期格式不一定被干扰, 但没理由留着。
        as_root "$dev" "find /data/data/$PKG/files -name '._*' -delete" >/dev/null 2>&1
        ok "  ✓ 历史数据已还原, 属主=$uid:$gid"
    else
        warn "  ! 取不到应用 uid, 数据属主可能不对"
    fi

    # 7. 恢复装机状态(刚才删了注册文件, 必须补回来)
    info "  恢复设备所有者与开机自启..."
    "$ADB" -s "$dev" shell "dpm set-device-owner --user 0 $PKG/.KioskAdminReceiver" >/dev/null 2>&1
    "$ADB" -s "$dev" shell "dpm set-active-admin --user 0 $PKG/.KioskAdminReceiver" >/dev/null 2>&1
    "$ADB" -s "$dev" shell "cmd package set-home-activity --user 0 $PKG/.MainActivity" >/dev/null 2>&1
    "$ADB" -s "$dev" shell "settings put system xzjh_auto_boot_package_name $PKG" >/dev/null 2>&1
    "$ADB" -s "$dev" shell "settings put system xzjh_daemon_package_name $PKG" >/dev/null 2>&1
    ok "  ✓ 换签名完成(备份留在 $bk, 确认无误后可删)"
    return 0
}

# ── 单台处理 ───────────────────────────────────────────────────────────
OK_COUNT=0; FAIL_COUNT=0; SKIP_COUNT=0
declare -a FAILED_LIST=()

clone_one() {
    local raw="$1"
    local dev; dev="$(normalize "$raw")"
    printf '\n\033[1m══════ %s ══════\033[0m\n' "$dev"

    if ! wait_reachable "$dev"; then
        bad "  ✗ 连不上(已重试 3 次), 跳过这台"
        FAIL_COUNT=$((FAIL_COUNT+1)); FAILED_LIST+=("$dev (连不上)")
        return 1
    fi
    ok "  ✓ 已连接"

    local model android
    model="$(as_root "$dev" getprop ro.product.model)"
    android="$(as_root "$dev" getprop ro.build.version.release)"
    info "  机型: ${model:-?} / Android ${android:-?}"

    if [ "$DRY_RUN" = 1 ]; then
        local installed
        installed="$("$ADB" -s "$dev" shell pm path "$PKG" 2>/dev/null | tr -d '\r' | head -1)"
        [ -n "$installed" ] && ok "  ✓ 已安装 $PKG" || warn "  ! 未安装 $PKG"
        SKIP_COUNT=$((SKIP_COUNT+1))
        return 0
    fi

    # 1. 停应用(必须在装之前: 运行中的进程会持着旧代码, 且稍后推配置时
    #    应用可能又把配置写回去, 把我们推的覆盖掉)
    as_root "$dev" "am force-stop $PKG" >/dev/null
    "$ADB" -s "$dev" shell am force-stop "$PKG" >/dev/null 2>&1

    # 2. 安装。--no-streaming: 流式安装在这个板子上出现过 .so 被写坏的情况
    #    (ELF magic 变成 00 00 00 00), 装完能启动但一调用 native 就崩。
    local before after
    before="$("$ADB" -s "$dev" shell dumpsys package "$PKG" 2>/dev/null | tr -d '\r' \
              | grep -E 'versionName|lastUpdateTime' | tr '\n' ' ')"
    info "  安装前: ${before:-未安装}"
    if ! "$ADB" -s "$dev" install --no-streaming -r "$APK" >/tmp/_clone_install.log 2>&1; then
        sed 's/^/      /' /tmp/_clone_install.log
        if grep -q 'UPDATE_INCOMPATIBLE' /tmp/_clone_install.log; then
            # 面板上已装的应用与我们的 APK 不是同一把 key 签的(现场见过:
            # 装机方用自己的 key 预装过一版)。install -r 覆盖不了, 且设备
            # 所有者应用连卸载都被禁, 只能走换签名流程。
            if [ "$REPLACE_SIG" = 1 ]; then
                if ! replace_signed "$dev"; then
                    FAIL_COUNT=$((FAIL_COUNT+1)); FAILED_LIST+=("$dev (换签名失败)")
                    return 1
                fi
                # 换签名已经装好新包了, 回到主流程补配置
            else
                bad "  ✗ 签名不匹配(INSTALL_FAILED_UPDATE_INCOMPATIBLE)"
                info "    面板上已装的是另一把 key 签的版本, 覆盖装不上。"
                info "    确认要换成我们的签名就加 --replace 重跑(会先备份数据、"
                info "    解除设备所有者、重启、卸载重装, 历史数据会还原)。"
                FAIL_COUNT=$((FAIL_COUNT+1)); FAILED_LIST+=("$dev (签名不匹配, 需 --replace)")
                return 1
            fi
        else
            bad "  ✗ 安装失败:"
            FAIL_COUNT=$((FAIL_COUNT+1)); FAILED_LIST+=("$dev (安装失败)")
            return 1
        fi
    fi
    grep -qi 'success' /tmp/_clone_install.log && ok "  ✓ 安装成功"
    after="$("$ADB" -s "$dev" shell dumpsys package "$PKG" 2>/dev/null | tr -d '\r' \
             | grep -E 'versionName|lastUpdateTime' | tr '\n' ' ')"
    info "  安装后: $after"

    # 3. 校验 native 库完整(防流式安装损坏)
    #    路径不靠 glob: su 0 不过 shell, glob 不展开(见 as_root 说明);
    #    从 dumpsys 的 legacyNativeLibraryDir 取, 该路径本身含 '=',
    #    所以用 's/^[^=]*=//' 而不是 's/.*=//' —— 后者贪婪匹配到最后一个 '=',
    #    只会剩下 '/lib'。
    local magic libdir
    libdir="$(as_root "$dev" "dumpsys package $PKG | grep legacyNativeLibraryDir | sed 's/^[^=]*=//'")"
    if [ -n "$libdir" ]; then
        magic="$(as_root "$dev" \
            "dd if=$libdir/arm64/libRS485Control_arm64-v8a.so bs=1 count=4 2>/dev/null | od -An -tx1" \
            | tr -d ' \n\r')"
    fi
    if [ "$magic" = "7f454c46" ]; then
        ok "  ✓ native 库 ELF magic 正常 (7f 45 4c 46)"
    else
        warn "  ! native 库校验异常 (读到 '${magic:-空}'), 若是 00000000 说明库损坏需重装"
    fi

    # 4. 启动一次让应用自建 files/config 目录。
    #    这一步是为了属主: 该目录由应用(以 app uid)创建, 属主天然正确;
    #    若由我们用 su 0 mkdir, 属主会是 root, 应用之后写不回 app.ini。
    as_root "$dev" "am start -n $ACT" >/dev/null
    sleep 5
    as_root "$dev" "am force-stop $PKG" >/dev/null

    if [ "$PUSH_CONFIG" = 0 ]; then
        warn "  --no-config: 跳过配置推送(保留面板现有设定)"
    else
        local cfgdir; cfgdir="$(dirname "$CFG_REMOTE")"
        as_root "$dev" "mkdir -p $cfgdir" >/dev/null

        # 5. 备份旧配置(可回收: 留 .bak-<时间戳> 在面板上, 不删)
        if [ -n "$(as_root "$dev" "ls $CFG_REMOTE" 2>/dev/null)" ]; then
            local bak="app.ini.bak-$(date +%Y%m%d-%H%M%S)"
            as_root "$dev" "cp $CFG_REMOTE $cfgdir/$bak" >/dev/null \
                && info "  旧配置已备份为 $bak"
        fi

        # 6. 推入模板配置
        "$ADB" -s "$dev" shell "su 0 cp /dev/null $CFG_REMOTE" >/dev/null 2>&1
        if ! "$ADB" -s "$dev" push "$TPL" "$CFG_REMOTE" >/tmp/_clone_push.log 2>&1; then
            # adb push 目标在 /data/data 下通常会被权限挡住; 走 tmp 再 su 0 mv
            warn "  直接 push 失败, 改走 /data/local/tmp 中转"
            "$ADB" -s "$dev" push "$TPL" /data/local/tmp/app.ini >/dev/null 2>&1 || {
                bad "  ✗ 推送配置失败"; sed 's/^/      /' /tmp/_clone_push.log
                FAIL_COUNT=$((FAIL_COUNT+1)); FAILED_LIST+=("$dev (推配置失败)")
                return 1
            }
            as_root "$dev" "cp /data/local/tmp/app.ini $CFG_REMOTE && rm -f /data/local/tmp/app.ini" >/dev/null
        fi

        # 7. 属主改回应用 uid —— 上面 su 0 cp 写进去的文件是 root:root,
        #    应用(以 app uid 运行)之后写不回 app.ini, 设定就再也存不住了。
        local uid gid
        uid="$(as_root "$dev" "stat -c '%u' /data/data/$PKG")"
        gid="$(as_root "$dev" "stat -c '%g' /data/data/$PKG")"
        if [ -n "$uid" ] && [ -n "$gid" ]; then
            as_root "$dev" "chown -R ${uid}:${gid} /data/data/$PKG/files" >/dev/null
            # 读回比对必须用数值(%u:%g)而不是名称(%U:%G): 名称形如 u0_a91,
            # 而 uid 是 10091, 拿名称和 "u0_a${uid}" 拼出来的是 u0_a10091,
            # 永远比不相等 —— 属主明明是对的也会误报。
            local owner
            owner="$(as_root "$dev" "stat -c '%u:%g' $CFG_REMOTE")"
            if [ "$owner" = "${uid}:${gid}" ]; then
                ok "  ✓ 配置属主已改为应用 uid ($uid:$gid)"
            else
                warn "  ! 属主改完读回是 '$owner' (期望 $uid:$gid), 请人工确认"
            fi
        else
            warn "  ! 取不到应用 uid, 跳过 chown —— 应用可能无法保存设定!"
        fi

        # 8. 读回校验: 把面板上的配置拉回来和模板逐字节比对
        "$ADB" -s "$dev" pull "$CFG_REMOTE" /tmp/_clone_readback.ini >/dev/null 2>&1 \
            || "$ADB" -s "$dev" shell "su 0 cat $CFG_REMOTE" > /tmp/_clone_readback.ini 2>/dev/null
        if cmp -s "$TPL" /tmp/_clone_readback.ini; then
            ok "  ✓ 配置读回与模板一致 ($(wc -l < "$TPL" | tr -d ' ') 行)"
        else
            warn "  ! 配置读回与模板有差异:"
            diff "$TPL" /tmp/_clone_readback.ini 2>/dev/null | sed 's/^/      /' | head -10
        fi
    fi

    # 9. 启动并确认进程活着
    as_root "$dev" "am start -n $ACT" >/dev/null
    sleep 4
    local pid
    pid="$(as_root "$dev" "pidof $PKG")"
    if [ -n "$pid" ]; then
        ok "  ✓ 应用已启动 (pid=$pid)"
    else
        bad "  ✗ 应用启动后没有进程, 请看 logcat"
        FAIL_COUNT=$((FAIL_COUNT+1)); FAILED_LIST+=("$dev (启动失败)")
        return 1
    fi

    ok "  ✓ $dev 克隆完成"
    OK_COUNT=$((OK_COUNT+1))
    return 0
}

for t in "${TARGETS[@]}"; do
    clone_one "$t"
done

# ── 汇总 ───────────────────────────────────────────────────────────────
printf '\n\033[1m══════ 汇总 ══════\033[0m\n'
info "  成功 ${OK_COUNT} 台 / 跳过(仅检查) ${SKIP_COUNT} 台 / 失败 ${FAIL_COUNT} 台"
if [ ${#FAILED_LIST[@]} -gt 0 ]; then
    printf '  未完成:\n'
    for f in "${FAILED_LIST[@]}"; do printf '    - %s\n' "$f"; done
    printf '\n  把没连上的 IP 存成列表文件再跑一遍即可, 例如:\n'
    printf '    printf "%%s\\n" 192.168.0.41 192.168.0.42 > ~/panel_deploy/retry.txt\n'
    printf '    scripts/clone_panel.sh -f ~/panel_deploy/retry.txt\n'
    exit 1
fi
ok "全部完成"
