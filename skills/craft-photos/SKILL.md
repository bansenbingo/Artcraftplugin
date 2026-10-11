---
name: craft-photos
description: Organize photos and develop RAW images locally in LightCraft, with catalog queries, slider discovery, rendered previews and exports.
---

使用 LightCraft 本地图库和 RAW 开发引擎。桌面 craft_launch 默认打开配置 workspace 下独立的持久图库；需要用户已有图库时，配置 apps.lightcraft.library 为那个真实目录。`scratch:true` 是内存演示图库，不能当成用户的真实照片库。

一个持久图库同时只能被一个进程打开。用户已在 GUI 中编辑时，使用 craft-desktop；不要让独立引擎再以 --library 打开相同目录。独立引擎会话默认内存；要持久化，在配置 apps.lightcraft.headless_args 中使用 ["--library","绝对图库路径"]，再重建会话。

桌面通过 craft_list_commands 发现 catalog.query、library.select、develop.controls、develop.set、app.export 等精确命令。独立 MCP 通过 craft_engine_tools 发现 query_photos、select_photos、list_controls、get_develop、set_develop、render_photo 和 export 的实时 schema。先确认照片 id、当前设置和控件范围，修改后渲染预览。

导入优先使用引用或复制模式，并遵循用户已授权的方式；move 模式会移动原始文件，不从普通导入意图推断为 move。导出明确文件格式、尺寸、色彩空间和目标目录；该软件部分导出尺寸默认 3000px，原尺寸按实时 schema 指定，不把默认导出当成原图。

磁盘写入失败可能意味着修改已应用在内存、尚未持久化。读取图库未保存状态并处理原因后验证保存。库锁、开发控件和原生参数见 [协议说明](../../references/protocols.md)。
