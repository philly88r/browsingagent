import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image


def main():
    options = Options()
    options.add_argument('--window-size=1280,720')
    options.add_argument('--window-position=0,0')
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = webdriver.Chrome(options=options)

    driver.get('https://www.google.com')
    time.sleep(3)

    viewport = driver.execute_script(
        "return {width: window.innerWidth, height: window.innerHeight, dpr: window.devicePixelRatio};"
    )
    vw = int(viewport['width'])
    vh = int(viewport['height'])
    dpr = float(viewport['dpr'])

    result = driver.execute_script(
        """
        const candidates = Array.from(document.querySelectorAll('a')).filter(a => {
            const text = (a.textContent || '').trim().toLowerCase();
            const aria = (a.getAttribute('aria-label') || '').trim().toLowerCase();
            return text === 'images' || aria === 'images';
        });
        if (!candidates.length) return null;
        const a = candidates[0];
        const r = a.getBoundingClientRect();
        return {
            text: (a.textContent || '').trim(),
            left: r.left,
            top: r.top,
            width: r.width,
            height: r.height,
            center_x: r.left + (r.width / 2),
            center_y: r.top + (r.height / 2)
        };
        """
    )

    if not result:
        print('Could not find the Images link on Google.')
        print('Browser will remain open. Press Enter to exit.')
        input()
        return

    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)
    screenshot_path = os.path.join(screenshot_dir, 'google_images_coords_keep_open.png')
    driver.save_screenshot(screenshot_path)

    with Image.open(screenshot_path) as img:
        sw, sh = img.size

    viewport_x = int(round(result['center_x']))
    viewport_y = int(round(result['center_y']))
    screenshot_x = int(round((viewport_x / vw) * sw))
    screenshot_y = int(round((viewport_y / vh) * sh))

    print(f"Images link text: {result['text']}")
    print(f"Viewport: {vw}x{vh} CSS px")
    print(f"DPR: {dpr}")
    print(f"Screenshot: {sw}x{sh} physical px")
    print(f"Viewport click coords: ({viewport_x}, {viewport_y})")
    print(f"Screenshot coords: ({screenshot_x}, {screenshot_y})")
    print(f"Screenshot saved: {screenshot_path}")
    print('Browser left open. Press Enter here when you are done inspecting it.')
    input()
    driver.quit()


if __name__ == '__main__':
    main()
