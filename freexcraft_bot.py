#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeXcraft 自动续时脚本 (Cookie 直通 + 广告处理版)
"""

import asyncio
import random
import os
import datetime
import json
import requests
from datetime import timezone, timedelta
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# =====================================================================
#                         配置区域
# =====================================================================

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
    
    # 优先读取单账号和 Cookie 配置
    email = os.getenv("FX_EMAIL") or "yexu87520a@2925.com"
    pwd = os.getenv("FX_PASSWORD") or "qweqwe12"
    cookie_str = os.getenv("FX_COOKIE")  # 新增：读取 Cookie 环境变量
    
    accounts.append({
        "email": email, 
        "pass": pwd, 
        "cookie": cookie_str,
        "tg_token": DEFAULT_TG_TOKEN, 
        "tg_chat": DEFAULT_TG_CHATID
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
        self.cookie_str = account.get("cookie")
        self.notifier = TelegramNotifier(account["tg_token"], account["tg_chat"])
        self.status = "Failed"
        self.detail = ""

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

    async def inject_cookies(self, context):
        """清洗并注入 Cookie"""
        if not self.cookie_str:
            return False
            
        try:
            raw_cookies = json.loads(self.cookie_str)
            clean_cookies = []
            for c in raw_cookies:
                # Playwright 只接受 Strict, Lax, None 这三种 sameSite 格式，其他的要删掉
                if "sameSite" in c and c["sameSite"].lower() not in ["strict", "lax", "none"]:
                    del c["sameSite"]
                # 名字带 copy 的冗余 cookie 可能会报错，直接跳过
                if "(copy" in c.get("name", ""):
                    continue
                clean_cookies.append(c)
                
            await context.add_cookies(clean_cookies)
            print(f"🍪 [{self.email}] 成功注入缓存的 Cookie！")
            return True
        except Exception as e:
            print(f"⚠️ [{self.email}] Cookie 注入失败，格式可能有误: {e}")
            return False

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
                # --- 1. 尝试 Cookie 直通 ---
                has_cookie = await self.inject_cookies(context)
                
                if has_cookie:
                    print(f"🔗 [{self.email}] 携带 Cookie 直接访问面板...")
                    await page.goto(DASHBOARD_URL, wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    # 检查是否被踢回了登录页
                    if "login" in page.url:
                        print(f"⚠️ [{self.email}] Cookie 已过期或失效，准备退回密码登录...")
                        has_cookie = False # 强制进入下面的密码登录流程
                    else:
                        print(f"✅ [{self.email}] 成功跳过登录！")

                # --- 2. 备用：密码登录 (仅当没 Cookie 或 Cookie 失效时执行) ---
                if not has_cookie:
                    print(f"🚀 [{self.email}] 使用密码访问登录页...")
                    await page.goto(LOGIN_URL, wait_until="networkidle")
                    
                    try:
                        btn = page.locator("button:has-text('同意')").first
                        if await btn.is_visible(): await btn.click()
                    except: pass

                    await page.fill("input[name='email']", self.email)
                    await page.fill("input[name='password']", self.password)
                    await page.click("button[type='submit']")
                    await page.wait_for_load_state("networkidle")

                    if "login" in page.url:
                        raise Exception("登录失败，被 Cloudflare 拦截或密码错误")

                    print(f"🔗 [{self.email}] 跳转至服务器面板...")
                    await page.goto(DASHBOARD_URL, wait_until="networkidle")

                # --- 3. 处理广告与续时 ---
                await self.clear_fullscreen_ads(page)

                renew_btn = page.locator("button:has-text('Renew'), button:has-text('续期'), button:has-text('续时')").first
                
                try:
                    await renew_btn.wait_for(state="visible", timeout=15000)
                except:
                    print(f"⚠️ [{self.email}] 15秒内未找到明确可见的续时按钮。")

                if await renew_btn.is_visible():
                    await renew_btn.scroll_into_view_if_needed()
                    await renew_btn.click()
                    self.status = "Success"
                    self.detail = "续时任务成功完成"
                    print(f"🎉 [{self.email}] {self.detail}！")
                else:
                    self.status = "Warning"
                    self.detail = "未找到可点击的 Renew 按钮"

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
    print("FreeXcraft 自动续时工具 (Cookie直通版)")
    print("="*50)
    
    accounts = parse_accounts()
    for acc in accounts:
        bot = FreeXcraftBot(acc)
        await bot.run()
        await asyncio.sleep(random.randint(5, 10))

if __name__ == "__main__":
    asyncio.run(main())
