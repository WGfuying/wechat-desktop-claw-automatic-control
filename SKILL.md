---
name: 微信 PC 端自动控制
description: 在 Windows 端通过 Windows-MCP 原生控制微信桌面端，向指定联系人发送消息、图片、文件（仅支持 Windows，暂无 macOS 版）。触发词：给某人发微信、打开微信发消息、微信发送、通过微信发给。也支持被其他 Skill 调用，实现自动化推送。
version: 1.2.0
author: 微光浮影
homepage: https://skillhub.cn/skills/wechat-desktop-claw-automatic-control
license: Apache-2.0
platform: windows
slug: wechat-desktop-claw-automatic-control
tags:
  - wechat
  - automation
  - windows-mcp
  - windows
  - mcp
---

# 微信 PC 端自动控制 v1.2.0

> ⚠️ **平台支持：Windows only（仅支持 Windows）**
> 本 Skill **仅支持 Windows 平台**，依赖「微信 Windows 桌面端」+「Windows-MCP」原生控制。
> **暂无 macOS 版**，也不支持微信 macOS 客户端。任何跨平台打包 / 上架 / 分发时，**务必保留此声明**，避免 macOS 用户体验到「装了用不了」。

通过 **Windows-MCP**（[github.com/CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP)）原生控制微信 Windows 桌面端，实现消息 / 图片 / 文件的自动发送。走系统原生 API + 元素定位，比猜类名 / 猜坐标的 pywinauto 野路子稳一个次元。

**本 Skill 完全开源，源代码公开（MIT）。**

## 更新日志

### v1.2.0（依赖切换：Windows-MCP 上位，2026-10-24）

- 🔄 **主依赖从 `pywinauto` 切换为 `Windows-MCP`**：自动化走系统原生 API，稳定度跨一个层级，且不会再出现「猜错主窗类名 → 误拉微信实例 → 逼用户重登」的事故。
- 🪟 **明确平台声明：Windows only，暂无 macOS 版**（元数据 `platform: windows` + 正文顶部警示框，打包 / 上架时务必保留）。
- 📌 **`pywinauto` 脚本降级为「离线兼容备选」**：仅在无 Windows-MCP 环境（纯命令行、无 MCP 宿主）时备用，不再是首选。

### v1.1.0（针对自主 Agent 驱动适配）

- 🆕 **批次模式 `--manifest`**：一条命令、单个进程处理多个群聊 + 多张图，杜绝 Agent 在多次调用之间误关微信。
- 🆕 **截图校验 `--screenshot`**：不关闭微信即可把聊天窗口存成 PNG，供 Agent 肉眼核验发送结果。
- 🆕 **托盘 / 最小化自动恢复**：即使微信被收进托盘，也会自动 `ShowWindow(SW_RESTORE)` + 置前台还原，无需人工重开。
- 🆕 **结构化输出**：`[SENT_OK]` / `[SENT_FAIL]` / `[RESULT]` 标记，便于 Agent 解析成败。
- 🔒 **脚本绝不关闭微信**：任何路径都不会退出微信进程。

### v1.0.1

- 🔓 **源代码完全公开**，MIT 协议。
- 添加 LICENSE / README.md，SKILL.md 补充 homepage / license / tags 字段。

## 功能

- 打开微信桌面端（如未运行则自动启动，且**绝不退出**）
- 定位联系人 / 群聊（点左侧列表项，避开搜索框歧义）
- 发送文本消息（支持长文本从文件读取）
- 发送图片（Windows-MCP 走剪贴板 / pywinauto 备选走 DIB 剪贴板）
- 发送文件
- 被其他 Skill 调用于自动化推送

## 环境要求

- **Windows 系统**（必需，本 Skill 仅支持 Windows）
- 微信 Windows 桌面端已安装并登录
- **Windows-MCP**（主控制层，必需）：本地 stdio 免鉴权，提供 Screenshot / Snapshot / Click / Type / App 等原生工具
- Python 3.7+（**仅**「备选：pywinauto 脚本」需要，主流程不需要）

