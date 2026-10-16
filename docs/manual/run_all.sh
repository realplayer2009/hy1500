#!/bin/bash
# 一键完成：修正蜂鸣器口径 → 重画插图 → 重建 docx → 校验 → 投递
set -e
PY="/Users/han24-m5air/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3"
cd "/Users/han24-m5air/gitw/hy1500-1"

echo "===== 1) 运行蜂鸣器口径修正 ====="
bash docs/manual/fix_buzzer.sh 2>&1 | tail -20

echo "===== 2) 重画插图 ====="
"$PY" docs/manual/make_figs.py 2>&1 | tail -2

echo "===== 3) 重建 docx ====="
"$PY" docs/manual/build_manual.py 2>&1 | tail -2

echo "===== 4) 全文校验 ====="
"$PY" docs/manual/dump_text.py > /tmp/m.txt 2>/dev/null
echo "-- 残留安卓字样: $(grep -c -E 'Android|ADB|Termux|termux-x11|开发者模式|唤醒锁' /tmp/m.txt || true)"
echo "-- OUT5 提示音口径: $(grep -c 'OUT5 操作确认音输出' /tmp/m.txt || true)"
echo "-- OT10 现场接线: $(grep -c '现场唯一接线的蜂鸣器' /tmp/m.txt || true)"
echo "-- 误留旧措辞: $(grep -c 'OUT5 操作提示蜂鸣器' /tmp/m.txt || true)"

echo "===== 5) 结构校验 ====="
"$PY" "/Applications/DeepSeek Harness.app/Contents/Resources/runtime/office-skills/scripts/check_office.py" \
  "docs/manual/变压器加热系统-使用手册.docx" --out /tmp/final3.json --contains "变压器加热系统" >/dev/null 2>&1
echo "checker exit=$?"

echo "===== 6) 投递到文档目录 ====="
cp -f "docs/manual/变压器加热系统-使用手册.docx" "/Users/han24-m5air/Documents/变压器加热系统-使用手册_v2.docx"
ls -l "docs/manual/变压器加热系统-使用手册.docx" "/Users/han24-m5air/Documents/变压器加热系统-使用手册_v2.docx"
shasum -a 256 "docs/manual/变压器加热系统-使用手册.docx" "/Users/han24-m5air/Documents/变压器加热系统-使用手册_v2.docx"

echo "ALL DONE"
