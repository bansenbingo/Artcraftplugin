# ArtCraft — macOS / Windows 插件

供 **Codex 桌面及 CLI** 使用的本地 Craft 自动化插件：7 个 skills、2 个 stdio MCP，支持桌面控制与独立引擎。无需 OpenAI API key，不调用远程生成服务。

本仓库同时保留 **原始 macOS 版 0.1.0** 和 **Windows 版 0.1.1**。两版独立存放，Windows 改动没有覆盖原来的 macOS 源码或 ZIP。

## Agent 安装规则：先识别系统，再选择版本

**请安装本插件的 agent 严格遵守以下顺序：**

1. 检测当前执行主机的操作系统，例如运行 `python -c "import sys; print(sys.platform)"`（macOS 可用 `python3`，Windows 可用 `py -3`）。不要根据对话语言、路径示例或用户以前使用的系统作判断。
2. `win32` 选择 **`windows/`**；`darwin` 选择**仓库根目录的原始 macOS 插件**。Linux/WSL 尚未验证，安装器会拒绝；要控制 Windows 软件，请在 Windows 原生 Python / PowerShell 中安装。
3. 推荐执行根目录的 `scripts/install.py`，它会自动选择正确的 setup 脚本、marketplace 和插件标识。先用 `--dry-run` 查看选择结果。
4. **只安装当前系统对应的一版**，避免重复注册同名 `craft-desktop` / `craft-engine` 服务。根目录 `.agents` 和 `.mcp.json` 属于 macOS；Windows 不要对仓库根目录运行 `codex plugin marketplace add`。
5. 安装后初始化两个 MCP，使用 `craft_status` 和 `craft_engine_status` 核对真实 GUI/CLI 路径，再通过 `craft_engine_tools` 或隔离的 GUI 实例验证连接。目录存在或端口开放不等于连接成功。

| 系统 | 插件目录 | Marketplace / 安装标识 | 安装包 |
|---|---|---|---|
| Windows | [`windows/`](windows/README.md) | `artcraft-windows` / `artcraft-agent@artcraft-windows` | [`artcraft-windows-plugin.zip`](dist/artcraft-windows-plugin.zip) · [SHA256](dist/artcraft-windows-plugin.zip.sha256) |
| macOS | 仓库根目录（原始 0.1.0） | `artcraft-local` / `artcraft-agent@artcraft-local` | [`artcraft-agent-plugin.zip`](dist/artcraft-agent-plugin.zip) · [SHA256](dist/artcraft-agent-plugin.zip.sha256) |

