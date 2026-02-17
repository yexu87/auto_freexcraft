#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeXcraft 自动续时脚本 (Cookie直通 + 暴力破除遮罩版)
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

# 👇 直接写死了你提取的完整 Cookie 用于调试
DEBUG_COOKIE = """[
  {
    "name": "__eoi",
    "value": "ID=3e34cf426b3ec53e:T=1771163663:RT=1771350711:S=AA-AfjYiGHdk43MLwjhVxQrTsMDI",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1786715663,
    "httpOnly": false,
    "secure": true,
    "sameSite": "no_restriction"
  },
  {
    "name": "__gads",
    "value": "ID=66a6f9444d656fb7:T=1771163663:RT=1771350711:S=ALNI_MYQzDh7I9kpLDkBiLo9I2sVYFW_Hg",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1804859663,
    "httpOnly": false,
    "secure": true,
    "sameSite": "no_restriction"
  },
  {
    "name": "__gpi",
    "value": "UID=0000135b392b25f8:T=1771163663:RT=1771350711:S=ALNI_MbQZrY5uBHAbwNVubW13ju8jMByKg",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1804859663,
    "httpOnly": false,
    "secure": true,
    "sameSite": "no_restriction"
  },
  {
    "name": "_ga",
    "value": "GA1.1.1109323617.1770991645",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1805910712.147659,
    "httpOnly": false,
    "secure": false,
    "sameSite": "unspecified"
  },
  {
    "name": "_ga_8KHW58GCFV",
    "value": "GS2.1.s1771350296$o13$g1$t1771350743$j24$l0$h1578333337",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1805910743.137127,
    "httpOnly": false,
    "secure": false,
    "sameSite": "unspecified"
  },
  {
    "name": "_tea_utm_cache_10000007",
    "value": "undefined",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1771596441,
    "httpOnly": false,
    "secure": false,
    "sameSite": "unspecified"
  },
  {
    "name": "FCCDCF",
    "value": "%5Bnull%2Cnull%2Cnull%2C%5B%22CQfkB8AQfkB8AEsACBZHCSFoAP_gAEPgACJwK1IB_C7EbCFCiDJ3IKMEMAhHABBAYsAwAAYBAwAADBIQIAQCgkEYBASAFCACCAAAKASBAAAgCAAAAUAAIAAFAABAAAwAIBAIIAAAgAAAAEAIAAAACIAAEQCAAAAEAEAAkAgAAAIASAAAAAAAAACBAAAAAAAAAAAAAAAABAEAAQAAQAAAAAAAiAAAAAAAABAIAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAABAAAAAAAQWEQD-F2I2EKFEGCuQUYIYBCuACAAxYBgAAwCBgAAGCQgQAgFJIIkCAEAIEAAEAAAQAgCAABQEBAAAIAAAAAqAACAABgAQCAQAIABAAAAgIAAAAAAEQAAIgEAAAAIAIABABAAAAQAkAAAAAAAAAECAAAAAAAAAAAAAAAAAAIAAEABgAAAAAABEAAAAAAAACAQIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAA.ILCIB_C7EbCFCiDJ3IKMEMAhXABBAYsAwAAYBAwAADBIQIAQCkkEaBASAFCACCAAAKASBAAAoCAgAAUAAIAAVAABAAAwAIBAIIEAAgAAAQEAIAAAACIAAEQCAAAAEAEAAkAgAAAIASAAAAAAAAACBAAAAAAAAAAAAAAAABAEAASAAwAAAAAAAiAAAAAAAABAIEAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAABAAAAAAAQAAAE%22%2C%222~61.89.122.161.184.196.230.314.442.445.494.550.576.827.1029.1033.1046.1047.1051.1097.1126.1166.1301.1342.1415.1725.1765.1942.1958.1987.2068.2072.2074.2107.2213.2219.2223.2224.2328.2331.2387.2416.2501.2567.2568.2575.2657.2686.2778.2869.2878.2908.2920.2963.3005.3023.3126.3234.3235.3253.3309.3731.6931.8931.13731.15731.33931~dv.%22%2C%222A146546-4501-449D-B761-83CEF7A793CA%22%5D%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%22032ad8b8-bf97-4eb2-ac92-06ebb994dec8%5C%22%2C%5B1770991641%2C688000000%5D%5D%22%5D%5D%5D",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1804687645,
    "httpOnly": false,
    "secure": false,
    "sameSite": "unspecified"
  },
  {
    "name": "FCNEC",
    "value": "%5B%5B%22AKsRol_7agnqnPUer1OgVrMOlskJgG5AXo8dOqlaMl5AbzEmP4aCK_me8gnge2DG4Ydvx9Z1O1zPTDMpAkl9LVilv7BMIEDwNx10QKKCtfMQYGNjJFq2oOOwg3zBMfeT8iDeuY4-zN_FaX_SE75sr2B5s2rxWCxRqw%3D%3D%22%5D%5D",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1802886712,
    "httpOnly": false,
    "secure": false,
    "sameSite": "unspecified"
  },
  {
    "name": "freexcraft_session",
    "value": "eyJpdiI6IldxNkR2UDJXQXA4dWxJZ2xhVldhRnc9PSIsInZhbHVlIjoiYXhXT250K1hkSmR2Z1hqK1krT1daaWxkcGdoSUsxdUpKUUV3cmM0a0RjVUx4WEN4cm1TVVZ0RExQa1V6Mml2ZThKUTVXaXFYSTdSRUF1L0R3dnJESkR0eC9uaitnS1VNc0RTdUp6R2dVRmVXUjBIUEVaVmpOMkNON3dxYzYzMy8iLCJtYWMiOiJkYjVjOTVkNThiYmU2MDY3YjFiZmUwNGRjYTFiYjIyMmFkYjAzYTRhOGNkZTk5YTBmOTMzMjgwMDc1YTBhZjVjIiwidGFnIjoiIn0%3D",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1771609934.186529,
    "httpOnly": true,
    "secure": true,
    "sameSite": "lax"
  },
  {
    "name": "freexcraft_session (copy 2)",
    "value": "eyJpdiI6IldxNkR2UDJXQXA4dWxJZ2xhVldhRnc9PSIsInZhbHVlIjoiYXhXT250K1hkSmR2Z1hqK1krT1daaWxkcGdoSUsxdUpKUUV3cmM0a0RjVUx4WEN4cm1TVVZ0RExQa1V6Mml2ZThKUTVXaXFYSTdSRUF1L0R3dnJESkR0eC9uaitnS1VNc0RTdUp6R2dVRmVXUjBIUEVaVmpOMkNON3dxYzYzMy8iLCJtYWMiOiJkYjVjOTVkNThiYmU2MDY3YjFiZmUwNGRjYTFiYjIyMmFkYjAzYTRhOGNkZTk5YTBmOTMzMjgwMDc1YTBhZjVjIiwidGFnIjoiIn0%3D",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1771609934.186529,
    "httpOnly": true,
    "secure": true,
    "sameSite": "lax"
  },
  {
    "name": "freexcraft_session (copy)",
    "value": "eyJpdiI6IkNvaEN3a0NJTUE1K3gwQjB5MnF3Unc9PSIsInZhbHVlIjoiZzFMNWtENHdwZVg3UXN1bGFBTjBJa2ZKUGUzK2o4aGphaXRJSSt3b2F4K0RUQTBzYm1kV3EvYjdmeloyTEJvRXVla0puSzZzUXdsZnNNUE85QmFCSE9NamtPQjU2cDRHTC9FMDNSQlJYeWtnc3VHUmZzL3R3bCtWczZLcEJ5dGUiLCJtYWMiOiJjYzc2NjkwMzhkNTZlYjQ0OGFhOGI5MWI5MDUwMmViOTllYmViODY2ZjdhZmQ3NGUyZDZlMDMwYzA4M2M2YTkyIiwidGFnIjoiIn0%3D",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1771609537.568516,
    "httpOnly": true,
    "secure": true,
    "sameSite": "lax"
  },
  {
    "name": "XSRF-TOKEN",
    "value": "eyJpdiI6IksyKzg2OS9PNDNBdHZhd1o1L050R1E9PSIsInZhbHVlIjoiWlA3b2NqNDZyeCtPVlZtc2VEeFdUVms3a3U2NW5RUEgzTnJLaHdqY1hLSGdpYmJNUDFVMjhCTTBjVGl2R29nT2x3cGdNQTdzYmZxZ3JlU2FhMmgvd2VTaGhkbXdGTWdQaUVMZlU3b2RwMkJRYnlyT1hWL2Y2bjBWUzZjbDlPSjciLCJtYWMiOiIzNGI5ZWZmZmUxZmY4ZTFiMzEyZTVmYWQwZGIzNzI5YzczMGIxNTczNGYzMTE0ZGJhY2Y5NWMxZjIxMDE1YWQ2IiwidGFnIjoiIn0%3D",
    "domain": ".freexcraft.com",
    "path": "/",
    "expires": 1771609934.186278,
    "httpOnly": false,
    "secure": true,
    "sameSite": "lax"
  }
]"""

