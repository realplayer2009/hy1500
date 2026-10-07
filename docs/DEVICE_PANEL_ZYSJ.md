# ZYSJ 固件屏安装与恢复

2026-10-05 已实装一台新屏，应用、导航锁、默认 HOME、厂商自启/守护、两阶段静态 Logo、宣传动画均已部署；重启后应用自动进入前台，锁定任务状态为 `LOCKED`。Logo/动画的显示效果仍以现场目视为准。

本页适用于已核对的这套固件：

- 型号 `rk3562_t`，Android 13 / API 33，屏幕 1024×600。
- `ro.system.build.fingerprint` 为 `rockchip/rk3562_t/rk3562_t:13/TQ2A.230305.008.F1/server0208230255:userdebug/release-keys`。
- 厂商服务为 `zysj`，工程设置为 `com.sz.zysj.settings`（系统 APK：`/system/priv-app/RxSettings/RxSettings2362K.apk`）。
- `ro.build.fingerprint` 被厂商设置成 Google Android 9 的值，不能用它判断真实版本。

它与原批次的 `xzjh` 固件不同：不存在 `/dev/block/by-name/logo`，不能调用原指南的 `service call xzjh 117`，也不能靠写入 `xzjh_*` 设置项配置厂商自启。其他固件需重新核对接口，不能只按型号选择流程。

下列命令使用 Linux Bash；安装电脑需要 ADB 和 Python 3，Logo 生成脚本只用 Python 标准库，屏内无需安装工具。

## 连接与应用安装

按[批量安装指南](批量安装指南.md)现场发现地址，将变量设成当前屏的地址：

```bash
d='<当前屏IP:端口>'
adb connect "$d"
adb -s "$d" install --no-streaming -r android/dist/RS485Control-arm64-v8a-debug.apk
# 新屏首次设置；更新已经配置好的屏不重复 set-device-owner
adb -s "$d" shell dpm set-device-owner --user 0 com.rs485.control/.KioskAdminReceiver
adb -s "$d" shell dpm set-active-admin --user 0 com.rs485.control/.KioskAdminReceiver
adb -s "$d" shell cmd package set-home-activity --user 0 com.rs485.control/.MainActivity
adb -s "$d" shell cmd role add-role-holder --user 0 android.app.role.HOME com.rs485.control
adb -s "$d" shell am start -W -n com.rs485.control/.MainActivity
```

默认桌面需通过系统“默认主屏幕应用”页面确认 RS485Control 已选中（入口为 `adb -s "$d" shell am start -W -a android.settings.HOME_SETTINGS`，先按下文进入维护模式）。仅看到开机自动启动应用不能证明默认桌面设置正确。本次已在暂停厂商守护时从该页面按 Home，直接返回 RS485Control；完成后恢复导航锁与守护。

## 厂商自启与守护

厂商工程设置中的“开机启动应用”实际写入其默认 SharedPreferences 的字符串 `boot_app_key=com.rs485.control`；BOOT_COMPLETED 接收器从这里读取。该文件是 `/data/user/0/com.sz.zysj.settings/shared_prefs/com.sz.zysj.settings_preferences.xml`，不能直接用同名 `settings put` 代替。

本次用 root 备份原 XML，停止厂商设置应用后保留其他条目，仅增加/更新以下条目；通过同目录临时文件替换，保持所有者 `1000:1000`、权限 `660` 和 SELinux 类型 `system_app_data_file`。随后打开一次厂商设置，使其退出 force-stop 状态，再恢复控制应用导航锁。

```xml
<string name="boot_app_key">com.rs485.control</string>
<string name="app_keep_alive_packagename_key">com.rs485.control</string>
<string name="modify_app_keep_alive_packagename_key">com.rs485.control</string>
<boolean name="modify_app_keep_alive_switch_key" value="true" />
```

也可在维护模式中通过厂商设置界面选“开机启动应用”和“应用保活”，应用均选择 RS485Control。守护实际调用 `ZysjSystemManager.keepAlive(int, String, String)`；事务号从这台 **系统 framework** 的 `IZysjSystemService$Stub` 核对为十进制 **72**，默认周期为 **10000 ms**。第三个字符串在本固件实现中被忽略：

```bash
adb -s "$d" root
sleep 2
adb connect "$d"
adb -s "$d" shell 'service call zysj 72 i32 10000 s16 com.rs485.control s16 ""'
```

接口返回 `Parcel(00000000 00000000)`。它保存 `application_daemon_class=com.rs485.control` 和 `process_daemon_time=10000`，并发出 START_KEEP_LIVE_ACTION 启动厂商守护。本次重启后两项仍保留，启动日志再次出现该动作；不是只保存了一个无效设置项。

需要进入设置维护时先停止守护，避免维护页面被定时拉回控制软件：

