---
name: craft-office
description: Create and edit documents, spreadsheets and slides locally in WordCraft, GridCraft and DeckCraft using exact commands and visual previews.
---

用 WordCraft 编辑文字、段落、表格与文档；GridCraft 编辑单元格、公式、工作簿；DeckCraft 编辑幻灯片。先连接并 inspect，查询命令目录，再使用精确的参数。

WordCraft 桌面连接需要窗口密钥，插件在每次连接读取私有 key 文件。文字位置使用 story/path/off，off 是 UTF-8 字节偏移；不要按中文字符数直接填入。独立引擎可用 --author 标明 AI 编辑者；不要改变用户 GUI 的个人作者设置。

GridCraft 使用 sheet.read/cell.get 验证值和公式；通过 craft_control 调用这些读方法。craft_list_commands 查询 cell.set、range、file.save 等目标功能。公式值应来自软件重新计算，不能只看刚写入的公式字符串。截图检查版面，原生工程和 xlsx/CSV 导出分别按命令支持完成。

DeckCraft 先 inspect 当前 slides 和对象 id，再编辑文字、形状、图片、备注和顺序；布局后渲染代表页面并检查文本裁切。页/slide 索引和坐标单位以实时参数文档为准。

保留用户已授权的编辑范围，使用新文件名交付示例。插件跨进程会话不是实时协作锁，先读取当前选择，优先显式指定对象，避免依赖用户可能改变的选择。来源和控制方式见 [协议说明](../../references/protocols.md)。
