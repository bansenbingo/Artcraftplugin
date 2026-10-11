# 验证记录

2026-10-11，macOS，本机原生软件。测试通过 MCP Python SDK 客户端真实初始化、列工具并调用两个插件入口；GUI 使用合成内容和独立端口，最终输出位于 `/Users/teddyjiang/Documents/CraftAgent/smoke-20261011-185541`。未编辑用户照片或个人工程。

| 软件 | GUI 版本 | 已验证 |
|---|---|---|
| PhotoCraft | 0.7.0 | 建立 320×180 图像，令牌认证，app.save 保存 PSD，检查状态，返回窗口 PNG |
| VectorCraft | 0.9.0 | 新建画板、创建矩形、保存 SVG、返回窗口 PNG |
| FilmCraft | 0.6.0 | 新建工程与 24fps 序列，保存 fcproj，返回窗口 PNG |
| LightCraft | 0.6.0 | GUI 演示库曝光编辑与截图；原生独立 MCP 导入合成 PNG、开发编辑、转发 MCP 图片、导出 256px PNG |
| PdfCraft | 0.6.0 | 控制文件、令牌和 JSON-RPC 认证；创建空白 PDF、读取状态、返回窗口 PNG |
| EffectCraft | 0.8.0 | 创建合成与文字图层，保存 ecproj，返回窗口 PNG |
| WordCraft | 0.5.0 | 窗口密钥认证、写入中英文、保存 docx、返回窗口 PNG |
| GridCraft | 0.5.0 | GUI 写入公式并确认结果 5，保存 xlsx、截图；原生独立 MCP 连续编辑得到公式结果 18 并保存 xlsx |
| DeckCraft | 0.5.0 | 新建演示与幻灯片，保存 pptx，返回窗口 PNG |
| DesignCraft | 未安装 | 已读源码并制作适配，未实测 GUI/原生 CLI |
| SoundCraft | 未安装 | 已读源码并制作适配，未实测 GUI/原生 CLI |
| CADCraft | 未安装 | 已读源码并制作适配，未实测 GUI/原生 CLI |

保存文件二次验证：xlsx/docx/pptx ZIP 结构与 CRC 通过；PSD 头为 8BPS、尺寸 320×180；SVG 可解析为 XML；ecproj/fcproj 可解析为 JSON；LightCraft PNG 长边确实为 256。GridCraft 截图已目视确认 2、3、5 的结果。

原生 CLI：GridCraft 由 commit `9f896c1249f40d18bf182199dc03042959be5f3f` 执行 `cargo build --release -p gridcraft-cli` 构建；LightCraft 官方 0.6.0 macOS universal 包 SHA256 为 `e87014d49d4dbf00851f5ff3005ecd0d5418ccd77af4f72aa750374e3f4803ce`，与 release SHA256SUMS.txt 一致。二进制安装在用户 runtime，未打包进插件 ZIP。

协议单元测试 7 项：PhotoCraft token、WordCraft key、PdfCraft 控制文件/JSON-RPC、失败认证不得执行编辑、共享/符号链接凭据拒绝、独立原生会话连续状态与 schema 验证、超时不得重放编辑。7 个 skills 均通过 skill-creator quick_validate。

完整烟雾测试记录保存于 `test-results/smoke-live.json`，握手与引擎检查记录为 `test-results/smoke-protocol.json`；这是实测记录，不是外部 LLM 评估分数。未验证 Windows/Linux、全部命令、视频完整编码、PDF 文档保存、所有源格式往返或生产级稳定性。

版本差异：已安装 PdfCraft 0.6.0 的控制目录没有 ui.quit/ui.resize，当前 main 文档已有它们。未知 UI 方法会返回原生错误，不会被模拟成成功。PhotoCraft engine file.save* 会被作用域策略拒绝，已实测改用 app.save。GridCraft 不采用通用 command_run 工具名，代理按实时 schema 调用 set_cell/get_cell/save_workbook。

插件由本机 codex plugin marketplace/add 解析并安装，两个 MCP 注册启用。最后还对安装缓存中的入口重新执行 MCP 握手、工具目录和只读状态调用，记录在 `test-results/installed-mcp.json`。新插件需要新聊天或重建客户端连接后才出现在对话工具列表。
