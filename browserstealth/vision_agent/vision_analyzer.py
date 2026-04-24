
class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

import base64
import json
import os
import re
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import prompts

# Force override system environment variables with .env file
load_dotenv(override=True)


DEFAULT_MODEL = "gemini-3-flash-preview"


def _load_gemini_api_key():
    for env in ("GEMINI_API_KEY", "GOOGLE_AI_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(env, "").strip()
        if value:
            return value
    home = os.path.expanduser("~")
    for fname in (".gemini_api_key", ".google_ai_key"):
        path = os.path.join(home, fname)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                value = f.read().strip()
            if value:
                return value
    return ""


class VisionAnalyzer:
    """Analyzes screenshots using Gemini or the OpenCode vision endpoint."""

    def __init__(self, model=None):
        self.model = model or DEFAULT_MODEL
        self.provider = "gemini" if self.model.startswith("gemini") else "opencode"
        self.base_url = 'https://opencode.ai/zen/go/v1'

        if self.provider == "gemini":
            self.api_key = _load_gemini_api_key()
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY / GOOGLE_AI_KEY not found")
        else:
            self.api_key = os.getenv('OPENCODE_API_KEY')
            if not self.api_key:
                raise ValueError("OPENCODE_API_KEY not found in environment variables")

    def _openai_post(self, messages, max_tokens=1024, temperature=0.2, timeout=60, **kwargs):
        """Make a request to the OpenAI-compatible OpenCode endpoint."""
        if self.provider == "gemini":
            return self._gemini_post(messages, max_tokens=max_tokens, temperature=temperature, timeout=timeout, **kwargs)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if kwargs.get('response_format'):
            payload['response_format'] = kwargs.pop('response_format')
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers, json=payload, timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        msg = result['choices'][0]['message']
        content = msg.get('content')
        if not content:
            # Try alternate fields (reasoning models)
            content = msg.get('reasoning_content') or msg.get('reasoning') or ''
        if not content:
            finish = result['choices'][0].get('finish_reason', '?')
            print(f"   [API] WARNING: empty content, finish_reason={finish}, msg_keys={list(msg.keys())}")
        return content or ''

    def _gemini_post(self, messages, max_tokens=1024, temperature=0.2, timeout=60, **kwargs):
        """Make a request to the Gemini generateContent endpoint."""
        system_parts = []
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            parts = self._to_gemini_parts(raw_content)
            if role == "system":
                system_parts.extend(parts)
            else:
                contents.append({
                    "role": "model" if role == "assistant" else "user",
                    "parts": parts,
                })

        generation_config = {
            "maxOutputTokens": max(max_tokens, 512),
            "temperature": temperature,
        }
        if kwargs.get("response_format"):
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_parts:
            payload["system_instruction"] = {"parts": system_parts}

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        response = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key,
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            print(f"   [Gemini] WARNING: no candidates. Response: {json.dumps(data)[:500]}")
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            finish = candidates[0].get("finishReason", "?")
            print(f"   [Gemini] WARNING: empty content, finishReason={finish}")
        return text

    def _to_gemini_parts(self, raw_content):
        if isinstance(raw_content, str):
            return [{"text": raw_content}]

        parts = []
        for item in raw_content:
            item_type = item.get("type")
            if item_type == "text":
                parts.append({"text": item.get("text", "")})
            elif item_type == "image_url":
                url = item.get("image_url", {}).get("url", "")
                match = re.match(r"data:([^;]+);base64,(.*)", url, re.DOTALL)
                if match:
                    parts.append({
                        "inline_data": {
                            "mime_type": match.group(1),
                            "data": match.group(2),
                        }
                    })
        return parts or [{"text": ""}]

    def encode_image(self, image_path):
        """Encode image to base64"""
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def find_coordinates(self, screenshot_path, target_description):
        """
        VERIFIER AGENT: Given a screenshot with a coordinate grid and a target description,
        return the exact pixel center (x, y) of that target by reading the grid labels.
        """
        from PIL import Image as _Image
        image_base64 = self.encode_image(screenshot_path)

        # Read actual image dimensions so the prompt matches the screenshot
        try:
            with _Image.open(screenshot_path) as img:
                img_w, img_h = img.size
        except Exception:
            img_w, img_h = 1280, 720

        prompt = prompts.VERIFIER_TEMPLATE.format_map(SafeDict(
            target_description=target_description,
            img_w=img_w,
            img_h=img_h,
        )

        import time as _t
        last_err = None
        refined_target = target_description
        for attempt in range(3):
            try:
                print(f"   [Verifier] Locating: {refined_target}" + (f" (retry {attempt})" if attempt else ""))
                attempt_prompt = prompts.VERIFIER_TEMPLATE.format_map(SafeDict(
                    target_description=refined_target,
                    img_w=img_w,
                    img_h=img_h,
                )
                messages = [
                    {"role": "system", "content": prompts.SYSTEM_JSON_COORDS},
                    {"role": "user", "content": [
                        {"type": "text", "text": attempt_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                    ]}
                ]
                call_kwargs = {}
                # Gemini 3 can sometimes stream back malformed partial JSON for tiny
                # coordinate objects in JSON mode. Plain text with the same strict
                # prompt parses more reliably through the fallback layers below.
                if self.provider != "gemini":
                    call_kwargs["response_format"] = {"type": "json_object"}
                text = self._openai_post(
                    messages,
                    max_tokens=512,
                    temperature=0.1,
                    timeout=120,
                    **call_kwargs,
                ).strip()

                # Layer 1: find last balanced JSON object in text (models often wrap prose around JSON)
                candidates = []
                pos = 0
                while True:
                    start = text.find('{', pos)
                    if start < 0:
                        break
                    depth, in_string, escape = 0, False, False
                    for idx in range(start, len(text)):
                        ch = text[idx]
                        if in_string:
                            escape = (ch == '\\' and not escape)
                            if not escape and ch == '"':
                                in_string = False
                            continue
                        if ch == '"':
                            in_string = True
                        elif ch == '{':
                            depth += 1
                        elif ch == '}':
                            depth -= 1
                            if depth == 0:
                                candidates.append(text[start:idx + 1].strip())
                                pos = idx + 1
                                break
                    else:
                        break
                for c in reversed(candidates):
                    if '"x"' in c and '"y"' in c:
                        try:
                            coords = json.loads(c)
                            if 'nx' in coords and 'ny' in coords:
                                x = int(float(coords['nx']) * img_w / 1000)
                                y = int(float(coords['ny']) * img_h / 1000)
                                print(f"   [Verifier] -> Normalized ({coords['nx']}, {coords['ny']}) scaled to ({x}, {y})")
                                return x, y
                            x, y = int(coords.get('x', 0)), int(coords.get('y', 0))
                            if 0 < x < 1 and 0 < y < 1:
                                x, y = int(x * img_w), int(y * img_h)
                                print(f"   [Verifier] -> Float normalized detected, scaled to ({x}, {y})")
                                return x, y
                            print(f"   [Verifier] -> ({x}, {y})")
                            return x, y
                        except (json.JSONDecodeError, ValueError):
                            pass

                # Layer 2: simple regex for inline JSON fragments
                m = re.search(r'\{[^}]*"[xy]"\s*:[^}]+\}', text)
                if m:
                    try:
                        coords = json.loads(m.group(0))
                        if 'nx' in coords and 'ny' in coords:
                            x = int(float(coords['nx']) * img_w / 1000)
                            y = int(float(coords['ny']) * img_h / 1000)
                            print(f"   [Verifier] -> Normalized ({coords['nx']}, {coords['ny']}) scaled to ({x}, {y})")
                            return x, y
                        x, y = int(coords.get('x', 0)), int(coords.get('y', 0))
                        if 0 < x < 1 and 0 < y < 1:
                            x, y = int(x * img_w), int(y * img_h)
                            print(f"   [Verifier] -> Float normalized detected, scaled to ({x}, {y})")
                            return x, y
                        print(f"   [Verifier] -> ({x}, {y})")
                        return x, y
                    except (json.JSONDecodeError, ValueError):
                        pass

                # Layer 3: extract x and y key-value pairs anywhere in text
                # "? makes the opening quote optional — handles malformed `y": 40` responses
                xm = re.search(r'"?x"?\s*:\s*(\d+)', text)
                ym = re.search(r'"?y"?\s*:\s*(\d+)', text)
                if xm and ym:
                    x, y = int(xm.group(1)), int(ym.group(1))
                    print(f"   [Verifier] -> ({x}, {y}) [fallback extract]")
                    return x, y

                # Layer 4: prose coordinate extraction (e.g. "at approximately x=1100, y=30" or "around 1100, 30")
                prose = re.search(r'(?:at|around|near|about|approximately)\s*[x=\s]*(\d+)[,\s]+[y=\s]*(\d+)', text, re.I)
                if not prose:
                    prose = re.search(r'\b(\d{3,4})\s*[,\s]+\s*(\d{2,4})\b', text)
                if prose:
                    x, y = int(prose.group(1)), int(prose.group(2))
                    print(f"   [Verifier] -> ({x}, {y}) [prose fallback]")
                    return x, y

                print(f"   [Verifier] No JSON in: {text[:120]}")
                if "dropdown" in target_description.lower() or "choose" in target_description.lower():
                    refined_target = (
                        target_description
                        + " — target the small dropdown field rectangle or down-arrow, not the descriptive paragraph/card text"
                    )
                _t.sleep(1 + attempt)
                continue

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_err = e
                print(f"   [Verifier] Network error (attempt {attempt+1}/3): {e}")
                _t.sleep(1 + attempt)
                continue
            except Exception as e:
                print(f"   [Verifier] Error: {e}")
                return None, None

        print(f"   [Verifier] Giving up after 3 attempts: {last_err}")
        return None, None

    def coordinate_task(self, screenshot_path, task_instruction, milestones=None, active_plan=None, action_history=None, semantic_map=None):
        """
        COORDINATOR AGENT: High-level manager that decides the current objective.
        """
        image_base64 = self.encode_image(screenshot_path)
        milestones_str = "\n".join(milestones) if milestones else "none yet"
        plan_str = active_plan or "No active page plan yet."
        
        # Format action history for the prompt
        hist_str = ""
        if action_history:
            # Only take the last 5 relevant actions to avoid context bloat
            relevant = [a for a in action_history if a.get('action') in ('click', 'type', 'scroll', 'click_effect', 'click_failed', 'click_mismatch')]
            for a in relevant[-5:]:
                reason = a.get('reasoning', '')
                hist_str += f"- {a['action']}: {reason}\n"
        hist_str = hist_str or "No actions taken in this session yet."

        prompt = prompts.COORDINATOR_TEMPLATE.format_map(SafeDict(
            task_instruction=task_instruction,
            milestones=milestones_str,
            active_plan=plan_str,
            action_history=hist_str,
            semantic_map=semantic_map or "No semantic map available."
        )

        try:
            print(f"   [Coordinator] Analyzing task state...")
            messages = [
                {"role": "system", "content": prompts.SYSTEM_JSON_STRICT},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]}
            ]
            # Use a faster model for coordination if available, but for now use the default
            text = self._openai_post(messages, max_tokens=1024, temperature=0.1, timeout=60, response_format={"type": "json_object"}).strip()
            result = self._parse_action(text)
            
            directive = result.get('directive', 'Continue with the task.')
            status = result.get('current_status', 'Analyzing...')
            print(f"   [Coordinator] Status: {status}")
            print(f"   [Coordinator] Directive: {directive}")
            return directive
        except Exception as e:
            print(f"   [Coordinator] Failed: {e}")
            return "Continue with the task."

    def analyze_screenshot(self, screenshot_path, task_instruction, context=None, milestones=None, action_history=None, semantic_map=None):
        """
        MAIN AGENT: Decide what action to take next.
        """
        # Step 1: COORDINATOR LAYER
        directive = self.coordinate_task(
            screenshot_path, 
            task_instruction, 
            milestones=milestones,
            active_plan=getattr(self, 'current_page_plan', ''),
            action_history=action_history,
            semantic_map=semantic_map
        )
        
        prompt = self._build_analysis_prompt(task_instruction, context, directive=directive, semantic_map=semantic_map)

        import time as _t
        for attempt in range(3):
            try:
                if screenshot_path:
                    print(f"   [Main] Analyzing with screenshot..." + (f" (retry {attempt})" if attempt else ""))
                    image_base64 = self.encode_image(screenshot_path)
                    messages = [
                        {"role": "system", "content": prompts.SYSTEM_JSON_STRICT},
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                        ]}
                    ]
                else:
                    print(f"   [Main] Analyzing DOM only..." + (f" (retry {attempt})" if attempt else ""))
                    messages = [
                        {"role": "system", "content": prompts.SYSTEM_JSON_STRICT},
                        {"role": "user", "content": prompt}
                    ]
                text = self._openai_post(messages, max_tokens=1024, temperature=0.2, timeout=60, response_format={"type": "json_object"}).strip()
                print(f"   [Main] Status: 200")
                print(f"   [Main] Response: {len(text)} chars")
                if not text.strip():
                    print(f"   [Main] Empty response, retrying...")
                    _t.sleep(2)
                    continue
                result = self._parse_action(text)
                if result.get('_parse_failed'):
                    print(f"   [Main] Parse failed — retrying...")
                    _t.sleep(2)
                    continue
                
                # Attach the directive to the result so the UI can log it
                result['_directive'] = directive
                return result

            except requests.exceptions.RequestException as e:
                print(f"   [Main] Status: {getattr(e.response, 'status_code', 'ERR') if hasattr(e, 'response') else 'ERR'}")
                if attempt < 2:
                    _t.sleep(2)
                    continue
                return {'action': 'error', 'message': f'Request failed: {str(e)}'}
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {'action': 'error', 'message': f'Analysis failed: {str(e)}'}

        return {'action': 'wait', 'reasoning': 'All retries exhausted, pausing', 'parameters': {'duration': 3}}

    def _build_analysis_prompt(self, task_instruction, context, directive=None, semantic_map=None):
        context_block = f"PREVIOUS ACTIONS:\n{context}\n\n" if context else ""
        directive_block = f"CURRENT DIRECTIVE FROM COORDINATOR:\n{directive}\n\n" if directive else ""
        semantic_block = f"\nSEMANTIC MAP OF PAGE ELEMENTS (Use [id] for precision):\n{semantic_map}\n\n" if semantic_map else ""
        return prompts.MAIN_AGENT_TEMPLATE.format_map(SafeDict(
            task_instruction=task_instruction,
            directive_block=directive_block,
            context_block=context_block + semantic_block,
        )

    def _parse_action(self, response_text):
        """Parse the action from the model's response. Handles prose-wrapping models."""
        def _extract_json(text):
            # 1. Try fenced code blocks
            for fence in ('```json', '```'):
                if fence in text:
                    s = text.find(fence) + len(fence)
                    e = text.find('```', s)
                    if e > s:
                        return text[s:e].strip()
            # 2. Find all balanced top-level JSON objects
            candidates = []
            pos = 0
            while True:
                start = text.find('{', pos)
                if start < 0:
                    break
                depth, in_string, escape = 0, False, False
                for idx in range(start, len(text)):
                    ch = text[idx]
                    if in_string:
                        escape = (ch == '\\' and not escape)
                        if not escape and ch == '"':
                            in_string = False
                        continue
                    if ch == '"':
                        in_string = True
                    elif ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            candidates.append(text[start:idx + 1].strip())
                            pos = idx + 1
                            break
                else:
                    break
            # 3. Prefer candidate with "action" key, otherwise last candidate (often at end of prose)
            for c in reversed(candidates):
                if '"action"' in c:
                    return c
            return candidates[-1] if candidates else text.strip()

        try:
            json_text = _extract_json(response_text)
            action = json.loads(json_text)
            if isinstance(action, dict) and 'parameters' not in action:
                action['parameters'] = {}
            if isinstance(action, dict) and not action.get('action'):
                print(f"   [Parse] JSON parsed but no 'action' key. Keys: {list(action.keys())}. Preview: {response_text[:300]}")
            return action
        except json.JSONDecodeError:
            print(f"   [Parse] JSON decode failed. Preview: {response_text[:300]}")
            # Salvage key fields with regex
            action_m = re.search(r'"action"\s*:\s*"([a-z_]+)"', response_text, re.I)
            reasoning_m = re.search(r'"reasoning"\s*:\s*"((?:\\.|[^"\\])*)"', response_text, re.DOTALL)
            target_m = re.search(r'"target"\s*:\s*"((?:\\.|[^"\\])*)"', response_text, re.DOTALL)
            url_m = re.search(r'"url"\s*:\s*"([^"]+)"', response_text)
            field_m = re.search(r'"field_type"\s*:\s*"(username|password)"', response_text, re.I)
            key_m = re.search(r'"key"\s*:\s*"([A-Za-z_]+)"', response_text)
            text_m = re.search(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', response_text, re.DOTALL)

            if not action_m:
                # Return wait so the loop retries rather than terminating
                return {'action': 'wait', 'reasoning': 'Corrupt API response — retrying next iteration', 'parameters': {'duration': 1}, '_parse_failed': True}

            action = action_m.group(1).lower()
            params = {}
            if action == 'click' and target_m:
                params = {'target': target_m.group(1)}
            elif action == 'navigate' and url_m:
                params = {'url': url_m.group(1)}
            elif action == 'fill_credentials' and field_m:
                params = {'field_type': field_m.group(1).lower()}
            elif action == 'press_key' and key_m:
                params = {'key': key_m.group(1)}
            elif action == 'type' and text_m:
                params = {'text': text_m.group(1)}

            return {
                'action': action,
                'reasoning': reasoning_m.group(1) if reasoning_m else 'Recovered from partial response',
                'parameters': params
            }

    def plan_page(self, screenshot_paths, task_instruction, site_memory="", completed_work=None):
        """
        PAGE PLANNER AGENT: Given screenshots of the full page (top to bottom),
        understand every field/section and return a numbered action plan the main
        agent must follow in order.
        """
        parts = []
        if site_memory:
            parts.append({"text": f"MEMORY FROM PREVIOUS RUNS ON THIS SITE:\n{site_memory}\n\n"})

        completed_section = ""
        if completed_work:
            items_str = "\n".join(f"  ✅ {m}" for m in completed_work)
            completed_section = prompts.PLANNER_COMPLETED_SECTION.format_map(SafeDict(items=items_str))

        parts.append({"text": prompts.PLANNER_TEMPLATE.format_map(SafeDict(
        parts.append({"text": prompts.PLANNER_TEMPLATE.format_map(SafeDict(\n            completed_section=completed_section
        )})
        ))})\n        # Add all page screenshots
        for i, path in enumerate(screenshot_paths):
            try:
                img_b64 = self.encode_image(path)
                parts.append({"text": f"\n[Screenshot {i+1} of {len(screenshot_paths)}]"})
                parts.append({"inline_data": {"mime_type": "image/png", "data": img_b64}})
            except Exception as e:
                print(f"   [Planner] Could not load screenshot {path}: {e}")

        # Build OpenAI-compatible message content
        content = []
        for p in parts:
            if 'text' in p:
                content.append({"type": "text", "text": p['text']})
            elif 'inline_data' in p:
                content.append({"type": "image_url", "image_url": {
                    "url": f"data:{p['inline_data']['mime_type']};base64,{p['inline_data']['data']}"
                }})

        try:
            print(f"   [Planner] Analyzing {len(screenshot_paths)} screenshot(s)...")
            plan = self._openai_post(
                [{"role": "user", "content": content}],
                max_tokens=4096, temperature=0.1, timeout=180
            ).strip()
            if plan:
                print("   [Planner] Here is my task:")
                for line in task_instruction.strip().split('\n'):
                    print(f"   {line}")
                print("   [Planner] Here is my plan:")
                for line in plan.split('\n'):
                    print(f"   {line}")
            return plan
        except Exception as e:
            print(f"   [Planner] Error: {e}")
            return ""

    def research_approach(self, stuck_description, site_url):
        """
        RESEARCH AGENT: When the main agent is stuck, search for
        grounding to find the best approach for the problem.
        Returns a short advice string to inject as context.
        """
        domain = site_url.split('/')[2] if '//' in site_url else site_url
        query = (
            f"I am using Selenium/Python browser automation and I am stuck trying to: "
            f'"{stuck_description}" on {domain}. '
            f"The element is not responding to ActionChains clicks or JavaScript dispatchEvent clicks. "
            f"What is the most reliable way to interact with this element using Selenium? "
            f"Give me a specific, actionable answer — focus on JavaScript execution tricks, "
            f"finding the element by label text, scrollIntoView, or any workaround specific to this site."
        )

        try:
            print(f"   [Research] Searching for approach: {stuck_description[:60]}...")
            advice = self._openai_post(
                [{"role": "user", "content": query}],
                max_tokens=512, temperature=0.1, timeout=120
            ).strip()
            if advice:
                print(f"   [Research] Got advice ({len(advice)} chars)")
                return advice[:600]
            return None
        except Exception as e:
            print(f"   [Research] Search failed: {e}")
            return None

    def quick_check(self, screenshot_path, question):
        """Ask a quick yes/no or short question about the screenshot"""
        image_base64 = self.encode_image(screenshot_path)
        messages = [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
        ]}]
        try:
            return self._openai_post(messages, max_tokens=256, temperature=0.1, timeout=120)
        except Exception as e:
            return f"Error: {str(e)}"

    def rescue_attempt(self, screenshot_path, stuck_target, page_url, task_hint=''):
        """
        Fresh-eyes agent called when the main agent is stuck on a specific target.
        No history, no accumulated failures — just a screenshot and one job.
        Returns a dict: {action, coordinates, key, reasoning} or None on failure.
        """
        image_base64 = self.encode_image(screenshot_path)
        context_line = f"CONTEXT: {task_hint}\n" if task_hint else ""
        prompt = prompts.RESCUE_TEMPLATE.format_map(SafeDict(
            page_url=page_url,
            stuck_target=stuck_target,
            context_line=context_line
        )
        try:
            print(f"   🆘 [Rescue] Fresh agent analyzing — stuck on: {stuck_target[:60]}")
            messages = [
                {"role": "system", "content": prompts.SYSTEM_RESCUE},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]}
            ]
            text = self._openai_post(messages, max_tokens=256, temperature=0.1, timeout=120,
                                     response_format={"type": "json_object"}).strip()
            data = json.loads(text)
            print(f"   🆘 [Rescue] Decision: {data.get('action')} — {data.get('reasoning','')[:80]}")
            return data
        except Exception as e:
            print(f"   🆘 [Rescue] Failed: {e}")
            return None
