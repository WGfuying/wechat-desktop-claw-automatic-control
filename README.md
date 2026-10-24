# 微信 PC 端自动控制 Skill

> ⚠️ **平台支持：Windows only（仅支持 Windows）**
> 本 Skill **仅支持 Windows 平台**，依赖微信 Windows 桌面端 + Windows-MCP 原生控制。
> **暂无 macOS 版**，也不支持微信 macOS 客户端。打包 / 上架 / 分发时务必保留此声明。

> 本 Skill 是 OpenClaw / WorkBuddy 的插件，在 Windows 端通过 **Windows-MCP** 原生控制微信桌面端，实现消息 / 图片 / 文件的自动发送。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 打开微信 | 如未运行自动启动，已运行则直接连接（绝不退出） |
| 定位联系人 | 点左侧聊天列表项（避开搜索框歧义） |
| 发送文本 | 支持长文本（从文件读取） |
| 发送图片 | Windows-MCP 走剪贴板 / pywinauto 备选走 DIB 剪贴板 |
| 发送文件 | 通过微信文件选择对话框 |
| 被其他 Skill 调用 | 可作为自动化推送通道 |

## 📦 安装

### 方式一：SkillHub（推荐）

```bash
skillhub install wechat-desktop-claw-automatic-control
```

### 方式二：手动安装

将本 Skill 目录复制到 OpenClaw / WorkBuddy 的 workspace skills 目录：

```bash
cp -r wechat-desktop ~/.openclaw/workspace/skills/wechat-desktop
```

### 方式三：安装主依赖 Windows-MCP

在 WorkBuddy 客户端 MCP 配置（`~/.workbuddy/mcp.json`）加入：

```json
{
  "mcpServers": {
    "windows-mcp": {
      "command": "uvx",
      "args": ["windows-mcp", "serve"]
    }
  }
}
```

保存后到连接器管理页点击 **Trust** 启用。首次运行会从 PyPI 拉取依赖，可能较慢，属正常。

独立使用（无 MCP 宿主）：

```bash
uvx windows-mcp serve
```

## 🔧 依赖

- **必需**：Windows 系统 + 微信 Windows 桌面端 + Windows-MCP（主控制层）。
- **可选（仅离线备选脚本需要）**：Python 3.7+ 与 `pywinauto pyperclip pillow pywin32`。

```bash
# 仅当你不使用 Windows-MCP、想直接跑 scripts/wechat_send.py 时才需要
pip install pywinauto pyperclip pillow pywin32
```

## 🚀 使用方法

### 主流程：Windows-MCP 原生控制（推荐）

在支持 MCP 的宿主里直接调用 `windows-mcp` 工具：置顶微信 → `Screenshot` 读坐标 → `Click` 点列表项 → `Type` 落字回车 → `Screenshot` 核验。详见 SKILL.md「主流程」章节（含坐标换算 1.735 与三大坑）。

### 备选：命令行直接调用（pywinauto 离线脚本）

> 仅在无 Windows-MCP 环境时使用。

```bash
# 发送文本
python scripts/wechat_send.py --contact "好友昵称" --message "你好！"

# 从文件读取长文本发送（适合报告/长消息）
python scripts/wechat_send.py --contact "好友昵称" --message-file "report.txt"

# 发送图片
python scripts/wechat_send.py --contact "好友昵称" --image "C:\screenshot.png"

# 发送文件
python scripts/wechat_send.py --contact "好友昵称" --file "C:\document.pdf"

# 仅启动微信（不发送）
python scripts/wechat_send.py --launch-only
```

### 批次模式（推荐 Agent 多群 / 多图任务）

> 一条命令、单个进程处理多个群聊 + 多张图，**微信全程不关**，避免自主 Agent 在多次调用之间误关微信。

```bash
# 先准备 send_plan.json
python scripts/wechat_send.py --manifest send_plan.json

# 想顺手把窗口截图存下来核验（不关闭微信）
python scripts/wechat_send.py --manifest send_plan.json --screenshot D:/verify.png
```

