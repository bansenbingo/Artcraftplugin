# 本地 Craft 控制：源码核对与协议差异

核对日期：2026-10-11。结论基于下列固定 commit 的文档、CLI 参数解析器和桌面控制处理器。最新 main 和已安装版本可能不同；实际 tools/list、engine.commands 和连接测试优先。

## 共用架构

Agent → CLI 的 stdio MCP → 内存引擎，或 Agent → MCP bridge → 本机 TCP JSON-lines → GUI 内的同一命令注册表。普通 TCP 控制消息是 `{id,method,params}`，响应 `{id,ok,result/error}`；不是 HTTP，也不是所有应用都使用 JSON-RPC。PdfCraft 的控制通道例外：它使用 JSON-RPC 2.0。

UI、CLI 和 MCP 大部分调用同一套 engine command registry，因此命令编辑、UI 点击、文档检查和渲染都可以自动化。但 headless 文档和 GUI 文档彼此独立；这些项目仍是 alpha/开发阶段，不保证 Adobe 的所有能力或格式兼容性。

## 原生启动参数

以下是上游参数。端口是上游示例值，插件为每个应用分配独立的 19001–19012，避免 VectorCraft/DesignCraft/GridCraft/CADCraft 都使用 7979。

| 应用 | GUI 控制启动 | 原生 MCP 独立模式 | 原生 MCP 控制 GUI |
|---|---|---|---|
| PhotoCraft | `photocraft --control 7878 --control-token-file TOKEN --automation-read-root WORK --automation-write-root WORK` | `photocraft-cli mcp --automation-read-root WORK --automation-write-root WORK` | `photocraft-cli mcp --bridge 127.0.0.1:7878 --control-token-file TOKEN` |
| VectorCraft | `vectorcraft --control 7979` | `vectorcraft-cli mcp --headless` | `vectorcraft-cli mcp --connect 127.0.0.1:7979` |
| FilmCraft | `filmcraft --control 9876` | `filmcraft-cli mcp` | `filmcraft-cli mcp --bridge 127.0.0.1:9876` |
| LightCraft | `lightcraft --library LIBRARY --control 7980` | `lightcraft-cli mcp --library OTHER_LIBRARY` | `lightcraft-cli mcp --connect 127.0.0.1:7980` |
| PdfCraft | `pdfcraft --control PRIVATE_CONTROL_FILE` | `pdfcraft-cli mcp --root WORK` | 无 `mcp --connect`；桌面使用 `pdfcraft-cli ui --control PRIVATE_CONTROL_FILE METHOD` 或插件 JSON 适配 |
| EffectCraft | `effectcraft --control 9877` | `effectcraft-cli mcp` | `effectcraft-cli mcp --bridge 9877` |
| DesignCraft | `designcraft --control 7979` | `designcraft-cli mcp` | `designcraft-cli mcp --connect 7979` |
| WordCraft | `wordcraft --control 7981` | `wordcraft-cli mcp` | `wordcraft-cli mcp --connect 127.0.0.1:7981` |
| GridCraft | `gridcraft --control 7979` | `gridcraft-cli mcp` | `gridcraft-cli mcp --connect 7979` |
| DeckCraft | `deckcraft --control 7990` | `deckcraft-cli mcp` | `deckcraft-cli mcp --connect 7990` |
| SoundCraft | `soundcraft --control 7801` | `soundcraft-cli mcp` | `soundcraft-cli mcp --connect 7801` |
| CADCraft | `cadcraft --control 7979` | `cadcraft-cli mcp` | `cadcraft-cli mcp --connect 127.0.0.1:7979` |

## 认证与文件访问

PhotoCraft 每条 TCP 连接先发送 `auth {token}`。token 文件自动创建并以 Unix 0600 保存。插件只读取私有文件，从不把令牌放进工具结果。

PhotoCraft 桌面的 file.open/file.save/file.saveAs/file.saveACopy 不通过作用域文件能力，因此自动化总是拒绝这些 engine 命令（即使 enabled 为 true）。正确接口是 craft_control 的 `app.open {path}` 与 `app.save {path}`，native MCP 对应 doc_open/doc_save。此区别在真实保存测试中已验证。