原始 macOS 快照：[macos-v0.1.0](https://github.com/bansenbingo/Artcraftplugin/tree/macos-v0.1.0)。原始说明另存为 [README-macos-original.md](references/README-macos-original.md)，其中的历史本机路径仅用于记录；安装以本页为准。

## Windows 安装

需要 Windows 原生 **Python 3.11+**、Git、支持 `codex plugin` 的 Codex CLI，以及本机 Craft 软件。`python` 必须在 Codex 的 PATH 中可用；如果只有 `py`，先将真实 Python 安装目录加入 PATH。首次 setup 会联网安装锁定的 Python 依赖。

在 PowerShell 中：

```powershell
git clone https://github.com/bansenbingo/Artcraftplugin.git
Set-Location Artcraftplugin
py -3 scripts/install.py --dry-run
py -3 scripts/install.py
```

自动安装器在 Windows 上执行相当于：

```powershell
py -3 windows/scripts/setup.py
codex plugin marketplace add "$((Resolve-Path .\windows).Path)"
codex plugin add artcraft-agent@artcraft-windows
```

若 `codex` 不在 PATH，使用 `py -3 scripts/install.py --codex 'C:\实际路径\codex.exe'`，或先安装/配置 Codex CLI。如果使用 Windows ZIP，先解压到固定目录，进入**解压后的插件根目录**，执行 `py -3 scripts/setup.py`、`codex plugin marketplace add "$PWD"`、`codex plugin add artcraft-agent@artcraft-windows`。

Windows GUI / CLI 自动从 `C:\Program Files\<XxxCraft>\<xxxcraft>.exe` 和 `<xxxcraft>-cli.exe` 等位置查找；路径带空格可正常处理。其他位置可在 `%APPDATA%\artcraft-agent\config.json` 中配置。**Windows 版显示名称为 ArtCraft，图标为从桌面 ArtCraft Launcher 原始资源提取的透明 PNG**，已经内置，安装者不需要另备快捷方式。

详见 [Windows 安装、配置和验证](windows/README.md)。已有本地旧版 Windows 测试安装 `artcraft-agent@artcraft-local` 的用户，迁移时先保存工程，再移除旧插件及旧的 `artcraft-local` marketplace，之后安装本页 Windows 版；这一步只针对旧测试安装，不要在正常 macOS 安装上执行。

## macOS 安装

需要 **Python 3.11+**、Git、支持 `codex plugin` 的 Codex CLI。macOS 使用根目录保留的原始 shell 启动器和 `.app` 路径发现。

```sh
git clone https://github.com/bansenbingo/Artcraftplugin.git
cd Artcraftplugin
python3 scripts/install.py --dry-run
python3 scripts/install.py
```

自动安装器在 macOS 上执行相当于：

```sh
python3 scripts/setup.py
codex plugin marketplace add "$PWD"
codex plugin add artcraft-agent@artcraft-local
```

使用原始 macOS ZIP 时，解压到固定目录后执行上述三条手动命令。完整历史测试见 [macOS 验证记录](VALIDATION.md)。macOS 的 GUI 通常不自带 CLI；可按下面方式安装匹配版本的官方 CLI（带 SHA256 校验）：

```sh
python3 scripts/setup.py --skip-runtime --install-cli lightcraft
```

此 CLI 下载器仅支持 macOS；Windows 使用已安装的 `-cli.exe`，不要在 Windows 调用 `--install-cli`。

## 配置与首次使用

| 内容 | Windows | macOS |
|---|---|---|
| 工作目录 | `~/Documents/CraftAgent` | `~/Documents/CraftAgent` |
| 用户配置 | `%APPDATA%\artcraft-agent\config.json` | `~/.config/artcraft-agent/config.json` |
| Python runtime / 日志 | `%LOCALAPPDATA%\artcraft-agent\` | `~/.local/share/artcraft-agent/` |

可通过 `CRAFT_AGENT_CONFIG` / `CRAFT_AGENT_HOME` 覆盖这些位置。Windows 打包桌面环境可能重定向 AppData；以 `craft_status` 的实际路径为准。插件不打包软件 EXE、venv、用户工程或控制凭据。修改配置后重建 MCP 连接；安装或更新后重新打开 Codex / 新建聊天以加载插件。

可以对 agent 说：

> 使用 ArtCraft 检查本机 Craft 软件，读取 PhotoCraft 的实时工具目录，创建合成测试图，预览后保存到 CraftAgent 文件夹。

> 使用 craft-photos 连接 LightCraft，把我指定照片的曝光提高 0.5，先预览，再导出新文件。

桌面 `craft-desktop` 操作真实窗口；`craft-engine` 启动独立 CLI 内存工程，**两者不是同一份文档**。精确命令必须从 `craft_list_commands` / `craft_engine_tools` 获取；保存工程和导出文件分别执行并检查产物。异常/超时后先 inspect，不能直接重放编辑。

PhotoCraft/VectorCraft 会实施各自的自动化文件范围；其他软件沿用其原生权限。LightCraft GUI 与独立引擎不要同时打开同一图库。截图可能要求窗口可见。本项目没有部署远程 MCP / ChatGPT App。

## 已验证范围

Windows 已验证 PhotoCraft、VectorCraft、FilmCraft、LightCraft、PdfCraft 的桌面连接及原生 CLI 初始化。PhotoCraft、VectorCraft、FilmCraft、PdfCraft 的基础创建/保存/预览已实测；LightCraft 本轮验证了连接、工具目录和 GUI 截图。VectorCraft 桌面截图存在窗口未绘制限制，其引擎预览正常；FilmCraft 尚未验证完整视频编码导出。见 [Windows 验证记录](windows/VALIDATION.md)。其余应用尚未安装，不能视为已实测。

macOS 历史验证保持在 [VALIDATION.md](VALIDATION.md)，与 Windows 结果分开记录。上游软件处于 alpha / 开发阶段，不承诺完整 Adobe 功能或所有格式往返。

Windows 检查命令：

```powershell
& "$env:LOCALAPPDATA\artcraft-agent\venv\Scripts\python.exe" -m unittest discover -s windows/tests -v
& "$env:LOCALAPPDATA\artcraft-agent\venv\Scripts\python.exe" windows/scripts/smoke_mcp.py
```

macOS 检查命令：

```sh
~/.local/share/artcraft-agent/venv/bin/python -m unittest discover -s tests -p test_runtime.py -v
~/.local/share/artcraft-agent/venv/bin/python scripts/smoke_mcp.py
```

本项目为非官方社区集成。协议来源与应用启动差异见 [references/protocols.md](references/protocols.md)。
