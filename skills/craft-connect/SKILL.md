---
name: craft-connect
description: Set up and diagnose local Craft app automation; connect a desktop window or discover native headless MCP tools.
---

连接和诊断本机 Craft 软件。使用 `craft-desktop` 的 `craft_status` 查看实际安装路径和版本。`craft_launch {app}` 开启对应软件的本地控制通道；普通双击打开的窗口未必启用了控制通道。`craft_inspect {app, view:"ui"}` 的成功响应才能证明连接正常。已打开的个人窗口不要强制退出；需要连接它时，在用户配置中写入其真实端口/控制文件，再重建 MCP 连接。

两种会话：桌面 `craft_command` 修改窗口里的工程；独立 `craft-engine` 调用本地 `<app>-cli mcp`，拥有另一份内存工程。持续编辑必须复用同一个会话。不要把独立引擎的结果描述成已显示在窗口中。独立引擎重启前显式保存工程。

若没有 CLI，桌面控制仍然可用。执行插件 `scripts/setup.py --install-cli <app> --skip-runtime` 可安装与本机 GUI 版本匹配、经官方 SHA256SUMS 校验的 macOS CLI；其他平台在配置中指定 CLI 路径。具体参数和安装步骤见 [协议说明](../../references/protocols.md) 与插件根目录 README。

先查询 `craft_list_commands {app,query}` 或 `craft_engine_tools {app,query}`，读取精确参数和 enabled 状态，再调用命令。文件读写范围是配置的 workspace；PhotoCraft/VectorCraft 会在应用内实施范围限制，其他软件沿用其原生文件权限。将工作文件放到配置目录或按任务修改 workspace，勿假定所有应用都有同样的沙箱。

出现超时或断线时，编辑可能已经执行；重新 inspect 验证后再决定是否重试。端口、令牌、窗口密钥不要输出到用户消息或提交到仓库。
