#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚠️ 微信桌面端自动化脚本 ——【离线兼容备选】

平台：仅支持 Windows（本 Skill 无 macOS 版）。
依赖：pywinauto, pyperclip, pillow, pywin32
角色：本脚本是「离线兼容备选」，仅在【无 Windows-MCP 环境】时使用。
      主流程请走 Windows-MCP（github.com/CursorTouch/Windows-MCP）原生控制，更稳定。

功能：打开微信、搜索联系人、发送消息/图片/文件（支持批次多群聊一次进程完成）
微信路径：D:/Tencent/Weixin/Weixin.exe（注意：是 Weixin 不是 WeChat）
发送方式：Enter 键发送
版本：1.2.0（备选层，随 Skill 主版本同步）

────────────────────────────────────────────────────────────
针对 自主 Agent（Codex / WorkBuddy 等）驱动的适配要点：
  1. 本脚本【绝不】关闭 / 退出微信。微信由脚本启动时即作为独立进程运行，
     脚本进程退出也不会杀掉微信，窗口始终保留。
  2. 新增 --manifest 批次模式：一条命令处理 N 个群聊 + N 张图，
     整个批次在一个进程内完成，杜绝 Agent 在多次调用之间“手滑关微信”。
  3. 新增 --screenshot 截图校验：不关闭微信即可把聊天窗口存成 PNG，
     供 Agent 肉眼确认发送结果（替代“关了重开再检查”的笨办法）。
  4. 托盘 / 最小化自动恢复：即便微信被收进托盘，也能自动 ShowWindow 还原前台。
  5. 结构化输出：每组发送以 [GROUP] / [SENT_OK] / [SENT_FAIL] / [RESULT]
     标记，便于 Agent 解析成败，不必靠“关窗检查”来判断。
