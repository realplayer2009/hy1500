# 文档工程取舍

> 后续修改本组件的 agents 请继续维护本文档：有实际参数或工程权衡时记录，没有则不强行添加。

- 问题：说明书目录原“章节”列宽 2.5 cm，只放短编号，而操作入口需要较长的导航名称。解决方案选择：在总宽 16.8 cm 内，将操作、入口、节次列改为 6.0／9.3／1.5 cm。解释：压缩编号列给入口文字留出空间，保持操作名称和导航路径便于对照。

说明书源文件为 `客户使用说明书.md`。在项目根目录执行 `python3 scripts/build_customer_manual.py` 生成 Word 和三幅线条图，再执行 `libreoffice --headless --convert-to pdf --outdir docs docs/客户使用说明书.docx` 导出 PDF；需要 python-docx、Pillow 和 Noto Sans CJK 字体。更改后核对图号、节次及导出分页，三种格式同步交付。
