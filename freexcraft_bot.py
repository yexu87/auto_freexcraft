#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeXcraft 多账号自动续时脚本 (含全屏广告处理 & 矩阵模式)
"""

import asyncio
import random
import os
import datetime
import requests
from datetime import timezone, timedelta
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# =====================================================================
#                         配置区域
# =====================================================================

# 运行模式配置
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
USE_HEADLESS = os.getenv("USE_HEADLESS", "true").lower() == "true"
WAIT_TIMEOUT = 30000  # 增加超时时间以应对广告加载

# 目标 URL
LOGIN_URL = "https://freexcraft.com/login"
DASHBOARD_URL = "https://freexcraft.com/servers/3ed9a4d5-b988-4e07-91da-891fe557f69f/dashboard"

# 通知配置
DEFAULT_TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
DEFAULT_TG_CHATID = os.getenv("TELEGRAM_CHAT_ID") or ""

# =====================================================================
#                         工具模块
# =====================================================================

def parse_accounts():
    """解析账号，支持单账号环境变量或批量 XSERVER_BATCH"""
    accounts = []
    raw_data = os.getenv("XSERVER_BATCH")
    
    if not raw_data:
        email = os.getenv("FX_EMAIL")
        pwd = os.getenv("FX_PASSWORD")
        if email and pwd:
            accounts.append({"email": email, "pass": pwd, "tg_token": DEFAULT_TG_TOKEN, "tg_chat": DEFAULT_TG_CHATID})
        return accounts

    for line in raw_data.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) >= 2:
            accounts.append({
                "email": parts[0], "pass": parts[1],
                "tg_token": parts[2] if len(parts) >= 4 else DEFAULT_TG_TOKEN,
                "tg_chat": parts[3] if len(parts) >= 4 else DEFAULT_TG_CHATID
            })
    return accounts

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send_msg(self, account, status, detail=""):
        if not (self.token and self.chat_id): return
        ts = datetime.datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        safe_email = account[:3] + "***" + account[account.find("@"):]
        msg = (f"<b>🎮 FreeXcraft 续时通知</b>\n"
               f"🆔 账号: <code>{safe_email}</code>\n"
               f"⏰ 时间: {ts}\n"
               f"📊 结果: <b>{status}</b>\n"
               f"📝 详情: {detail}")
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
        except: pass

# =====================================================================
#                         核心自动化类
# =====================================================================

class FreeXcraftBot:
    def __init__(self, account):
        self.email = account["email"]
        self.password = account["pass"]
        self.notifier = TelegramNotifier(account["tg_token"], account["tg_chat"])
        self.status = "Failed"
        self.detail = ""

    async def handle_popups(self, page):
        """处理登录前的隐私同意弹窗"""
        try:
            selectors = ["button:has-text('同意')", "button:has-text('Accept')", ".fc-cta-consent"]
            for s in selectors:
                btn = page.locator(s)
                if await btn.is_visible():
                    await btn.click()
                    print(f"[{self.email}] 已跳过隐私确认弹窗")
                    break
        except: pass

    async def clear_fullscreen_ads(self, page):
        """核心逻辑：检测并关闭全屏覆盖广告"""
        print(f"[{self.email}] 正在检测全屏广告遮罩...")
        await asyncio.sleep(5) # 给广告充足的弹出时间

        # 定义可能的关闭按钮特征
        close_selectors = [
            "button[aria-label='Close']", 
            ".modal-close", 
            "text='×'", 
            ".close-button",
            "i.fa-times",
            "div[class*='close']"
        ]

        # 1. 尝试直接点击关闭按钮
        for selector in close_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    # 检查是否在屏幕上方区域（通常关闭按钮在右上角）
                    box = await btn.bounding_box()
                    if box and box['y'] < 300: 
                        await btn.click()
                        print(f"✅ 已通过选择器关闭广告: {selector}")
                        await asyncio.sleep(2)
                        return
            except: continue

        # 2. 如果没找到明确按钮，尝试点击屏幕右上角位置 (坐标模拟)
        try:
            print(f"[{self.email}] 尝试模拟点击右上角关闭坐标...")
            await page.mouse.click(1200, 50) # 假设分辨率 1280 宽度
            await asyncio.sleep(2)
        except: pass

    async def run(self):
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=USE_HEADLESS)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await stealth_async(page)

            try:
                # --- 1. 登录阶段 ---
                print(f"🚀 [{self.email}] 正在访问登录页...")
                await page.goto(LOGIN_URL, wait_until="networkidle")
                await self.handle_popups(page)

                await page.fill("input[name='email']", self.email)
                await page.fill("input[name='password']", self.password)
                await page.click("button[type='submit']")
                await page.wait_for_load_state("networkidle")

                if "login" in page.url:
                    raise Exception("登录失败，请检查账号密码")

                # --- 2. 仪表盘阶段 ---
                print(f"🔗 [{self.email}] 跳转至服务器面板...")
                await page.goto(DASHBOARD_URL, wait_until="networkidle")

                # 处理广告遮罩
                await self.clear_fullscreen_ads(page)

                # --- 3. 续时操作 ---
                # 寻找 Renew 按钮
                renew_btn = page.locator("button:has-text('Renew'), button:has-text('续期'), button:has-text('续时')").first
                
                # 等待按钮可见且不被遮挡
                await renew_btn.wait_for(state="visible", timeout=15000)
                
                if await renew_btn.is_visible():
                    # 再次确保广告没遮挡点击
                    await renew_btn.scroll_into_view_if_needed()
                    await renew_btn.click()
                    
                    self.status = "Success"
                    self.detail = "成功关闭广告并点击续时按钮"
                    print(f"🎉 [{self.email}] 续时任务完成！")
                else:
                    self.status = "Warning"
                    self.detail = "进入了面板但未找到 Renew 按钮"

            except Exception as e:
                self.status = "Error"
                self.detail = str(e)
                print(f"❌ [{self.email}] 运行异常: {e}")
                # 保存截图以便排查广告样式
                if not IS_GITHUB_ACTIONS:
                    await page.screenshot(path=f"debug_{self.email}.png")
            
            finally:
                self.notifier.send_msg(self.email, self.status, self.detail)
                await browser.close()

# =====================================================================
#                           主入口
# =====================================================================

async def main():
    print("="*50)
    print("FreeXcraft 多账号自动续时工具")
    print("="*50)
    
    accounts = parse_accounts()
    if not accounts:
        print("❌ 未检测到有效账号配置，请设置 FX_EMAIL 或 XSERVER_BATCH")
        return

    target_idx = os.getenv("TARGET_INDEX")
    if target_idx is not None:
        idx = int(target_idx)
        if 0 <= idx < len(accounts):
            bot = FreeXcraftBot(accounts[idx])
            await bot.run()
    else:
        for acc in accounts:
            bot = FreeXcraftBot(acc)
            await bot.run()
            # 随机延迟防止被封
            await asyncio.sleep(random.randint(10, 30))

if __name__ == "__main__":
    asyncio.run(main())
