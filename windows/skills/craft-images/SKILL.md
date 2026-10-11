---
name: craft-images
description: Create and edit raster images in PhotoCraft or vector artwork in VectorCraft using local commands, previews and native file export.
---

用 PhotoCraft 做像素、图层、选区、蒙版和滤镜编辑；用 VectorCraft 做路径、形状、文字、画板和 SVG 编辑。通过 craft_status 确认软件可用，选择桌面会话或独立引擎会话，并在整个任务中保持一致。

桌面：craft_launch → craft_inspect → craft_list_commands（查询 open/new/place、图层/路径/文字、save/export 等目标功能）→ craft_command。每个命令的 id、参数和 enabled 必须来自当前命令目录。独立引擎：craft_engine_tools 发现精确工具 schema，craft_engine_call 执行；PhotoCraft 的 doc_new/doc_open/doc_save 和 VectorCraft 的 open_file/save_file 等名字以实时工具目录为准。

通过原生 render_preview 或 PNG 预览检查视觉结果；桌面窗口可用 craft_screenshot。工程保存和成品导出是两个不同步骤，按请求分别完成，返回真实文件路径。优先保留可编辑图层或矢量结构。不要假定 SVG 导出与原生工程保真度相同。

PhotoCraft 桌面的 file.open/file.save/file.saveAs/file.saveACopy 即使目录显示 enabled，也会被自动化权限拒绝；打开和保存必须用 craft_control 的 app.open {path}/app.save {path}，独立 MCP 用 doc_open/doc_save。PhotoCraft 需要 token-file；VectorCraft --connect 与独立引擎的 roots 参数不能混用。插件已封装认证差异，原生配置见 [协议说明](../../references/protocols.md)。保存到已有文件或压平/栅格化会影响可编辑性，遵循用户已授权的输出目标；例行预览使用新文件名。

多条命令批处理通常逐步执行、逐步记入撤销历史，并不保证原子回滚；遇到失败读取逐步结果并 inspect，避免整批重放。