## 安装

### 1. 安装并启用 Windows-MCP（主依赖）

在 WorkBuddy 客户端的 MCP 配置（`~/.workbuddy/mcp.json`）中加入：

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

保存后，到连接器管理页点击 **Trust** 启用即可。首次运行会从 PyPI 拉取依赖（可能较慢，属正常，并非卡死）。

> 独立使用（非 WorkBuddy 宿主）：直接 `uvx windows-mcp serve`，本地 stdio 直连。

### 2.（可选）pywinauto 备选脚本依赖

仅当你**不使用 Windows-MCP**、想直接跑 `scripts/wechat_send.py` 时才需要：

```bash
pip install pywinauto pyperclip pillow pywin32
```

## 主流程：Windows-MCP 原生控制（推荐）

在 WorkBuddy / 任何支持 MCP 的宿主里，**首选走 `windows-mcp` 的 MCP 工具** 完成微信自动化。配置写进 `~/.workbuddy/mcp.json`（`uvx windows-mcp serve`，本地 stdio 免鉴权）。

**端到端实测已跑通**：强制置顶微信 → 点左侧列表「文件传输助手」→ 输入框落字 → 回车发送，消息真进聊天记录（绿色气泡可见，非乐观回执）。

### ⚠️ 三个必须知道的坑（踩过的血泪）

1. **坐标系统不一致（最关键）**：`Screenshot` 返回的截图是 1920×1080 图像坐标，但 `Click` / `Type` 的 `loc` 用的是**另一套（窗口 / DPI 缩放）坐标**。实测换算关系：`Click坐标 ≈ 图像坐标 × 1.735`（即图像 ≈ Click × 0.577）。
   **正确做法**：每次点前先 `Screenshot` 读图像坐标 → 乘 1.735 得 Click 坐标 → 点完再 `Screenshot` 核验落点。绝不可复用上一张图的坐标（窗口会轻微位移）。

2. **微信 Qt 内核不进 Windows 无障碍树**：`Snapshot` 把微信显示成叶子节点 `window "微信"`，拿不到内部列表 / 输入框的元素 ID。**所以无法用 `label` 按 ID 点微信内部控件，只能坐标点击**。这也是 pywinauto 当年栽的根——不是工具问题，是微信 UI 的限制。

3. **别用搜索框开聊天**：在搜索框输入名字后按 Enter，会打开「搜一搜」面板而不是聊天窗（顶部搜索建议抢先命中）。**正确做法**：直接点左侧聊天列表里的联系人项（常用联系人如「文件传输助手」都在列表里），精准避开歧义。

### 标准流程（发「文件传输助手」为例）

```text
1. App(mode="switch", name="微信")        # 强制置顶，避免被宿主盖住
2. Screenshot(use_annotation=true)        # 读微信窗口 + 列表项图像坐标
3. Click(loc=[x*1.735, y*1.735])         # 点「文件传输助手」列表项，开聊天
4. Screenshot → 确认右侧聊天打开、输入框有闪烁光标
5. Type(text="…", loc=[输入框图像坐标*1.735], press_enter=true)  # 落字+回车发送
6. Screenshot → 核验绿色气泡出现在聊天记录
```

### 注意事项

- 窗口 z-order 不稳：宿主常抢前台盖住微信，**每个截图 / 点击前都先 `App switch 微信` 置顶**。
- 打开聊天后输入框通常已自动获焦（闪烁光标），`Type` 时 `loc` 填输入框坐标即可，不必额外点。
- 坐标换算系数 1.735 是特定分辨率 (1920×1080) 下实测值；换分辨率需重新标定（点一个已知点 → 比对落点 → 算系数）。
- 仍遵守「工具绝不关闭微信」铁律（`×` / `Alt+F4` 只是收托盘，关了反而卡死）。

