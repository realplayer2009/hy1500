#!/bin/bash
# 手册定稿：重出插图 -> 重出 docx -> 校验 -> 投递到 Documents
set -e
PY="/Users/han24-m5air/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3"
cd "/Users/han24-m5air/gitw/hy1500-1"

echo "== 1) 生成插图 =="
"$PY" docs/manual/make_figs.py | tail -2

echo "== 2) 构建 docx =="
"$PY" docs/manual/build_manual.py | tail -2

echo "== 3) 校验：不得残留安卓平台字样 =="
"$PY" docs/manual/dump_text.py > /tmp/manual_final.txt 2>/dev/null
BAD=$(grep -c -E "Android|ADB|Termux|termux-x11|开发者模式|唤醒锁" /tmp/manual_final.txt || true)
echo "android-ish hits: $BAD"

echo "== 4) 校验：OT/OUT 分工文案在文中 =="
grep -c "OT 与 OUT 的分工" /tmp/manual_final.txt || true

echo "== 5) 结构校验 =="
"$PY" "/Applications/DeepSeek Harness.app/Contents/Resources/runtime/office-skills/scripts/check_office.py" \
  "docs/manual/变压器加热系统-使用手册.docx" --out /tmp/final2.json --contains "变压器加热系统" >/dev/null 2>&1
echo "checker exit=$?"

echo "== 6) 投递 =="
cp -f "docs/manual/变压器加热系统-使用手册.docx" "/Users/han24-m5air/Documents/变压器加热系统-使用手册_v2.docx"
ls -l "docs/manual/变压器加热系统-使用手册.docx" "/Users/han24-m5air/Documents/变压器加热系统-使用手册_v2.docx"
shasum -a 256 "docs/manual/变压器加热系统-使用手册.docx" "/Users/han24-m5air/Documents/变压器加热系统-使用手册_v2.docx"
echo "ALL DONE"