```bash
adb -s "$d" shell 'service call zysj 72 i32 0 s16 com.rs485.control s16 ""'
adb -s "$d" shell am broadcast -a com.rs485.control.MAINTENANCE -n com.rs485.control/.KioskMaintenanceReceiver --ez enabled true
adb -s "$d" shell am start -n com.sz.zysj.settings/.SettingsActivity
# 维护完成
adb -s "$d" shell am broadcast -a com.rs485.control.MAINTENANCE -n com.rs485.control/.KioskMaintenanceReceiver --ez enabled false
adb -s "$d" shell am start -W -n com.rs485.control/.MainActivity
adb -s "$d" shell 'service call zysj 72 i32 10000 s16 com.rs485.control s16 ""'
```

## 静态 Logo

两阶段图像在 Android v2 boot 的 second 段内，使用 Rockchip RSCE 资源表的 `logo.bmp` 和 `logo_kernel.bmp`；本屏原图为 1920×1080 的 8 位 BMP，品牌资源为适配物理屏的 1024×600、8 位 BMP。

每台屏先备份自己的 boot，不能将本次生成的完整 boot 用来刷其他屏。本次设备备份为 `/data/local/tmp/rs485-boot.factory.img`，本机独立备份目录为 `android/dist/device-backup/zysj-20261005-1729/`（被 Git 忽略、不打入通用安装包）。

```bash
adb -s "$d" shell 'set -e; if [ ! -e /data/local/tmp/rs485-boot.factory.img ]; then dd if=/dev/block/by-name/boot of=/data/local/tmp/rs485-boot.factory.img.new bs=1M; mv /data/local/tmp/rs485-boot.factory.img.new /data/local/tmp/rs485-boot.factory.img; fi'
# 从本屏拉取到它自己的本机备份目录，以下相对路径仅为示例
adb -s "$d" pull /data/local/tmp/rs485-boot.factory.img boot.factory.img
python3 scripts/patch_rockchip_boot_logos.py boot.factory.img assets/boot_logo.bmp boot.brand.img
adb -s "$d" push boot.brand.img /data/local/tmp/rs485-boot.brand.img
# 核对本机与上传文件 SHA256 一致后，写入本屏
sha256sum boot.brand.img
adb -s "$d" shell sha256sum /data/local/tmp/rs485-boot.brand.img
adb -s "$d" shell 'dd if=/data/local/tmp/rs485-boot.brand.img of=/dev/block/by-name/boot bs=1M && sync'
```

[生成脚本](../scripts/patch_rockchip_boot_logos.py)只处理无 recovery_dtbo、无 AVB footer 的 v2 boot 副本，不操作设备。它校验原镜像 SHA1、全部资源哈希、资源边界及重叠，只在新图不超过原图大小时替换两张图；其余空间填零，更新资源哈希/长度和 boot SHA1，保持资源偏移、镜像长度、内核、ramdisk、设备树及其他内容。已有输出文件不会覆盖。本屏启动状态为 `orange`、`ro.boot.flash.locked=0`；其他启动安全状态需另行处理。

资源表格式依据 [Rockchip 官方 resource_tool.c](https://github.com/rockchip-linux/u-boot/blob/next-dev/tools/rockchip/resource_tool.c)。本次可重复生成的镜像与实际写入镜像一致，重启后的 boot SHA256 为 `099274277da1ecc34c9cb7f265a3bcfe1246672f3df9e631f913651f7937856e`。

恢复静态 Logo 时只恢复本屏自己的备份：

```bash
adb -s "$d" root
sleep 2
adb connect "$d"
adb -s "$d" shell 'dd if=/data/local/tmp/rs485-boot.factory.img of=/dev/block/by-name/boot bs=1M && sync'
adb -s "$d" reboot
```

## 动画与完成

本次 root 后 `adb remount` 直接成功，无需首次 overlayfs 重启分支；以后仍按 remount 实际提示处理。本固件播放器支持多种路径，已确认本屏没有更高优先级的 product/oem 动画和 system mp4/ts，因此部署至 `/system/media/bootanimation.zip`。厂商设置中的旋转操作会用 `bootanimation_0/90/180/270.zip` 重新覆盖此文件；更改系统旋转后需重新部署品牌动画。

```bash
adb -s "$d" remount
adb -s "$d" shell 'set -e; if [ ! -e /system/media/bootanimation.zip.orig.bak ]; then cp -p /system/media/bootanimation.zip /system/media/bootanimation.zip.orig.bak; fi'
adb -s "$d" push android/dist/bootanimation.zip /data/local/tmp/rs485-bootanimation.zip
adb -s "$d" shell 'set -e; cp /data/local/tmp/rs485-bootanimation.zip /system/media/bootanimation.zip.new; chown root:root /system/media/bootanimation.zip.new; chmod 644 /system/media/bootanimation.zip.new; chcon u:object_r:system_file:s0 /system/media/bootanimation.zip.new; mv /system/media/bootanimation.zip.new /system/media/bootanimation.zip; sync'
adb -s "$d" reboot
```

重启后自动进入控制界面。恢复动画仍按批量指南从本屏的 `/system/media/bootanimation.zip.orig.bak` 恢复。厂商设置原始 XML 另有设备备份 `/data/local/tmp/rs485-zysj-settings.factory.xml`；恢复时先停止厂商设置应用，以原文件替换并保持上述权限/SELinux 类型，再打开厂商设置应用，避免内存旧值覆盖文件。
