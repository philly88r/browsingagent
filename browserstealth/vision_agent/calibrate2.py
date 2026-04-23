"""
Coordinate Calibration Script v2 — OpenCode Model Test
========================================================
Opens Google.com, takes a screenshot with grid overlay,
asks the OpenCode vision verifier to locate the "Google Images" link,
and prints the returned coordinates so you can verify accuracy visually.
Leaves the browser open for manual checking.

Run:  python calibrate2.py
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image, ImageDraw, ImageFont


def start_browser():
    opts = Options()
    opts.add_argument('--window-size=1280,720')
    opts.add_argument('--window-position=0,0')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=opts)
    return driver


def get_viewport_and_dpr(driver):
    vp = driver.execute_script(
        "return {w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio};"
    )
    return int(vp['w']), int(vp['h']), float(vp['dpr'])


def draw_grid(screenshot_path, click_markers=None):
    """Draw JS-style coordinate grid on screenshot (matches agent's _inject_js_grid exactly)"""
    img = Image.open(screenshot_path).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    try:
        font_major = ImageFont.truetype("arial.ttf", 22)
        font_minor = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font_major = ImageFont.load_default()
        font_minor = font_major

    w, h = img.size

    # Vertical: major red lines every 100px with white labels at top
    for x in range(100, w, 100):
        color = (255, 0, 0, 200)
        for y_dot in range(0, h, 10):
            draw.line([(x, y_dot), (x, y_dot + 5)], fill=color, width=2)
        draw.rectangle([x - 22, 2, x + 22, 26], fill=(0, 0, 0, 200))
        draw.text((x - 20, 4), f"{x}", font=font_major, fill='white')

    # Vertical: minor orange dashed lines every 50px (between majors)
    for x in range(50, w, 100):
        color = (255, 165, 0, 120)
        for y_dot in range(0, h, 20):
            draw.line([(x, y_dot), (x, y_dot + 10)], fill=color, width=1)
        draw.rectangle([x - 16, 2, x + 18, 17], fill=(0, 0, 0, 140))
        draw.text((x - 14, 1), f"{x}", font=font_minor, fill='white')

    # Horizontal: major red lines every 100px with white labels on left
    for y in range(100, h, 100):
        color = (255, 0, 0, 200)
        for x_dot in range(0, w, 10):
            draw.line([(x_dot, y), (x_dot + 5, y)], fill=color, width=2)
        draw.rectangle([0, y - 13, 40, y + 13], fill=(0, 0, 0, 200))
        draw.text((2, y - 11), f"{y}", font=font_major, fill='white')

    # Horizontal: minor orange dashed lines every 50px (between majors)
    for y in range(50, h, 100):
        color = (255, 165, 0, 120)
        for x_dot in range(0, w, 20):
            draw.line([(x_dot, y), (x_dot + 10, y)], fill=color, width=1)
        draw.rectangle([0, y - 9, 26, y + 9], fill=(0, 0, 0, 140))
        draw.text((2, y - 7), f"{y}", font=font_minor, fill='white')

    # Viewport size label at bottom center (matches JS overlay)
    label = f'Viewport: {w}x{h}'
    try:
        lw, _ = font_major.getbbox(label)[2:4] if hasattr(font_major, 'getbbox') else draw.textsize(label, font=font_major)
    except Exception:
        lw = len(label) * 12
    lx = (w - lw) // 2
    draw.rectangle([lx - 10, h - 30, lx + lw + 10, h - 5], fill=(0, 0, 0, 180))
    draw.text((lx, h - 26), label, font=font_major, fill='red')

    if click_markers:
        for i, (sx, sy, label) in enumerate(click_markers):
            is_last = (i == len(click_markers) - 1)
            color = (0, 255, 0, 255) if is_last else (128, 0, 128, 200)
            r = 12 if is_last else 8
            draw.ellipse([sx - r, sy - r, sx + r, sy + r], outline=color, width=3 if is_last else 2)
            draw.line([sx - r - 8, sy, sx + r + 8, sy], fill=color, width=3 if is_last else 2)
            draw.line([sx, sy - r - 8, sx, sy + r + 8], fill=color, width=3 if is_last else 2)
            draw.rectangle([sx + 10, sy - 20, sx + 250, sy], fill=(0, 0, 0, 200))
            draw.text((sx + 12, sy - 18), label, font=font_major, fill='lime')

    img = img.convert("RGB")
    img.save(screenshot_path)


def map_screenshot_to_viewport(sx, sy, screenshot_size, viewport_size):
    sw, sh = screenshot_size
    vw, vh = viewport_size
    if sw <= 0 or sh <= 0:
        return sx, sy
    vx = int(round((sx / sw) * vw))
    vy = int(round((sy / sh) * vh))
    vx = min(max(vx, 0), max(vw - 1, 0))
    vy = min(max(vy, 0), max(vh - 1, 0))
    return vx, vy


def main():
    print("=" * 70)
    print("COORDINATE CALIBRATION — OpenCode Model Accuracy Test")
    print("=" * 70)

    driver = start_browser()
    driver.get("https://www.google.com")
    time.sleep(3)

    vw, vh, dpr = get_viewport_and_dpr(driver)
    print(f"\n📐 Viewport: {vw}x{vh} CSS px | DPR: {dpr:.2f}")
    print(f"📐 Expected screenshot: {int(vw * dpr)}x{int(vh * dpr)} physical px")

    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)

    # Take screenshot (raw physical pixels) and resize to CSS viewport size
    # — this matches the agent's take_screenshot pipeline exactly
    raw_path = os.path.join(screenshot_dir, "calib_google.png")
    driver.save_screenshot(raw_path)

    with Image.open(raw_path) as img:
        native_size = img.size
    print(f"📐 Raw screenshot: {native_size[0]}x{native_size[1]} physical px")

    # Resize to CSS viewport size so grid labels are in CSS pixels
    if native_size != (vw, vh):
        from PIL import Image as _Image
        with _Image.open(raw_path) as img:
            img = img.resize(
                (vw, vh),
                _Image.LANCZOS if hasattr(_Image, 'LANCZOS') else _Image.Resampling.LANCZOS
            )
            img.save(raw_path)
        print(f"📐 Resized screenshot to: {vw}x{vh} CSS px")
    else:
        print(f"📐 Screenshot already at CSS viewport size")

    # Draw grid on the CSS-sized image
    draw_grid(raw_path)
    print(f"📸 Grid screenshot saved: {raw_path}")

    # Use VisionAnalyzer (OpenCode) to find the Google Images link coordinates
    print("\n🤖 Asking OpenCode vision model for 'Google Images' link coordinates...")
    from vision_analyzer import VisionAnalyzer
    vision = VisionAnalyzer(model="mimo-v2-omni")
    coords = vision.find_coordinates(raw_path, "Google Images link in the top right corner of the Google homepage")
    print(f"\n📍 MODEL SAYS: Google Images link at ({coords[0]}, {coords[1]})")

    # Pure screenshot-based test — no DOM, no CSS. Model must read coordinates from grid only.
    print("\n� Screenshot-based coordinate test complete.")
    print(f"   Model answered: ({coords[0]}, {coords[1]})")
    print(f"   Open {raw_path} to verify visually against the grid overlay.")

    # Leave browser open
    print("\n✅ Browser left open. Inspect the screenshot and coordinates above.")
    print("   Type 'quit' or Ctrl-C to close.")
    try:
        while True:
            cmd = input("\n> ").strip()
            if cmd.lower() in ('quit', 'exit', 'q'):
                break
    except (EOFError, KeyboardInterrupt):
        pass

    driver.quit()
    print("\n✅ Calibration complete.")


if __name__ == "__main__":
    main()
