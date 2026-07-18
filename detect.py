#!/usr/bin/env python3
"""
朱雀 AI 检测自动化（完整版）
原理：用 Playwright 加载已保存的 storage_state（含 fp），
在浏览器同源环境下走页面自身的 WebSocket 检测流程。
"""

import asyncio, json, re, sys, os
from playwright.async_api import async_playwright

STATE_PATH = os.path.expanduser("~/.openclaw/workspace/.zhuque-state.json")

async def detect_via_page(text: str, state_path=STATE_PATH) -> dict:
    """通过 Playwright 页面直接调用朱雀检测"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            storage_state=state_path if os.path.exists(state_path) else None,
            locale="zh-CN"
        )
        page = await ctx.new_page()
        
        # 安全地捕获 WebSocket 消息（防事件错误传播）
        ws_messages = []
        
        def on_web_socket(ws):
            def on_sent(data):
                try:
                    if isinstance(data, str):
                        ws_messages.append(("sent", data))
                except Exception as e:
                    print(f"[ws sent err] {e}")
            def on_recv(data):
                try:
                    if isinstance(data, str):
                        ws_messages.append(("recv", data))
                except Exception as e:
                    print(f"[ws recv err] {e}")
            ws.on("framesent", on_sent)
            ws.on("framereceived", on_recv)
        
        page.on("websocket", on_web_socket)
        
        # 访问页面
        await page.goto("https://matrix.tencent.com/ai-detect/", wait_until="networkidle")
        await page.wait_for_timeout(4000)
        
        # 确认 fp 和配额
        fp = await page.evaluate("() => localStorage.getItem('fp')")
        remaining = await page.evaluate("() => localStorage.getItem('aiGenTxtRemainingCount')")
        token_raw = await page.evaluate("() => localStorage.getItem('aiGenAccessToken')")
        print(f"[*] fp: {fp}")
        print(f"[*] remaining: {remaining}")
        print(f"[*] access_token: {'exists' if token_raw else 'None'}")
        
        # 找 Clear 按钮（如果有示例文本先清除）
        clear_btn = page.locator("button:has-text('Clear')")
        if await clear_btn.count() > 0:
            await clear_btn.click()
            await page.wait_for_timeout(1000)
        
        # 找文本框
        textarea = page.locator("textarea.el-textarea__inner")
        if await textarea.count() == 0:
            print("[!] No textarea found")
            html = await page.content()
            print(f"Page: {html[:500]}")
            await browser.close()
            return {"status": "no_textarea"}
        
        # 输入文本
        await textarea.fill(text)
        await page.wait_for_timeout(500)
        
        # 点击 Detect
        btn = page.locator("button:has-text('Detect')")
        btn_exists = await btn.count()
        print(f"[*] Detect button exists: {btn_exists > 0}")
        
        if btn_exists == 0:
            await browser.close()
            return {"status": "no_detect_button"}
        
        await btn.click()
        print("[*] Detect clicked, waiting 20s for result...")
        
        # 等待结果
        for i in range(40):
            await asyncio.sleep(0.5)
            
            # 检查结果 DOM
            seg_box = page.locator(".txt-segment-box")
            try:
                seg_text = await seg_box.first.text_content(timeout=500)
                if seg_text and len(seg_text.strip()) > 10:
                    print(f"[+] Result appeared at {i*0.5}s")
                    print(f"    Text: {seg_text[:200]}")
                    break
            except:
                pass
            
            # 检查 quota 错误
            try:
                err_el = page.locator("text=today's quota").first
                if await err_el.count() > 0:
                    err_text = await err_el.text_content()
                    print(f"[!] Quota: {err_text}")
                    break
            except:
                pass
        
        # 截图
        await page.screenshot(path="/tmp/zhuque_result.png")
        
        # 提取所有可见的检测结果
        result_text = await page.evaluate("""() => {
            const el = document.querySelector('.txt-segment-box');
            if (!el) return null;
            return {
                text: el.textContent,
                html: el.innerHTML.substring(0, 1000)
            };
        }""")
        
        print(f"\n[*] Page result: {json.dumps(result_text, ensure_ascii=False)[:300] if result_text else 'None'}")
        
        # 打印 WebSocket 消息摘要
        print(f"[*] WS messages captured: {len(ws_messages)}")
        for t, msg in ws_messages[-8:]:
            try:
                data = json.loads(msg)
                print(f"  [{t}] {json.dumps(data, ensure_ascii=False)[:250]}")
            except:
                print(f"  [{t}] {msg[:150]}")
        
        await browser.close()
        
        return {
            "status": "completed",
            "fp": fp,
            "remaining": remaining,
            "page_result": result_text,
            "ws_messages": ws_messages[-10:]
        }


async def main():
    # 读终稿
    base = os.path.expanduser("/home/admin/my_document/03-内容工厂/3-终稿确认区")
    files = sorted([f for f in os.listdir(base) if "终稿" in f and f.endswith(".md")], reverse=True)
    
    # 找 GPT-5.6 的终稿
    target = [f for f in files if "GPT5" in f or "少写" in f or "Sol" in f]
    if not target:
        target = files
    filepath = os.path.join(base, target[0])
    print(f"[*] Article: {target[0]}")
    
    with open(filepath) as f:
        content = f.read()
    
    # 提取正文
    parts = content.split('---', 2)
    body = parts[2] if len(parts) >= 3 else content
    body = re.sub(r'\n---\n\n## (?:AI 检测结果|头图方案|预设评论).*', '', body, flags=re.DOTALL)
    body = re.sub(r'```.*?```', '', body, flags=re.DOTALL)
    body = re.sub(r'\|.*?\|', '', body)
    body = re.sub(r'[#*\[\]>]', '', body).strip()
    
    print(f"[*] Body: {len(body)} chars")
    
    result = await detect_via_page(body)
    print(f"\n{'='*50}")
    print(f"[*] Done")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
