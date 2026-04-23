"""
Coordinate Calibration Script
==============================
Opens a test page with targets at known CSS pixel positions,
takes a screenshot with grid overlay, and compares:
  1. Known CSS position (ground truth)
  2. Screenshot physical-pixel position (what the grid shows)
  3. Mapped viewport position (what the agent clicks at)
  4. elementFromPoint result (what the browser actually hits)

Run:  python calibrate_coords.py
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageDraw, ImageFont


def start_browser():
    opts = Options()
    opts.add_argument('--window-size=1280,720')
    opts.add_argument('--window-position=0,0')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=opts)
    return driver


def load_test_page(driver):
    """Inject a test page with colored targets at known CSS positions"""
    html = """
    <html><head><style>
      body { margin:0; padding:0; background:#1a1a2e; overflow:hidden; }
      .target {
        position: absolute;
        width: 40px; height: 40px;
        border: 3px solid white;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font: bold 14px monospace; color: white;
        cursor: pointer;
      }
      .info {
        position: fixed; top: 8px; left: 50%; transform: translateX(-50%);
        color: #0f0; font: bold 16px monospace; z-index: 9999;
        background: rgba(0,0,0,0.7); padding: 6px 16px; border-radius: 6px;
      }
    </style></head><body>
    <div class="info" id="hit-info">Click a target or press C to check coords</div>
    <div class="target" style="left:100px;top:100px;background:#e74c3c"  id="t1">T1</div>
    <div class="target" style="left:400px;top:100px;background:#3498db"  id="t2">T2</div>
    <div class="target" style="left:800px;top:100px;background:#2ecc71"  id="t3">T3</div>
    <div class="target" style="left:100px;top:300px;background:#f39c12"  id="t4">T4</div>
    <div class="target" style="left:600px;top:300px;background:#9b59b6"  id="t5">T5</div>
    <div class="target" style="left:1000px;top:300px;background:#1abc9c" id="t6">T6</div>
    <div class="target" style="left:400px;top:500px;background:#e67e22"  id="t7">T7</div>
    <div class="target" style="left:900px;top:500px;background:#c0392b"  id="t8">T8</div>
    <script>
      document.addEventListener('click', function(e) {
        var el = document.elementFromPoint(e.clientX, e.clientY);
        var id = el ? el.id || el.className : 'nothing';
        document.getElementById('hit-info').textContent =
          'Click at CSS(' + e.clientX + ',' + e.clientY + ') hit: ' + id;
      });
    </script>
    </body></html>
    """
    driver.get("data:text/html;charset=utf-8," + html)
    time.sleep(1)


def get_viewport_and_dpr(driver):
    vp = driver.execute_script(
        "return {w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio};"
    )
    return int(vp['w']), int(vp['h']), float(vp['dpr'])


def take_screenshot(driver, path):
    driver.save_screenshot(path)
    return path


def draw_grid(screenshot_path, click_markers=None):
    """Draw coordinate grid on screenshot (same as agent's add_reference_markers)"""
    img = Image.open(screenshot_path).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    try:
        font_major = ImageFont.truetype("arial.ttf", 22)
        font_minor = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font_major = ImageFont.load_default()
        font_minor = font_major

    w, h = img.size

    # Vertical lines
    for x in range(50, w, 50):
        is_major = (x % 100 == 0)
        color = (255, 0, 0, 200) if is_major else (255, 165, 0, 120)
        lw = 2 if is_major else 1
        for y_dot in range(0, h, 10 if is_major else 20):
            draw.line([(x, y_dot), (x, y_dot + (5 if is_major else 10))], fill=color, width=lw)
        if is_major:
            for label_y in [2, h // 2 - 12, h - 26]:
                draw.rectangle([x - 22, label_y, x + 22, label_y + 24], fill=(0, 0, 0, 200))
                draw.text((x - 20, label_y + 2), f"{x}", font=font_major, fill='white')
        else:
            for label_y in [2, h // 2 - 9]:
                draw.rectangle([x - 16, label_y, x + 18, label_y + 17], fill=(0, 0, 0, 140))
                draw.text((x - 14, label_y + 1), f"{x}", font=font_minor, fill='white')

    # Horizontal lines
    for y in range(25, h, 25):
        is_major = (y % 50 == 0)
        color = (255, 0, 0, 200) if is_major else (255, 165, 0, 120)
        lw = 2 if is_major else 1
        for x_dot in range(0, w, 10 if is_major else 20):
            draw.line([(x_dot, y), (x_dot + (5 if is_major else 10), y)], fill=color, width=lw)
        if is_major:
            for label_x in [0, w // 2 - 16, w - 36]:
                draw.rectangle([label_x, y - 13, label_x + 36, y + 13], fill=(0, 0, 0, 200))
                draw.text((label_x + 2, y - 11), f"{y}", font=font_major, fill='white')
        else:
            for label_x in [0, w // 2 - 12]:
                draw.rectangle([label_x, y - 9, label_x + 26, y + 9], fill=(0, 0, 0, 140))
                draw.text((label_x + 2, y - 7), f"{y}", font=font_minor, fill='white')

    # Viewport info
    draw.rectangle([10, 25, 200, 45], fill=(0, 0, 0, 200))
    draw.text((12, 27), f'Physical: {w}x{h}', font=font_major, fill='red')

    # Click markers
    if click_markers:
        for i, (sx, sy, label) in enumerate(click_markers):
            is_last = (i == len(click_markers) - 1)
            color = (0, 255, 0, 255) if is_last else (128, 0, 128, 200)
            r = 12 if is_last else 8
            draw.ellipse([sx - r, sy - r, sx + r, sy + r], outline=color, width=3 if is_last else 2)
            draw.line([sx - r - 8, sy, sx + r + 8, sy], fill=color, width=3 if is_last else 2)
            draw.line([sx, sy - r - 8, sx, sy + r + 8], fill=color, width=3 if is_last else 2)
            draw.rectangle([sx + 10, sy - 20, sx + 200, sy], fill=(0, 0, 0, 200))
            draw.text((sx + 12, sy - 18), label, font=font_major, fill='lime')

    img = img.convert("RGB")
    img.save(screenshot_path)


def map_screenshot_to_viewport(sx, sy, screenshot_size, viewport_size):
    """Map screenshot physical-pixel coords to CSS viewport coords"""
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
    print("COORDINATE CALIBRATION TOOL")
    print("=" * 70)

    driver = start_browser()
    load_test_page(driver)

    vw, vh, dpr = get_viewport_and_dpr(driver)
    print(f"\n📐 Viewport: {vw}x{vh} CSS px | DPR: {dpr:.2f}")
    print(f"📐 Expected screenshot: {int(vw * dpr)}x{int(vh * dpr)} physical px")

    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots')
    os.makedirs(screenshot_dir, exist_ok=True)

    # Take screenshot and draw grid
    raw_path = os.path.join(screenshot_dir, "calib_raw.png")
    take_screenshot(driver, raw_path)

    with Image.open(raw_path) as img:
        native_size = img.size
    print(f"📐 Actual screenshot: {native_size[0]}x{native_size[1]} physical px")

    # Known target positions (CSS px) — center of each 40x40 circle
    # CSS left/top + 20 for center
    targets = {
        'T1': (120, 120),
        'T2': (420, 120),
        'T3': (820, 120),
        'T4': (120, 320),
        'T5': (620, 320),
        'T6': (1020, 320),
        'T7': (420, 520),
        'T8': (920, 520),
    }

    # Calculate expected physical-pixel positions and mapped-back viewport positions
    click_markers = []
    print(f"\n{'─'*70}")
    print(f"{'Target':<8} {'CSS True':>12} {'Phys Pixel':>12} {'Mapped VP':>12} {'Roundtrip':>12} {'Error':>8}")
    print(f"{'─'*70}")

    for tid, (css_x, css_y) in targets.items():
        # Expected physical pixel position (CSS * DPR)
        phys_x = int(round(css_x * dpr))
        phys_y = int(round(css_y * dpr))

        # Map physical back to viewport (what the agent does)
        map_vx, map_vy = map_screenshot_to_viewport(phys_x, phys_y, native_size, (vw, vh))

        # Roundtrip error
        err_x = map_vx - css_x
        err_y = map_vy - css_y

        print(f"{tid:<8} ({css_x:>4},{css_y:>4})   ({phys_x:>4},{phys_y:>4})   ({map_vx:>4},{map_vy:>4})   ({map_vx:>4},{map_vy:>4})   ({err_x:>+3},{err_y:>+3})")

        click_markers.append((phys_x, phys_y, f"{tid} phys=({phys_x},{phys_y})"))

    print(f"{'─'*70}")

    # Click verification — test BOTH CSS and physical-pixel interpretations
    # ChromeDriver on high-DPR may use physical pixels instead of CSS
    print(f"\n🎯 CLICK VERIFICATION:")
    print(f"{'─'*70}")

    from selenium.webdriver.common.action_chains import ActionChains

    # Test 1: CSS viewport coords (what we expect ActionChains to use)
    print(f"\n  Test A: ActionChains with CSS viewport coords:")
    for tid, (css_x, css_y) in targets.items():
        try:
            actions = ActionChains(driver)
            actions.w3c_actions.pointer_action.move_to_location(css_x, css_y)
            actions.w3c_actions.pointer_action.click()
            actions.perform()
        except Exception:
            pass
        hit = driver.execute_script(
            f"var el = document.elementFromPoint({css_x}, {css_y}); "
            f"return el ? (el.id || el.className || el.tagName) : 'MISS';"
        )
        status = "✓ HIT" if hit == tid else f"✗ GOT '{hit}'"
        print(f"    {tid}: ActionChains({css_x},{css_y}) → {status}")

    # Test 2: JS click with CSS coords (ground truth — no ChromeDriver involvement)
    print(f"\n  Test B: JavaScript click with CSS coords (ground truth):")
    for tid, (css_x, css_y) in targets.items():
        driver.execute_script(f"""
            var el = document.elementFromPoint({css_x}, {css_y});
            if (el) {{
                var t = el.closest('a,button,input,select,textarea,[role="button"],[onclick]') || el;
                ['mousedown','mouseup','click'].forEach(function(type) {{
                    t.dispatchEvent(new MouseEvent(type, {{bubbles:true, cancelable:true, view:window, clientX:{css_x}, clientY:{css_y}}}));
                }});
            }}
        """)
        hit = driver.execute_script(
            f"var el = document.elementFromPoint({css_x}, {css_y}); "
            f"return el ? (el.id || el.className || el.tagName) : 'MISS';"
        )
        status = "✓ HIT" if hit == tid else f"✗ GOT '{hit}'"
        print(f"    {tid}: JS click({css_x},{css_y}) → {status}")

    # Test 3: ActionChains with PHYSICAL pixel coords (to test if ChromeDriver uses physical)
    print(f"\n  Test C: ActionChains with PHYSICAL pixel coords (CSS * DPR):")
    for tid, (css_x, css_y) in targets.items():
        phys_x = int(round(css_x * dpr))
        phys_y = int(round(css_y * dpr))
        try:
            actions = ActionChains(driver)
            actions.w3c_actions.pointer_action.move_to_location(phys_x, phys_y)
            actions.w3c_actions.pointer_action.click()
            actions.perform()
        except Exception:
            pass
        # Check what element is at the CSS position (where we intended)
        hit = driver.execute_script(
            f"var el = document.elementFromPoint({css_x}, {css_y}); "
            f"return el ? (el.id || el.className || el.tagName) : 'MISS';"
        )
        # Also check where the click actually landed (physical coords / DPR = CSS)
        actual_css_x = int(phys_x / dpr)
        actual_css_y = int(phys_y / dpr)
        hit_at_phys = driver.execute_script(
            f"var el = document.elementFromPoint({actual_css_x}, {actual_css_y}); "
            f"return el ? (el.id || el.className || el.tagName) : 'MISS';"
        )
        print(f"    {tid}: ActionChains phys({phys_x},{phys_y}) → at CSS({actual_css_x},{actual_css_y}) hit: {hit_at_phys}")

    print(f"{'─'*70}")

    # Draw grid with markers on screenshot
    draw_grid(raw_path, click_markers=click_markers)
    print(f"\n📸 Grid screenshot saved: {raw_path}")
    print(f"   Open it and verify the crosshairs align with the target centers.")

    # Interactive mode — type a CSS coordinate and see the mapping
    print(f"\n{'='*70}")
    print("INTERACTIVE MODE")
    print("Enter CSS viewport coords as 'x,y' to test mapping.")
    print("Enter 'phys x,y' to test physical-to-viewport mapping.")
    print("Enter 'click x,y' to click at viewport coords and check hit.")
    print("Enter 'quit' to exit.")
    print(f"{'='*70}")

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd.lower() in ('quit', 'exit', 'q'):
            break

        if cmd.startswith('click '):
            parts = cmd.split()[1].split(',')
            vx, vy = int(parts[0]), int(parts[1])
            # Click
            try:
                actions = ActionChains(driver)
                actions.w3c_actions.pointer_action.move_to_location(vx, vy)
                actions.w3c_actions.pointer_action.click()
                actions.perform()
            except Exception:
                driver.execute_script(f"""
                var el = document.elementFromPoint({vx},{vy});
                if(el){{['mousedown','mouseup','click'].forEach(function(t){{el.dispatchEvent(new MouseEvent(t,{{bubbles:true,cancelable:true,view:window,clientX:{vx},clientY:{vy}}}));}});}}
                """)
            hit = driver.execute_script(
                f"var el = document.elementFromPoint({vx},{vy}); "
                f"return el ? (el.id || el.className || el.tagName) : 'MISS';"
            )
            print(f"  Clicked VP({vx},{vy}) → hit: {hit}")

        elif cmd.startswith('phys '):
            parts = cmd.split()[1].split(',')
            sx, sy = int(parts[0]), int(parts[1])
            vx, vy = map_screenshot_to_viewport(sx, sy, native_size, (vw, vh))
            print(f"  Physical ({sx},{sy}) → Viewport ({vx},{vy})")

        else:
            parts = cmd.split(',')
            if len(parts) == 2:
                css_x, css_y = int(parts[0]), int(parts[1])
                phys_x = int(round(css_x * dpr))
                phys_y = int(round(css_y * dpr))
                vx, vy = map_screenshot_to_viewport(phys_x, phys_y, native_size, (vw, vh))
                print(f"  CSS({css_x},{css_y}) → Physical({phys_x},{phys_y}) → Mapped VP({vx},{vy}) | Error: ({vx-css_x},{vy-css_y})")

    driver.quit()
    print("\n✅ Calibration complete.")


if __name__ == "__main__":
    main()