## 备选：pywinauto 脚本（离线兼容模式）

> 仅在**无 Windows-MCP 环境**（例如纯命令行、无 MCP 宿主）时备用。有 Windows-MCP 时请走上方主流程。

`scripts/wechat_send.py` 是 pywinauto 实现的离线版本，单进程、支持批次（`--manifest`）与截图核验（`--screenshot`），且绝不关闭微信。

```bash
# 发送文本
python scripts/wechat_send.py --contact "好友昵称" --message "你好，这是自动发送的消息"

# 从文件读取长文本发送
python scripts/wechat_send.py --contact "好友昵称" --message-file "report.txt"

# 发送图片
python scripts/wechat_send.py --contact "好友昵称" --image "C:\path\to\image.png"

# 发送文件
python scripts/wechat_send.py --contact "好友昵称" --file "C:\path\to\file.pdf"

# 批次：一条命令处理多群 + 多图（微信全程不关）
python scripts/wechat_send.py --manifest send_plan.json

# 批次 + 截图核验（不关闭微信）
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

**被其他 Skill 调用**（离线模式）：

```python
import subprocess
subprocess.run([
    "python", "scripts/wechat_send.py",
    "--contact", "好友昵称", "--message", "消息内容"
])
```

## 技术说明

### 主控制层：Windows-MCP

- 走系统原生 API + 元素定位（Snapshot / Click / Type / App / Screenshot），不依赖猜类名 / 猜坐标。
- 微信 Qt 内核不进无障碍树，内部控件只能坐标点击（见上方「坑 2」）。
- 坐标换算：图像坐标 × 1.735 ≈ Click / Type 的 `loc`（1920×1080 实测）。

### 备选层：pywinauto（离线）

- 用 `pywinauto` 的 `uia` 后端连接微信主窗，**窗口标题必须为"微信"**（不是 "WeChat"）。
- 主窗类名为 `Chrome_WidgetWin_0`；另有 Qt 子窗也标题为「微信」，必须锁定主窗类名，否则 `uia.connect` 因「2 个匹配」报 `ElementAmbiguousError`。
- 中文输入统一走**剪贴板 + Ctrl+V**，避免 pywinauto 直接键入中文的编码问题。
- 图片发送：转 BMP（去 14 字节文件头，取 DIB 数据）写入剪贴板 `CF_DIB`，聊天框 Ctrl+V 即发送。
- 快捷键：发送 `Enter`、打开搜索 `Ctrl+F`、打开文件选择 `Ctrl+Alt+F`。

## 限制与注意事项

1. **🪟 Windows only**：本 Skill 仅支持 Windows 平台与微信 Windows 桌面端，**无 macOS 版**。打包 / 上架 / 分发请保留此声明。
2. **微信窗口必须可见（已支持托盘自动恢复）**：自动化需要窗口在前台。即使被收进托盘也会自动 `ShowWindow` 还原；但批次任务中**不要主动关闭 / 最小化**微信（`×`/`Alt+F4` 仅最小化到托盘，关了反而卡死后续）。
3. **登录状态**：通常自动登录，偶尔需要扫码（脚本 / 工具会提示）。
4. **联系人名称**：必须精确匹配列表项 / 搜索结果第一名。
5. **UI 依赖**：依赖微信 Windows 版 UI 结构，微信大版本更新可能需重新标定坐标系数。
6. **不能读取消息**：本 Skill 只发送，不读取微信消息内容。

## 源代码结构

```
wechat-desktop/
├── SKILL.md              # Skill 定义文件（本文件）
├── scripts/
│   └── wechat_send.py    # 备选：pywinauto 离线脚本（主流程走 Windows-MCP，本脚本仅在无 MCP 时备用）
├── LICENSE               # MIT 开源协议
└── README.md            # 说明文档
```

## 报告问题

SkillHub 评论区：https://skillhub.cn/skills/wechat-desktop-claw-automatic-control