`send_plan.json` 示例：

```json
[
  { "contact": "群聊A", "message": "xxx", "images": ["D:/pics/a.png"] },
  { "contact": "群聊B", "message": "xxx", "images": ["D:/pics/b.png"] }
]
```

字段：`contact`（必填）、`message` / `message_file`、`images`（数组）、`files`（数组）。脚本结尾输出 `[RESULT] total=N ok=M fail=K`，每组打 `[SENT_OK]` / `[SENT_FAIL]`。

### 在 OpenClaw / WorkBuddy 中触发

对话中说出以下触发词即可：

- "给 XXX 发微信：消息内容"
- "打开微信发消息给 XXX"
- "通过微信发给 XXX：内容"
- "微信发送 XXX"

### 被其他 Skill 调用（离线模式）

```python
import subprocess

subprocess.run([
    "python",
    "scripts/wechat_send.py",
    "--contact", "好友昵称",
    "--message", "B站播报内容..."
])
```

## 🔬 技术原理

### 主控制层：Windows-MCP

- 系统原生 API + 元素定位（Snapshot / Click / Type / App / Screenshot），不依赖猜类名 / 猜坐标。
- 微信 Qt 内核不进无障碍树，内部控件只能坐标点击。
- 坐标换算：Screenshot 图像坐标 × 1.735 ≈ Click / Type 的 `loc`（1920×1080 实测；换分辨率需重新标定）。

### 备选层：pywinauto（离线）

- 用 `pywinauto` 的 `uia` 后端，窗口标题必须为**中文"微信"**（不是 "WeChat"），主窗类名 `Chrome_WidgetWin_0`。
- 中文输入统一采用 **剪贴板 + Ctrl+V** 方案，避免直接键入中文的编码问题。
- 图片发送：转 BMP（去 14 字节文件头，取 DIB 数据）写入剪贴板 `CF_DIB`，聊天框 Ctrl+V 即发送。

## ⚠️ 注意事项

1. **🪟 Windows only**：本 Skill 仅支持 Windows 平台与微信 Windows 桌面端，**无 macOS 版**。
2. **微信窗口必须可见（已支持托盘自动恢复）**：v1.1.0 起即使被收进托盘也会自动还原前台；但 Agent 批次任务中请勿主动关闭 / 最小化微信（`×`/`Alt+F4` 仅最小化到托盘，关了会卡死后续）。
3. **登录状态**：通常自动登录，偶尔需要扫码确认。
4. **联系人名称**：精确匹配列表项 / 搜索结果第一个。
5. **UI 依赖**：依赖微信 Windows 版 UI 结构，大版本更新可能需重新标定坐标系数。
6. **仅发送，不读取**：本 Skill 不读取微信消息内容。

## 📁 文件结构

```
wechat-desktop/
├── SKILL.md              # Skill 定义（OpenClaw / WorkBuddy 识别用）
├── scripts/
│   └── wechat_send.py    # 备选：pywinauto 离线脚本（主流程走 Windows-MCP）
├── LICENSE               # MIT 开源协议
└── README.md            # 本文件
```

## 🤖 自主 Agent（Codex 等）驱动须知

- **绝不关闭微信**；Agent 也不要主动关 / 最小化微信窗口。
- **多群多图请用 `--manifest` 批次模式**（离线脚本），或走 Windows-MCP 单进程多步，从根上消除“多次调用间误关微信”。
- **校验用截图**，别靠“关了重开再瞅”。
- 若微信被收进托盘，重跑脚本 / 重新置顶即可自动还原，无需人工重开。

## 🐛 问题反馈

- SkillHub 评论区：https://skillhub.cn/skills/wechat-desktop-claw-automatic-control
- 或联系作者：微光浮影

## 📄 协议

Apache-2.0 License — 自由使用、修改、分发。详见 [LICENSE](LICENSE) 文件。
