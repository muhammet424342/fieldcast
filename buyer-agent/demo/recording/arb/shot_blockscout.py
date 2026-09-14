"""Screenshot Arbitrum Sepolia Blockscout (Arbiscan is Cloudflare-walled)."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
TX = {
    "release": "0x940965bf323e56f938d96663d24043ca5988548feb3841234e10a6a954a0d86d",
    "payment": "0x2c98152a0ee5e826de3ec383171fb91ebd09d957685358be3b0bf80bfbaaf3ad",
}
BASE = "https://arbitrum-sepolia.blockscout.com/tx/{}"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        for name, h in TX.items():
            url = BASE.format(h)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3500)
            # cookie/consent
            for sel in ["button:has-text('Got it')", "button:has-text('Accept')", "[aria-label='Close']"]:
                loc = page.locator(sel)
                if await loc.count():
                    try:
                        await loc.first.click(timeout=1500)
                    except Exception:
                        pass
            await page.wait_for_timeout(800)
            title = await page.title()
            body = await page.inner_text("body")
            ok = ("Success" in body) or ("success" in body.lower()) or (h[:10] in body)
            out = HERE / f"tx_{name}_blockscout.png"
            await page.screenshot(path=str(out), full_page=False)
            print(name, title[:80], "ok" if ok else "CHECK", out.stat().st_size)
        await browser.close()


asyncio.run(main())