WordCraft 读取 `~/Library/Application Support/WordCraft/control-key.local-PORT`（macOS），发送 `auth {key}`；其他平台可在配置指定 key_file。启动后的 key 每次重新读取，不能在 token 参数中代替 UI key 字段。

PdfCraft 的 `--control` 参数是文件路径，应用在里面写 `{port,token}`，端口随机分配。认证后支持 ui.state/ui.inspect（AccessKit widget tree）/ui.open/ui.commands/ui.command/ui.type/ui.key/ui.screenshot 等。ui.command 的参数只有 id，PDF task MCP 的 file.open/page.rotate 等映射命令不是这个 UI 接口。

其他原生 TCP 通道多数只绑定 loopback，没有认证。插件也只连接 127.0.0.1。不要把这些原生端口直接当远程 MCP 暴露。

PhotoCraft/VectorCraft/EffectCraft 独立 MCP 支持 automation-read/write-root，PdfCraft 用 --root；LightCraft、DesignCraft、FilmCraft 等不能凭空加这些统一参数。VectorCraft 的 roots imply headless，bridge 的 roots 要设在 GUI 进程，不能设在 --connect 的 CLI 端。PhotoCraft 的 bridge 同理。插件的 GUI roots 目前只对 PhotoCraft/VectorCraft 设置；不声称其他软件被插件沙箱隔离。

## Agent 操作顺序

1. `craft_status` 确认真实软件路径和版本；`craft_launch {app}` 启用控制通道。
2. `craft_inspect {app,view:"ui"}` 验证连接，再 `craft_list_commands {app,query,limit}` 读取功能 id、参数和 enabled。
3. `craft_command {app,command,params}` 编辑；ui.click/ui.key/对话框等通过 `craft_control`，遵循各应用原生 schema。
4. 重新 inspect；`craft_screenshot` 检查窗口（或独立 MCP render_preview 检查文档）。
5. 根据实时目录保存可编辑工程并导出成品，验证文件存在、内容和尺寸/时长。

独立 MCP 使用 `craft_engine_tools` 和 `craft_engine_call`，会话跨多次调用持续存在。插件保留原生图像、structuredContent、isError，并按原生 schema 校验入参。不要把全目录塞进每次上下文；使用 query/offset/limit。桥接不转发原生 progress/cancellation、资源/订阅或 sampling；有此需求时直接注册上游 native MCP。停止/客户端退出会丢弃未保存的内存工程。

批处理一般逐条编辑和撤销，不保证回滚。超时/断线可能发生在修改后，先读取状态，再决定是否重试。插件不自动重放编辑；原生进程异常退出也不会悄悄重建空会话。

## 源码证据

### photocraft · `830541ded278db4892877a527bf59345a472fa07`