# =====================================================================
#                         工具模块
# =====================================================================

def parse_accounts():
    accounts = []
    
    email = os.getenv("FX_EMAIL") or "yexu87520a@2925.com"
    pwd = os.getenv("FX_PASSWORD") or "qweqwe12"
    cookie_str = DEBUG_COOKIE
    
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
        print(f"[{self.email}] 正在执行全方位弹窗/遮罩清理...")
        await asyncio.sleep(4) 
        
        # 1. 尝试点击常见的各种“同意/确认”按钮
        try:
            for text in ['同意', 'Accept', 'Got it', 'I Agree']:
                btn = page.locator(f"button:has-text('{text}')").first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    print(f"✅ 点击了弹窗同意按钮: {text}")
                    await asyncio.sleep(1)
        except: pass

        # 2. 暴力移除法：向网页注入 JS，物理摧毁带有 z-[100] 或毛玻璃类的 Div
        try:
            await page.evaluate("""
                const overlays = document.querySelectorAll('div');
                overlays.forEach(div => {
                    if (div.className.includes('z-[100]') || div.className.includes('backdrop-blur')) {
                        div.remove();
                    }
                });
            """)
            print("✅ 暴力清理执行完毕，直接删除了所有底层遮罩！")
            await asyncio.sleep(1)
        except Exception as e:
            pass
            
        # 3. 按 ESC 键尝试退出普通弹窗
        try:
            await page.keyboard.press('Escape')
        except: pass

    async def inject_cookies(self, context):
        """清洗并注入 Cookie"""
        if not self.cookie_str:
            return False
            
        try:
            raw_cookies = json.loads(self.cookie_str)
            clean_cookies = []
            for c in raw_cookies:
                if "sameSite" in c:
                    val = c["sameSite"].lower()
                    if val == "strict":
                        c["sameSite"] = "Strict"
                    elif val == "lax":
                        c["sameSite"] = "Lax"
                    elif val == "none":
                        c["sameSite"] = "None"
                    else:
                        del c["sameSite"]
                        
                if "(copy" in c.get("name", ""):
                    continue
                clean_cookies.append(c)
                
            await context.add_cookies(clean_cookies)
            print(f"🍪 [{self.email}] 成功注入内置的调试 Cookie！")
            return True
        except Exception as e:
            print(f"⚠️ [{self.email}] Cookie 注入失败: {e}")
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
                    await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(5) 
                    
                    if "login" in page.url:
                        print(f"⚠️ [{self.email}] Cookie 已过期，退回密码登录...")
                        has_cookie = False 
                    else:
                        print(f"✅ [{self.email}] 成功跳过登录！")

                # --- 2. 备用：密码登录 ---
                if not has_cookie:
                    print(f"🚀 [{self.email}] 使用密码访问登录页...")
                    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(3)
                    
                    try:
                        btn = page.locator("button:has-text('同意')").first
                        if await btn.is_visible(): await btn.click()
                    except: pass

                    await page.fill("input[name='email']", self.email)
                    await page.fill("input[name='password']", self.password)
                    await page.click("button[type='submit']")
                    
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
                    await asyncio.sleep(3)

                    if "login" in page.url:
                        raise Exception("登录失败，被 Cloudflare 拦截或密码错误")

                    print(f"🔗 [{self.email}] 跳转至服务器面板...")
                    await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=45000)

                # --- 3. 处理广告与续时 ---
                await self.clear_fullscreen_ads(page)

                renew_btn = page.locator("button:has-text('Renew'), button:has-text('续期'), button:has-text('续时'), button:has-text('Renew Time')").first
                
                try:
                    # 只要节点附着到 DOM 就认为找到了，不管上面有没有遮挡
                    await renew_btn.wait_for(state="attached", timeout=15000)
                except:
                    print(f"⚠️ [{self.email}] 15秒内未找到续费按钮元素。")

                if await renew_btn.count() > 0:
                    await renew_btn.scroll_into_view_if_needed()
                    print(f"🎯 找到了续期按钮，正在尝试点击...")
                    try:
                        # 尝试正常点击，如果被挡住，马上进 except 走强行穿透
                        await renew_btn.click(timeout=3000)
                    except Exception:
                        print(f"🛡️ 按钮仍被无形结界遮挡，启动【强行穿透点击】！")
                        # force=True 会无视任何弹窗、遮罩、层级，直接命中目标坐标
                        await renew_btn.click(force=True)
                        
                    self.status = "Success"
                    self.detail = "续时操作触发成功"
                    print(f"🎉 [{self.email}] {self.detail}！")
                else:
                    self.status = "Warning"
                    self.detail = "进入了面板，但未找到可点击的 Renew 按钮"

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
    print("FreeXcraft 自动续时工具 (最终杀招版)")
    print("="*50)
    
    accounts = parse_accounts()
    for acc in accounts:
        bot = FreeXcraftBot(acc)
        await bot.run()
        await asyncio.sleep(random.randint(5, 10))

if __name__ == "__main__":
    asyncio.run(main())
