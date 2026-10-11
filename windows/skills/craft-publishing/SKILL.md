---
name: craft-publishing
description: Control PdfCraft PDF workflows and DesignCraft page layout locally, with page inspection, preview, native save and export.
---

PdfCraft 用于 PDF 阅读、页面组织、拆分合并、编辑和输出；DesignCraft 用于页面排版、文本框、图片框、样式和出版导出。

PdfCraft 的桌面控制协议与其他 Craft 应用不同。插件通过私有控制文件取得随机端口和 token。craft_inspect 返回 ui.state，craft_list_commands 返回 ui.commands，craft_command 只能传命令 id。需要文件参数时用 craft_control 的 ui.open {path}；输入和对话框通过其 ui.* 方法。批量 PDF 处理用独立 MCP 的 task tools，先 craft_engine_tools 再按 schema 调用。原生 pdfcraft-cli mcp 没有 --connect 模式；不要写这样的配置。

PdfCraft PDF 预览页码通常从 1 开始，DesignCraft render_page 等索引从 0 开始。每次以工具 schema 为准。DesignCraft 文本位置是 UTF-8 字节偏移，不是字符计数；中文字符通常占 3 字节。排版前读取页面、spread、story 和 frame id，编辑后检查溢出文本和页面预览。

输出到明确的新文件；工程保存和 PDF/图片导出分别验证。数字签名验证、OCR、加密、PDF/A 等只在当前目录确实存在该功能时使用，不从产品定位推断它们可用。具体 UI 方法见 [协议说明](../../references/protocols.md)。
