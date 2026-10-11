---
name: craft-video
description: Edit timelines in FilmCraft and compositions/VFX in EffectCraft through local app commands, frame previews and render/export jobs.
---

FilmCraft 负责视频时间线、素材、剪辑和导出；EffectCraft 负责合成、图层、关键帧、特效和渲染队列。连接真实应用后 inspect 工程，查询命令目录，再执行目标命令；不要猜测序列、轨道、合成或图层 id。

FilmCraft 查询 file.import、sequence、clip、effect、file.exportMedia 等功能。素材时间可能是 ticks、frames 或 seconds，读取当前命令参数文档和帧率后换算。EffectCraft 查询 comp.new、layer、prop、renderQueue；可以通过 command.describe 获取具体参数 schema。先用小尺寸代表帧检查效果，再渲染完整输出。

独立引擎使用 craft_engine_tools/craft_engine_call，原生 MCP 图像会原样返回。连接窗口用 craft_screenshot；该截图需要窗口实际绘制，不代表导出成片。渲染工具可能同步阻塞，也可能返回后台 job；读取实时 schema 和状态字段，直到任务完成，再检查实际输出文件。

此插件的独立引擎桥接不转发 MCP progress/cancellation。长渲染可设置 timeout_seconds（最多 3600），或使用原生后台任务工具并轮询。超时不等于取消；不要直接重新发起相同渲染。使用原生命令停止队列时，先核对目标任务。

保存工程并验证产物。视频容器、编码器、素材解码能力以当前安装版本为准。原生 CLI 使用 --bridge，EffectCraft 与 FilmCraft 的端口不同，见 [协议说明](../../references/protocols.md)。
