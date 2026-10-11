# ArtCraft Windows 0.1.1

Windows 原生版本，补充 Windows 程序发现、stdio 管道读取和 Python 启动器。显示名称 **ArtCraft**；图标来自 ArtCraft Launcher 的原始 Windows 图标资源，已内置在 [`assets/artcraft.png`](assets/artcraft.png)，无需访问安装者桌面。

**只在 Windows 原生 Python 中安装本目录**。macOS 请使用仓库根目录原版；Linux / WSL 未验证。首选 [仓库首页的系统自动选择安装器](https://github.com/bansenbingo/Artcraftplugin#agent-安装规则先识别系统再选择版本)，不要把根目录的 macOS `.mcp.json` 注册为 Windows 版。

## 安装

需要 Python 3.11+（`python` 在 Codex PATH 中可用）、Git、支持 `codex plugin` 的 Codex CLI。完整仓库安装：

```powershell
git clone https://github.com/bansenbingo/Artcraftplugin.git
Set-Location Artcraftplugin
py -3 scripts/install.py --dry-run
py -3 scripts/install.py
```

或者进入**本目录 / Windows ZIP 解压根目录**手动安装：

```powershell
py -3 scripts/setup.py
codex plugin marketplace add "$PWD"
codex plugin add artcraft-agent@artcraft-windows
```

不要同时启用 macOS 和 Windows 两个版本；它们使用相同 MCP 服务名。首次 setup 联网安装 `requirements-lock.txt` 到独立 venv；之后服务启动不下载依赖。重新打开 Codex / 新建聊天加载插件，调用 `craft_status` 和 `craft_engine_status` 检查路径。`scripts/doctor.py` 也可检查发现结果。

## 软件路径和配置

默认扫描 `C:\Program Files\<XxxCraft>\<xxxcraft>.exe` / `<xxxcraft>-cli.exe`，也检查 `ProgramW6432`、本地应用目录和 PATH。已安装程序无需复制到插件。Windows 不使用 `setup.py --install-cli`（该下载功能仅用于 macOS）。

用户配置：`%APPDATA%\artcraft-agent\config.json`。运行环境：`%LOCALAPPDATA%\artcraft-agent\venv\Scripts\python.exe`；日志与控制文件在 runtime 的 `run/`。默认工作目录 `~/Documents/CraftAgent`。打包桌面进程可能重定向 AppData，以工具实际返回路径为准。

非默认目录可显式配置，例如：

```json
{
  "workspace": "C:/Users/your-name/Documents/CraftAgent",
  "apps": {
    "photocraft": {
      "executable": "D:/Apps/PhotoCraft/photocraft.exe",
      "cli": "D:/Apps/PhotoCraft/photocraft-cli.exe"
    },
    "lightcraft": {"headless_args": []},
    "wordcraft": {"headless_args": ["--author", "AI Agent"]}
  }
}
```

工作路径含中文或空格时照常使用 JSON 字符串；更新配置后重建 MCP 连接。两个 MCP 使用 `python servers/run.py desktop|engine` 启动，启动器再选择安装好的 venv。`CRAFT_AGENT_PYTHON` 可指定实际 runtime Python。

## 使用与验证

先查询精确命令 / schema，再编辑、inspect、预览和保存。GUI 与独立引擎分别持有工程；窗口截图与内容预览不同。不要关闭或覆盖用户已有项目。PhotoCraft 桌面读写用 `app.open` / `app.save`，其他差异见 [protocols.md](references/protocols.md)。

在本目录中运行：

```powershell
& "$env:LOCALAPPDATA\artcraft-agent\venv\Scripts\python.exe" -m unittest discover -s tests -v
& "$env:LOCALAPPDATA\artcraft-agent\venv\Scripts\python.exe" scripts/smoke_mcp.py
```

普通 smoke 检查 MCP 握手，不启动 GUI。`--live` 仅供隔离的 GUI 测试，要求窗口能实际绘制；遇到截图失败要检查状态并清理本次测试实例，不要反复执行编辑。已实测范围与限制见 [VALIDATION.md](VALIDATION.md)。

图标同时用于亮色、暗色及 composer：manifest 的 `logo`、`logoDark`、`composerIcon` 均指向 `./assets/artcraft.png`。更新后重建客户端才能刷新缓存显示。
