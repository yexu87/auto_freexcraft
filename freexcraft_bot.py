#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeXcraft 多账号自动续时脚本 (含全屏广告处理 & 矩阵模式)
调试版 - 已内置测试账号
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

IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
USE_HEADLESS = os.getenv("USE_HEADLESS", "true").lower() == "true"
WAIT_TIMEOUT = 30000

LOGIN_URL = "https://freexcraft.com/login"
DASHBOARD_URL = "https://freexcraft.com/servers/3ed9a4d5-b988-4e07-91da-891fe557f69f/dashboard"

DEFAULT_TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
DEFAULT_TG_CHATID = os.getenv("TELEGRAM_CHAT_ID") or ""

# =====================================================================
#                         工具模块
# =====================================================================

def parse_accounts():
    accounts = []
    raw_data = os.getenv("XSERVER_BATCH")
    
    if not raw_data:
        # 修改点：在这里加入了默认的调试账号和密码
        email = os.getenv("FX_EMAIL") or "yexu87520a@2925.com"
        pwd = os.getenv("FX_PASSWORD") or "qweqwe12"
        
        if email and pwd:
            accounts.append({
                "email": email, 
                "pass": pwd, 
                "tg_token": DEFAULT_TG_TOKEN, 
                "tg_chat": DEFAULT_TG_CHATID
            })
        return accounts

    for line in raw_data.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): 
            continue
        
        parts = [p.strip() for p in line.replace(",", ",").split(",")]
        
        if len(parts) >= 2:
            accounts.append({
                "email": parts[0], 
                "pass": parts[1],
                "tg_token": parts[2] if len(parts) >= 4 else DEFAULT_TG_TOKEN,
                "tg_chat": parts[3] if len(parts) >= 4 else DEFAULT_TG_CHATID
            })
    return accounts

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send_msg(self, account, status, detail=""):
        if not (self.token and self.chat_id): 
            return
            
        ts = datetime.datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        safe_email = account[:3] + "***" + account[account.find("@"):] if "@" in account else account
        
        msg = (f"<b>🎮 FreeXcraft 续时通知</b>\n"
               f"🆔 账号: <code>{safe_email}</code>\n"
               f"⏰ 时间: {ts}\n"
               f"📊 结果: <b>{status}</b>\n"
               f"📝 详情: {detail}")
               
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
        except: 
            pass

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
        try:
            selectors = ["button:has-text('同意')", "button:has-text('Accept')", ".fc-cta-consent"]
            for s in selectors:
                btn = page.locator(s).first
                if await btn.is_visible():
                    await btn.click()
                    print(f"[{self.email}] 已跳过隐私确认弹窗")
                    break
        except: 
            pass

    async def clear_fullscreen_ads(self, page):
        print(f"[{self.email}] 正在检测全屏广告遮罩...")
        await asyncio.sleep(5) 

        close_selectors = [
            "button[aria-label='Close']",
            ".modal-close",
            "text='×'",
            ".close-button",
            "i.fa-times",
            "div[class*='close']"
        ]

        for selector in close_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    box = await btn.bounding_box()
                    if box and box['y'] < 300: 
                        await btn.click()
                        print(f"✅ 已通过选择器关闭广告: {selector}")
                        await asyncio.sleep(2)
                        return
            except: 
                continue

        try:
            print(f"[{self.email}] 尝试模拟点击右上角关闭坐标...")
            await page.mouse.click(1200, 50) 
            await asyncio.sleep(2)
        except: 
            pass

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=USE_HEADLESS)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await stealth_async(page)

            try:
                # 1. 登录
                print(f"🚀 [{self.email}] 正在访问登录页...")
                await page.goto(LOGIN_URL, wait_until="networkidle")
                await self.handle_popups(page)

                await page.fill("input[name='email']", self.email)
                await page.fill("input[name='password']", self.password)
                await page.click("button[type='submit']")
                await page.wait_for_load_state("networkidle")

                if "login" in page.url:
                    raise Exception("登录失败,请检查账号密码")

                # 2. 仪表盘
                print(f"🔗 [{self.email}] 跳转至服务器面板...")
                await page.goto(DASHBOARD_URL, wait_until="networkidle")

                # 处理广告
                await self.clear_fullscreen_ads(page)

                # 3. 续时
                renew_btn = page.locator("button:has-text('Renew'), button:has-text('续期'), button:has-text('续时')").first
                
                try:
                    await renew_btn.wait_for(state="visible", timeout=15000)
                except:
                    print(f"⚠️ [{self.email}] 15秒内未找到明确可见的续时按钮。")

                if await renew_btn.is_visible():
                    await renew_btn.scroll_into_view_if_needed()
                    await renew_btn.click()
                    self.status = "Success"
                    self.detail = "成功关闭广告并点击续时按钮"
                    print(f"🎉 [{self.email}] 续时任务完成！")
                else:
                    self.status = "Warning"
                    self.detail = "进入了面板但未找到可点击的 Renew 按钮"

            except Exception as e:
                self.status = "Error"
                self.detail = str(e)
                print(f"❌ [{self.email}] 运行异常: {e}")
                
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
        print("❌ 未检测到有效账号配置")
        return

    target_idx = os.getenv("TARGET_INDEX")
    if target_idx is not None:
        try:
            idx = int(target_idx)
            if 0 <= idx < len(accounts):
                bot = FreeXcraftBot(accounts[idx])
                await bot.run()
        except ValueError:
            print("❌ TARGET_INDEX 格式错误")
    else:
        for acc in accounts:
            bot = FreeXcraftBot(acc)
            await bot.run()
            await asyncio.sleep(random.randint(10, 30))

if __name__ == "__main__":
    asyncio.run(main())
