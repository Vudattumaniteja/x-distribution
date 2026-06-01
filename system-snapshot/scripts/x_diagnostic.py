import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Attempting to open X.com...")
        try:
            # Using 'domcontentloaded' instead of 'networkidle'
            await page.goto("https://x.com/OpenAI", wait_until="domcontentloaded", timeout=30000)
            print(f"Page loaded: {page.url}")
            
            # Check for login wall
            if "login" in page.url.lower():
                print("STATUS: LOGIN WALL DETECTED")
            else:
                print("STATUS: PAGE ACCESSIBLE")
                
            # Take a screenshot for visual confirmation
            await page.screenshot(path="logs/x_diagnostic.png")
            print("Screenshot saved to logs/x_diagnostic.png")
            
        except Exception as e:
            print(f"STATUS: ERROR - {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
