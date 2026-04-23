"""
Handler for human verification requests (2FA, SMS codes, etc.)
"""

import time


class VerificationHandler:
    """Manages human verification interactions"""
    
    def __init__(self, agent):
        self.agent = agent
        self.pending_verification = None
    
    def request_verification(self, action):
        """
        Store verification request and prepare for user input
        
        Args:
            action: The need_human action from the vision analyzer
        
        Returns:
            dict: Verification request details
        """
        params = action.get('parameters', {})
        
        self.pending_verification = {
            'request': params.get('request', 'Verification needed'),
            'field_description': params.get('field_description', 'input field'),
            'x': params.get('x'),
            'y': params.get('y'),
            'reasoning': action.get('reasoning', ''),
            'timestamp': time.time()
        }
        
        return self.pending_verification
    
    def submit_verification(self, user_input):
        """
        Submit user-provided verification code/input.
        Supports multi-box OTP (spreads digits across separate inputs)
        and optional submit-button click instead of Enter.
        
        Args:
            user_input: The code or text provided by the user
        
        Returns:
            bool: Success status
        """
        if not self.pending_verification:
            print("⚠️  No pending verification request")
            return False
        
        x = self.pending_verification.get('x')
        y = self.pending_verification.get('y')
        
        try:
            # Click on the input field if coordinates provided
            if x and y:
                vx, vy = self.agent.map_screenshot_to_viewport(int(x), int(y))
                print(f"📍 Clicking verification field at viewport ({vx}, {vy}) [from screenshot ({x}, {y})]")
                self.agent.movement.click_at(vx, vy)
                time.sleep(0.5)
            
            # Detect multi-box OTP inputs (e.g. 6 separate <input maxlength="1">)
            digits = list(str(user_input))
            multi_inputs = self.agent.driver.execute_script("""
                var inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input[type="tel"], input:not([type])'));
                var otpInputs = inputs.filter(function(inp) {
                    var style = window.getComputedStyle(inp);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                    var rect = inp.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return false;
                    var maxl = parseInt(inp.getAttribute('maxlength') || '999');
                    return maxl === 1;
                });
                // Also catch inputs in a visual OTP row even without maxlength=1
                if (otpInputs.length < 2) {
                    var visible = inputs.filter(function(i) { return i.offsetParent !== null; });
                    // Heuristic: 4-8 inputs in a horizontal row with similar size
                    if (visible.length >= 4 && visible.length <= 8) {
                        var rects = visible.map(function(i) { return i.getBoundingClientRect(); });
                        var sameRow = rects.every(function(r) { return Math.abs(r.top - rects[0].top) < 20; });
                        if (sameRow) return visible;
                    }
                }
                return otpInputs;
            """)
            
            if multi_inputs and len(multi_inputs) >= len(digits):
                print(f"⌨️  Entering {len(digits)}-digit OTP into {len(multi_inputs)} input boxes")
                for i, d in enumerate(digits):
                    try:
                        multi_inputs[i].clear()
                        multi_inputs[i].send_keys(d)
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"   ⚠️  Could not type digit {d} into box {i+1}: {e}")
            else:
                # Single-field entry
                print(f"⌨️  Entering verification: {user_input}")
                self.agent.movement.type_text(str(user_input))
                time.sleep(0.3)

            # Submit: try a submit button first, then Enter as fallback
            submit_clicked = False
            try:
                submit_btn = self.agent.driver.execute_script("""
                    var btns = Array.from(document.querySelectorAll('button, input[type="submit"], a[role="button"], [class*="submit"], [class*="verify"], [class*="confirm"]'));
                    for (var i = 0; i < btns.length; i++) {
                        var txt = (btns[i].textContent || btns[i].value || '').toLowerCase();
                        if (txt.indexOf('verify') !== -1 || txt.indexOf('submit') !== -1 || txt.indexOf('confirm') !== -1 || txt.indexOf('continue') !== -1) {
                            var r = btns[i].getBoundingClientRect();
                            if (r.width > 0 && r.height > 0) return btns[i];
                        }
                    }
                    return null;
                """)
                if submit_btn:
                    submit_btn.click()
                    print("   ✅ Clicked submit/verify button")
                    submit_clicked = True
                    time.sleep(2)
            except Exception as e:
                print(f"   ⚠️  Could not click submit button: {e}")
            
            if not submit_clicked:
                try:
                    from selenium.webdriver.common.keys import Keys
                    active = self.agent.driver.switch_to.active_element
                    active.send_keys(Keys.RETURN)
                    print("↵ Pressed Enter to submit verification")
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠️  Could not press Enter after verification: {e}")

            # Clear pending verification
            self.pending_verification = None

            print("✅ Verification submitted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error submitting verification: {str(e)}")
            return False
    
    def has_pending_verification(self):
        """Check if there's a pending verification request"""
        return self.pending_verification is not None
    
    def get_pending_request(self):
        """Get the current pending verification request"""
        return self.pending_verification
    
    def cancel_verification(self):
        """Cancel the pending verification"""
        self.pending_verification = None