────────────────────────────────────────────────────────────
"""

import sys
import io
import time
import json
import subprocess
import argparse
from pathlib import Path

# 设置 stdout 为 UTF-8 编码，避免 Windows 控制台 GBK 编码错误
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from pywinauto import Application
    from pywinauto import findwindows
    from pywinauto.keyboard import send_keys
    import pyperclip
except ImportError as e:
    print(f"缺少依赖库：{e}")
    print("请运行：pip install pywinauto pyperclip pillow pywin32")
    sys.exit(1)

import ctypes

WECHAT_PATH = "D:/Tencent/Weixin/Weixin.exe"
TIMEOUT = 20
SW_RESTORE = 9
# 微信主窗专属类名（Chromium 内核 UI）；另有 Qt 子窗也标题为「微信」，故必须锁定主窗类名，
# 否则 uia connect 会因「2 个匹配」报 ElementAmbiguousError 而误判未运行、去乱拉实例
MAIN_CLASS = "Chrome_WidgetWin_0"


def log(msg):
    print(msg, flush=True)


def bring_to_foreground(hwnd):
    """强制把窗口从最小化/托盘还原到前台（尽力绕过 foreground lock）。"""
    try:
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def main_window_of(app):
    """取微信主窗（按主窗类名锁定，避开与 Qt 子窗的标题歧义）。"""
    return app.window(title_re="微信", class_name=MAIN_CLASS)


def launch_wechat():
    """启动微信（若已运行则直接连接），并稳妥还原到前台。

    注意：本函数【绝不】关闭微信。
    """
    # 优先连接已运行（含托盘还原后）的微信主窗口；连不上就拉起/还原
    try:
        app = Application(backend='uia').connect(title_re="微信", class_name=MAIN_CLASS, timeout=10)
        log("微信已在运行，直接连接")
        return app
    except Exception:
        pass

    # 微信在系统托盘/窗口不可枚举时，拉起可执行文件（单实例会还原主窗而非真重启）
    log("启动/还原微信...")
    subprocess.Popen(WECHAT_PATH)
    time.sleep(6)

    # 等待微信窗口出现
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        try:
            app = Application(backend='uia').connect(title_re="微信", class_name=MAIN_CLASS, timeout=2)
            log("微信启动成功")
            return app
        except Exception:
            time.sleep(1)

    log("无法连接微信，可能需要在手机上扫码确认登录")
    log("请扫码后重新运行脚本")
    sys.exit(1)


def get_main_window(app):
    """获取微信主窗口，确保可见且在前台（含托盘还原）。"""
    try:
        window = main_window_of(app)
        hwnd = window.handle
        bring_to_foreground(hwnd)
        time.sleep(0.6)
        if not window.is_visible():
            try:
                window.restore()
            except Exception:
                pass
            time.sleep(0.5)
            bring_to_foreground(hwnd)
            time.sleep(0.4)
        try:
            window.set_focus()
        except Exception:
            pass
        time.sleep(0.3)
        if window.is_active():
            log("✅ 微信窗口已激活")
        else:
            log("⚠️ 警告：微信窗口可能未在前台（已尽力还原，可继续）")
        return window
    except Exception as e:
        log(f"获取窗口失败：{e}")
        sys.exit(1)


def ensure_window(app):
    """批次任务中每次操作前调用：确保窗口还活着且在前台（防止被收进托盘）。

    不会关闭任何东西；若窗口被收进托盘则自动还原，若句柄丢失则重连。
    """
    try:
        window = main_window_of(app)
        if not window.is_visible():
            bring_to_foreground(window.handle)
            time.sleep(0.4)
            try:
                window.restore()
            except Exception:
                pass
            bring_to_foreground(window.handle)
            time.sleep(0.3)
        else:
            bring_to_foreground(window.handle)
            time.sleep(0.2)
        return window
    except Exception:
        # 窗口句柄丢失，尝试整体重连
        return get_main_window(app)


def ensure_logged_in(window):
    """冷启动/掉登录会停在「进入微信」确认页；自动点掉绿钮并完成登录。

    已登录（主界面）时登录钮不存在，函数静默返回。

    关键点：
      - 「进入微信」绿钮是微信自绘控件，uia 的 .click() 常常点不中，必须用 .click_input()
        （真实移动鼠标并按下）才能触发。
      - 登录后微信进入「正在进入」消息同步加载页，点完绿钮后固定等待同步即可。
      - 不再依赖读取主界面文字判定就绪（微信聊天列表/搜索框是自绘控件，uia 读不到文字）。
    """
    # 是否处于登录确认页：找「进入微信/登录/进入」按钮
    for label in ("进入微信", "登录", "进入"):
        try:
            btn = window.child_window(title=label, control_type="Button")
            if btn.exists(timeout=1):
                btn.click_input()
                log(f"✅ 已点击「{label}」完成登录，等待消息同步…")
                time.sleep(12)  # 消息同步加载（正在进入）需要时间
                return True
        except Exception:
            continue
    # 兜底：全树搜「进入微信」绿钮
    try:
        for ctrl in window.descendants(control_type="Button"):
            if "进入微信" in (ctrl.window_text() or ""):
                ctrl.click_input()
                log("✅ 已点击「进入微信」完成登录，等待消息同步…")
                time.sleep(12)
                return True
    except Exception:
        pass
    # 无登录钮 = 本来就是登录态
    log("✅ 已处于登录态（无需登录）")
    return True


def search_contact(window, name):
    """搜索并选中联系人"""
    log(f"搜索联系人：{name}")

    # Ctrl+F 打开搜索
    send_keys("^f")
    time.sleep(1)

    # 输入联系人名称
    pyperclip.copy(name)
    time.sleep(0.2)
    send_keys("^v")
    time.sleep(1.5)

    # 关键：微信搜索框直接回车会触发"搜一搜"联网搜索而非打开联系人；
    # 需先用方向键把焦点移入结果列表、选中首个匹配的联系人，再回车打开
    send_keys("{DOWN}")
    time.sleep(0.6)
    send_keys("{ENTER}")
    time.sleep(1)
    log(f"已选中联系人：{name}")


def send_text(window, text):
    """发送文本消息（Enter 发送）"""
    log(f"发送文本：{text[:60]}{'...' if len(text) > 60 else ''}")

    pyperclip.copy(text)
    time.sleep(0.2)
    send_keys("^v")  # 粘贴
    time.sleep(0.3)
    send_keys("{ENTER}")  # Enter 发送
    time.sleep(0.5)
    log("[SENT_OK] text")
    return True


def send_image(window, image_path):
    """发送图片（通过剪贴板 + Ctrl+V 粘贴到聊天框）"""
    import win32clipboard
    import win32con
    from PIL import Image

    log(f"发送图片：{image_path}")

    if not Path(image_path).exists():
        log(f"[SENT_FAIL] image not found: {image_path}")
        return False

    try:
        img = Image.open(image_path)
        output = io.BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # 去掉 BMP 文件头

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
        win32clipboard.CloseClipboard()

        time.sleep(0.3)
        send_keys("^v")  # Ctrl+V 粘贴图片
        time.sleep(1)
        send_keys("{ENTER}")  # Enter 发送
        log("[SENT_OK] image")
        return True
    except Exception as e:
        log(f"[SENT_FAIL] image error: {e}")
        log("请确保安装了 pywin32：pip install pywin32")
        return False


def send_file(window, file_path):
    """发送文件（通过 Ctrl+Alt+F 快捷键或点击 + 按钮）"""
    log(f"发送文件：{file_path}")

    if not Path(file_path).exists():
        log(f"[SENT_FAIL] file not found: {file_path}")
        return False

    try:
        # 尝试 Ctrl+Alt+F（微信发送文件快捷键）
        send_keys("^%f")  # Ctrl+Alt+F
        time.sleep(1.5)

        # 此时应出现文件选择对话框，输入文件路径
        pyperclip.copy(str(file_path))
        time.sleep(0.2)
        send_keys("^v")
        time.sleep(0.5)
        send_keys("{ENTER}")
        time.sleep(1)
        log("[SENT_OK] file")
        return True
    except Exception as e:
        log(f"[SENT_FAIL] file error: {e}")
        return False


def take_screenshot(window, path):
    """对微信窗口截图存为 PNG（用于 Agent 校验，绝不关闭微信）。"""
    try:
        img = window.capture_as_image()
        img.save(path)
        log(f"[SCREENSHOT] saved -> {path}")
        return True
    except Exception as e:
        log(f"[SCREENSHOT_FAIL] {e}")
        return False


def process_one(window, item):
    """处理单个群聊/联系人条目。window 全程保持打开，绝不关闭。"""
    contact = item.get("contact") or item.get("name")
    if not contact:
        log("[GROUP] skip: 缺少 contact 字段")
        return False
    log(f"[GROUP] contact={contact}")
    search_contact(window, contact)
    ok = True
    if item.get("message_file"):
        try:
            with open(item["message_file"], 'r', encoding='utf-8') as f:
                msg = f.read()
            log(f"从文件读取消息：{item['message_file']} ({len(msg)} 字符)")
            send_text(window, msg)
        except Exception as e:
            log(f"[SENT_FAIL] message_file: {e}")
            ok = False
    elif item.get("message"):
        send_text(window, item["message"])
    for img in (item.get("images") or []):
        if not send_image(window, img):
            ok = False
    for fl in (item.get("files") or []):
        if not send_file(window, fl):
            ok = False
    log(f"[GROUP_DONE] contact={contact} result={'ok' if ok else 'partial'}")
    return ok


def main():
    parser = argparse.ArgumentParser(description="微信桌面端自动化工具（支持批次）")
    parser.add_argument("--contact", help="联系人名称（单发模式）")
    parser.add_argument("--message", help="要发送的文本内容")
    parser.add_argument("--message-file", help="从文件读取要发送的文本内容（适用于长消息）")
    parser.add_argument("--image", help="要发送的图片路径")
    parser.add_argument("--file", help="要发送的文件路径")
    parser.add_argument("--launch-only", action="store_true", help="仅启动微信，不发送内容")
    parser.add_argument("--manifest", help="批次模式：JSON 文件，列出多个群聊/图片（推荐 Agent 多群任务使用）")
    parser.add_argument("--screenshot", help="发送完成后对微信窗口截图保存路径（用于校验，不关闭微信）")
    args = parser.parse_args()

    # 启动/连接微信（绝不关闭）
    app = launch_wechat()
    window = get_main_window(app)
    ensure_logged_in(window)  # 冷启动/掉登录时自动点「进入微信」完成登录

    if args.launch_only:
        log("微信已启动，可以开始使用了")
        if args.screenshot:
            take_screenshot(window, args.screenshot)
        return

    # ===== 批次模式（单进程处理多群，杜绝 Agent 多次调用间误关微信）=====
    if args.manifest:
        mpath = Path(args.manifest)
        if not mpath.exists():
            log(f"[ERROR] manifest 不存在：{args.manifest}")
            sys.exit(1)
        try:
            items = json.loads(mpath.read_text(encoding='utf-8'))
        except Exception as e:
            log(f"[ERROR] manifest 解析失败：{e}")
            sys.exit(1)
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            log("[ERROR] manifest 必须是 JSON 数组或对象")
            sys.exit(1)
        total = len(items)
        done = 0
        for idx, item in enumerate(items, 1):
            log(f"===== 批次进度 {idx}/{total} =====")
            window = ensure_window(app)  # 每组前确认窗口还活着/在前台（不关闭）
            if process_one(window, item):
                done += 1
        log(f"[RESULT] total={total} ok={done} fail={total - done}")
        if args.screenshot:
            take_screenshot(window, args.screenshot)
        return

    # ===== 单发模式（保持原有行为）=====
    if not args.contact:
        log("请指定 --contact 参数（或多群任务改用 --manifest 批次模式）")
        sys.exit(1)

    # 搜索并选中联系人
    search_contact(window, args.contact)

    # 发送内容
    if args.message_file:
        # 从文件读取消息内容
        try:
            with open(args.message_file, 'r', encoding='utf-8') as f:
                message = f.read()
            log(f"从文件读取消息：{args.message_file} ({len(message)} 字符)")
            send_text(window, message)
        except Exception as e:
            log(f"读取消息文件失败：{e}")
            sys.exit(1)
    elif args.message:
        send_text(window, args.message)

    if args.image:
        send_image(window, args.image)

    if args.file:
        send_file(window, args.file)

    if not any([args.message, args.message_file, args.image, args.file]):
        log("未指定要发送的内容，请使用 --message / --message-file / --image / --file 参数")

    if args.screenshot:
        take_screenshot(window, args.screenshot)


if __name__ == "__main__":
    main()