- [apps/photocraft-cli/src/main.rs](https://github.com/storytold/photocraft/blob/830541ded278db4892877a527bf59345a472fa07/apps/photocraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/photocraft/blob/830541ded278db4892877a527bf59345a472fa07/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/photocraft/blob/830541ded278db4892877a527bf59345a472fa07/docs/control-protocol.md)
- [apps/photocraft/src/control_server.rs](https://github.com/storytold/photocraft/blob/830541ded278db4892877a527bf59345a472fa07/apps/photocraft/src/control_server.rs)

### vectorcraft · `22ff29167e23bf0d71c9609d189c4fdaf89e2e7c`

- [apps/vectorcraft-cli/src/main.rs](https://github.com/storytold/vectorcraft/blob/22ff29167e23bf0d71c9609d189c4fdaf89e2e7c/apps/vectorcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/vectorcraft/blob/22ff29167e23bf0d71c9609d189c4fdaf89e2e7c/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/vectorcraft/blob/22ff29167e23bf0d71c9609d189c4fdaf89e2e7c/docs/control-protocol.md)
- [apps/vectorcraft/src/control_server.rs](https://github.com/storytold/vectorcraft/blob/22ff29167e23bf0d71c9609d189c4fdaf89e2e7c/apps/vectorcraft/src/control_server.rs)

### filmcraft · `4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe`

- [apps/filmcraft-cli/src/main.rs](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/apps/filmcraft-cli/src/main.rs)
- [docs/agents.md](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/docs/agents.md)
- [docs/control-protocol.md](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/docs/control-protocol.md)
- [apps/filmcraft/src/control_server.rs](https://github.com/storytold/filmcraft/blob/4e2d0bc2d3646f9cf27ef7aa8b2095c6858c7efe/apps/filmcraft/src/control_server.rs)

### lightcraft · `0ba118de92a81f7463ca0e6d79e1323137b1adae`

- [apps/lightcraft-cli/src/main.rs](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/apps/lightcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/docs/control-protocol.md)
- [apps/lightcraft/src/control_server.rs](https://github.com/storytold/lightcraft/blob/0ba118de92a81f7463ca0e6d79e1323137b1adae/apps/lightcraft/src/control_server.rs)

### pdfcraft · `bbbe60015c571ebfc39708ee07777b89e267122a`

- [apps/pdfcraft-cli/src/main.rs](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/apps/pdfcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/docs/mcp.md)
- [crates/ui-egui/src/control.rs](https://github.com/storytold/pdfcraft/blob/bbbe60015c571ebfc39708ee07777b89e267122a/crates/ui-egui/src/control.rs)

### effectcraft · `9a7d3e76991d5372448033b473dc12c2480a6a04`

- [apps/effectcraft-cli/src/main.rs](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/apps/effectcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/docs/control-protocol.md)
- [apps/effectcraft/src/control_server.rs](https://github.com/storytold/effectcraft/blob/9a7d3e76991d5372448033b473dc12c2480a6a04/apps/effectcraft/src/control_server.rs)

### designcraft · `16a7365701f9ce8f93ca77a27a8dc2fffb807869`

- [apps/designcraft-cli/src/main.rs](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/apps/designcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/docs/control-protocol.md)
- [apps/designcraft/src/control_server.rs](https://github.com/storytold/designcraft/blob/16a7365701f9ce8f93ca77a27a8dc2fffb807869/apps/designcraft/src/control_server.rs)

### wordcraft · `1d4f741f23773f47a27a5a017ba47e59629caee5`

- [apps/wordcraft-cli/src/main.rs](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/apps/wordcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/docs/control-protocol.md)
- [apps/wordcraft/src/control_server.rs](https://github.com/storytold/wordcraft/blob/1d4f741f23773f47a27a5a017ba47e59629caee5/apps/wordcraft/src/control_server.rs)

### gridcraft · `9f896c1249f40d18bf182199dc03042959be5f3f`

- [apps/gridcraft-cli/src/main.rs](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/apps/gridcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/docs/control-protocol.md)
- [apps/gridcraft/src/control_server.rs](https://github.com/storytold/gridcraft/blob/9f896c1249f40d18bf182199dc03042959be5f3f/apps/gridcraft/src/control_server.rs)

### deckcraft · `a98df49b21632d69a3da994d35df1ea91dab41af`

- [apps/deckcraft-cli/src/main.rs](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/apps/deckcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/docs/control-protocol.md)
- [apps/deckcraft/src/control_server.rs](https://github.com/storytold/deckcraft/blob/a98df49b21632d69a3da994d35df1ea91dab41af/apps/deckcraft/src/control_server.rs)

### soundcraft · `7414719f3760de1c9359ec9723351a7232442e61`

- [apps/soundcraft-cli/src/main.rs](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/apps/soundcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/docs/control-protocol.md)
- [apps/soundcraft/src/control_server.rs](https://github.com/storytold/soundcraft/blob/7414719f3760de1c9359ec9723351a7232442e61/apps/soundcraft/src/control_server.rs)

### cadcraft · `699dd1aeca1dba018931d2eb95e92c0cf2033bbd`

- [apps/cadcraft-cli/src/main.rs](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/apps/cadcraft-cli/src/main.rs)
- [docs/mcp.md](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/docs/mcp.md)
- [docs/control-protocol.md](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/docs/control-protocol.md)
- [apps/cadcraft/src/control_server.rs](https://github.com/storytold/cadcraft/blob/699dd1aeca1dba018931d2eb95e92c0cf2033bbd/apps/cadcraft/src/control_server.rs)
