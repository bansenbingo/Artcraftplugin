# Windows 验证记录

2026-10-11，Windows 原生环境。测试使用合成文档，未编辑用户照片或个人项目；测试实例和临时文档已清理。macOS 的历史结果独立保留在仓库根目录 `VALIDATION.md`。

| 软件 | 桌面测试 | 独立引擎测试 |
|---|---|---|
| PhotoCraft | 创建 320×180 RGB 图像，检查状态，保存 PSD、窗口截图 | 创建、检查、PNG 预览，CLI 初始化成功（21 个工具） |
| VectorCraft | 创建 320×180 画板与矩形，检查并保存原生文件 | 创建、检查、320×180 PNG 预览、保存原生文件（32 个工具） |
| FilmCraft | 创建工程和 320×180 / 24fps 序列，保存 fcproj、窗口截图 | 创建、检查序列、帧预览、保存工程（17 个工具） |
| LightCraft | 隔离演示库启动、UI 检查、窗口截图 | 原生 CLI 初始化、实时工具目录（318 个工具）；本次没有编辑用户照片 |
| PdfCraft | 私有控制文件、认证、创建空白 PDF、状态与窗口截图 | 从合成文本创建 PDF，打开、检查、页预览、另存 PDF（143 个工具） |
| EffectCraft / DesignCraft / WordCraft / GridCraft / DeckCraft / SoundCraft / CADCraft | 本机未安装，未实测 | 本机未安装，未实测 |

保存产物已检查非空；引擎预览 PNG 签名和尺寸正确。详细的三款补充测试记录见 [windows-validation.json](test-results/windows-validation.json)。工具数量仅代表当前安装版本的目录，不代表每个命令均已验证。

两个已安装 MCP 入口均重新初始化成功：desktop 7 个工具、engine 4 个工具。五款已安装应用均完成原生 CLI 握手，并关闭此次测试的独立会话。Python 依赖 `pip check` 通过。原有 Windows 协议单元测试 7 项通过，覆盖凭据/认证、JSON-RPC、持久状态、参数校验及超时不重放。

发布版补充 UTF-8/BOM 中文配置、Program Files GUI/CLI 自动发现测试，Windows 单元测试共 9 项；根目录自动安装器另有 Windows / macOS 选择及 Linux 拒绝测试共 3 项。发布目录的两个 MCP 握手与严格参数验证通过，Codex CLI 正确解析 `artcraft-agent@artcraft-windows` 0.1.1 的 marketplace。打包时校验原始 macOS 文件保持原样、ZIP CRC/SHA256、Windows 图标及 manifest 路径一致。

Windows 适配包括：AppData 路径、Program Files GUI / CLI 自动发现、`Scripts/python.exe` venv、Python MCP 启动器、线程/队列读取 Windows 子进程 stdout（替代对管道使用 `select`）、Windows fixture CLI 启动和 POSIX 权限断言的平台分支。

限制：VectorCraft 的真实窗口截图返回未绘制帧（窗口遮挡、最小化或锁屏等）；其独立引擎内容预览正常。FilmCraft 仅验证空序列及代表帧，尚未验证完整视频编码/导出。未覆盖全部命令、格式往返、多客户端并发或所有 Windows 版本。普通 MCP 注册成功不能替代真实编辑/保存测试。

Windows 版内置的 256×256 透明 PNG 从本机桌面 ArtCraft Launcher 快捷方式指向的图标资源提取；源码、安装缓存与打包版本使用同一文件。软件 EXE、runtime、用户配置、凭据及用户工程不随插件上传。
