import random
import time
import math
import numpy as np
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class HumanLikeMovement:
    """Simulates human-like mouse movements and interactions"""
    
    def __init__(self, driver):
        self.driver = driver
        self.action = ActionChains(driver)
    
    def bezier_curve(self, start, end, control_points=2):
        """Generate points along a Bezier curve for natural mouse movement"""
        points = []
        
        # Generate random control points between start and end
        controls = []
        for _ in range(control_points):
            x = random.randint(min(start[0], end[0]), max(start[0], end[0]))
            y = random.randint(min(start[1], end[1]), max(start[1], end[1]))
            controls.append((x, y))
        
        # Create the full point list: start -> controls -> end
        all_points = [start] + controls + [end]
        
        # Generate curve points
        steps = random.randint(15, 30)  # Variable number of steps
        for i in range(steps + 1):
            t = i / steps
            point = self._bezier_point(t, all_points)
            points.append(point)
        
        return points
    
    def _bezier_point(self, t, points):
        """Calculate a point on the Bezier curve"""
        n = len(points) - 1
        x = sum(self._bernstein(n, i, t) * points[i][0] for i in range(n + 1))
        y = sum(self._bernstein(n, i, t) * points[i][1] for i in range(n + 1))
        return (int(x), int(y))
    
    def _bernstein(self, n, i, t):
        """Bernstein polynomial"""
        return math.comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
    
    def move_to(self, x, y, duration=None):
        """Move mouse to coordinates"""
        pass  # No artificial delay — API calls are already slow enough

    def click_at(self, x, y, button='left', double=False):
        """Click at absolute viewport coordinates."""
        x = int(x)
        y = int(y)

        def describe_target(vx, vy):
            try:
                return self.driver.execute_script(
                    """
                    var el = document.elementFromPoint(arguments[0], arguments[1]);
                    if (!el) return null;
                    var t = el.closest('a,button,input,select,textarea,[role="button"],[role="link"],[tabindex],[onclick]') || el;
                    return {
                        tag: (t.tagName || '').toLowerCase(),
                        id: t.id || '',
                        text: (t.innerText || t.value || t.getAttribute('aria-label') || '').trim().slice(0, 80)
                    };
                    """,
                    vx,
                    vy,
                )
            except Exception:
                return None

        def js_coordinate_click(vx, vy):
            return self.driver.execute_script(
                """
                var x = arguments[0], y = arguments[1], dbl = arguments[2];
                var el = document.elementFromPoint(x, y);
                if (!el) return {clicked: false, reason: 'no_element'};
                var t = el.closest('a,button,input,select,textarea,label,[role="button"],[role="link"],[tabindex],[onclick]') || el;
                try { t.focus({preventScroll:true}); } catch (e) { try { t.focus(); } catch (e2) {} }
                var pointerTypes = ['pointerover','pointerenter','mouseover','mouseenter','pointermove','mousemove','pointerdown','mousedown','pointerup','mouseup'];
                pointerTypes.forEach(function(type) {
                    var isPointer = type.indexOf('pointer') === 0;
                    var evt = isPointer
                        ? new PointerEvent(type, {bubbles:true, cancelable:true, composed:true, pointerId:1, isPrimary:true, pointerType:'mouse', button:0, buttons:1, clientX:x, clientY:y, view:window})
                        : new MouseEvent(type, {bubbles:true, cancelable:true, composed:true, button:0, buttons:1, clientX:x, clientY:y, view:window});
                    t.dispatchEvent(evt);
                });
                t.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, composed:true, button:0, buttons:0, clientX:x, clientY:y, view:window}));
                if (dbl) {
                    t.dispatchEvent(new MouseEvent('dblclick', {bubbles:true, cancelable:true, composed:true, button:0, buttons:0, clientX:x, clientY:y, view:window}));
                }
                return {
                    clicked: true,
                    tag: (t.tagName || '').toLowerCase(),
                    id: t.id || '',
                    text: (t.innerText || t.value || t.getAttribute('aria-label') || '').trim().slice(0, 80)
                };
                """,
                vx,
                vy,
                bool(double),
            )

        target_before = describe_target(x, y)
        if target_before:
            desc = target_before.get('text') or target_before.get('id') or target_before.get('tag') or 'unknown'
            print(f"   🎯 Coordinate target at ({x}, {y}): {desc}")
        else:
            print(f"   ⚠️  No DOM target found at ({x}, {y}) before click")

        actionchains_ok = False

        try:
            actions = ActionChains(self.driver)
            actions.w3c_actions.pointer_action.move_to_location(x, y)
            actions.w3c_actions.pointer_action.double_click() if double else actions.w3c_actions.pointer_action.click()
            actions.perform()
            actionchains_ok = True
        except Exception as e:
            print(f"   ⚠️  ActionChains CSS click failed ({e})")

        if not actionchains_ok:
            # Try physical-pixel scaling for HiDPI / Windows OS scaling
            # devicePixelRatio may be 1.0 even with 125%/150% OS scaling, so try a few guesses
            dpr = 1.0
            try:
                dpr = float(self.driver.execute_script("return window.devicePixelRatio || 1") or 1.0)
            except Exception:
                pass

            candidates = []
            if dpr > 1.0:
                candidates.append(dpr)
            # Common OS scaling factors even when DPR reports 1.0 (Windows 125%, 150%)
            for guess in [1.25, 1.5, 2.0]:
                if guess not in candidates:
                    candidates.append(guess)

            for scale in candidates:
                try:
                    px = int(round(x * scale))
                    py = int(round(y * scale))
                    actions = ActionChains(self.driver)
                    actions.w3c_actions.pointer_action.move_to_location(px, py)
                    actions.w3c_actions.pointer_action.double_click() if double else actions.w3c_actions.pointer_action.click()
                    actions.perform()
                    actionchains_ok = True
                    print(f"   🔁 ActionChains physical-pixel fallback (scale={scale}) at ({px}, {py})")
                    break
                except Exception as e:
                    print(f"   ⚠️  ActionChains scale={scale} failed ({e})")

        # Only run JS coordinate click as a fallback when ActionChains failed.
        # Running both causes double-click events on the same element.
        if not actionchains_ok:
            try:
                js_result = js_coordinate_click(x, y)
                if js_result and js_result.get('clicked'):
                    desc = js_result.get('text') or js_result.get('id') or js_result.get('tag') or 'unknown'
                    print(f"   ✅ JS coordinate click dispatched at ({x}, {y}) on {desc}")
                else:
                    print(f"   ⚠️  JS coordinate click found no element at ({x}, {y})")
            except Exception as e2:
                print(f"   ⚠️  JS click also failed: {e2}")
        else:
            print(f"   ✅ ActionChains click succeeded — skipping redundant JS click")
    
    def type_text(self, text, element=None, wpm=None):
        """Type text instantly using send_keys."""
        try:
            if element:
                element.send_keys(text)
            else:
                active = self.driver.switch_to.active_element
                active.send_keys(text)
        except Exception:
            ActionChains(self.driver).send_keys(text).perform()
    
    def press_key(self, key_name):
        """Press a special key like Enter, Tab, etc."""
        key_map = {
            'ENTER': Keys.ENTER,
            'RETURN': Keys.RETURN,
            'TAB': Keys.TAB,
            'ESCAPE': Keys.ESCAPE,
            'ESC': Keys.ESCAPE,
            'BACKSPACE': Keys.BACK_SPACE,
            'DELETE': Keys.DELETE,
            'SPACE': Keys.SPACE,
            'PAGEDOWN': Keys.PAGE_DOWN,
            'PAGE_DOWN': Keys.PAGE_DOWN,
            'PAGEUP': Keys.PAGE_UP,
            'PAGE_UP': Keys.PAGE_UP,
        }
        
        key = key_map.get(key_name.upper(), Keys.ENTER)
        
        # Find active element or use body
        try:
            active_element = self.driver.switch_to.active_element
            active_element.send_keys(key)
        except:
            # Fallback to body
            element = self.driver.find_element("tag name", "body")
            element.send_keys(key)
        
        time.sleep(random.uniform(0.1, 0.3))
    
    def scroll(self, direction='down', amount=None, x_hint=None, y_hint=None):
        """Scroll the page and any inner scrollable containers.

        x_hint, y_hint: optional coordinates to target a specific panel or overlay.
        If None, tries center, left-third, and right-third of viewport at center height.
        """
        if amount is None:
            amount = random.randint(100, 400)

        if direction == 'up':
            amount = -amount

        # 1. Scroll the main window only if NOT targeting a specific inner container
        if x_hint is None and y_hint is None:
            self.driver.execute_script(f"window.scrollBy(0, {amount})")

        # 2. Scroll scrollable containers at multiple positions to catch sidebars/panels/overlays
        # Robust version: tries scrollBy first, falls back to scrollTop assignment, and
        # reports the element found + whether the scroll position actually changed.
        scroll_js = """
        (function(xPos, yPos, dy) {
            var el = document.elementFromPoint(xPos, yPos);
            var path = [];
            while (el && el !== document.body && el !== document.documentElement) {
                path.push(el.tagName + (el.id ? '#'+el.id : '') + (el.className ? '.'+el.className.split(' ').slice(0,2).join('.') : ''));
                var style = window.getComputedStyle(el);
                var ov = (style.overflow || '') + (style.overflowY || '');
                if ((ov.includes('scroll') || ov.includes('auto')) && el.scrollHeight > el.clientHeight + 5) {
                    var before = el.scrollTop;
                    el.scrollBy(0, dy);
                    var after = el.scrollTop;
                    // If scrollBy didn't move (some custom scrollers ignore it), force scrollTop
                    if (Math.abs(after - before) < 2) {
                        el.scrollTop = before + dy;
                        after = el.scrollTop;
                    }
                    return {
                        found: true,
                        tag: el.tagName,
                        id: el.id || '',
                        class: (el.className || '').split(' ').slice(0,3).join(' '),
                        before: before,
                        after: after,
                        delta: after - before,
                        path: path.join(' > ')
                    };
                }
                el = el.parentElement;
            }
            return {found: false, path: path.join(' > ')};
        })(arguments[0], arguments[1], arguments[2]);
        """

        try:
            w = self.driver.execute_script("return window.innerWidth")
            h = self.driver.execute_script("return window.innerHeight")
        except Exception:
            w, h = 1000, 800

        y_pos = y_hint if y_hint is not None else h // 2

        if x_hint is not None:
            x_positions = [x_hint]
        else:
            x_positions = [w // 4, w // 2, (w * 3) // 4]

        for xp in x_positions:
            try:
                result = self.driver.execute_script(scroll_js, xp, y_pos, amount)
                if result and result.get('found'):
                    tag = result.get('tag', '?')
                    delta = result.get('delta', 0)
                    el_id = result.get('id', '')
                    print(f"   📜 Inner scroll on <{tag}> id={el_id} delta={delta}px (from {result.get('before')} to {result.get('after')})")
                elif result:
                    print(f"   ⚠️  No scrollable parent found at ({xp}, {y_pos}). Path: {result.get('path', '?')}")
            except Exception as e:
                print(f"   ⚠️  Inner scroll JS error at ({xp}, {y_pos}): {e}")

        time.sleep(random.uniform(0.2, 0.4))
    
    def random_mouse_movement(self):
        """Perform random mouse movement (like a human reading)"""
        width = self.driver.execute_script("return window.innerWidth")
        height = self.driver.execute_script("return window.innerHeight")
        
        # Random point on screen
        x = random.randint(100, width - 100)
        y = random.randint(100, height - 100)
        
        self.move_to(x, y, duration=random.uniform(0.5, 1.5))
