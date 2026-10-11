---
name: craft-audio-cad
description: Edit local SoundCraft audio sessions or CADCraft drawings with discovered commands, document inspection and export.
---

SoundCraft 用于音轨、混音、路由和音频输出；CADCraft 用于绘图、图层、几何和 DXF 等输出。此插件有源码核对的连接适配，但不保证用户安装了这两款软件；先 craft_status 检查，缺失时清楚说明并按任务安装官方版本或配置已构建二进制。

SoundCraft 连接后读取 session.inspect，查询 track、mix、clip、bounce 等命令。以音轨/片段实际 id 为准，验证单位（dB、samples、seconds）及采样率，再执行编辑。自动化启动默认 --no-audio；播放需求可使用用户已启动的正常实例并配置其端口。未经用户录音请求，不启用录音或输入监听。

CADCraft 查询 command_line/execute 和 document.inspect/drawing.inspect 等实时工具；核对坐标系、图纸单位和当前图层再创建实体。数值编辑后读取几何并渲染预览。导出格式以实际工具目录为准。

桌面用 craft_command/craft_control；独立引擎用 craft_engine_tools/craft_engine_call。保存可编辑工程后再导出，返回产物路径和实际验证结果。原生 --connect 参数差异见 [协议说明](../../references/protocols.md)。
