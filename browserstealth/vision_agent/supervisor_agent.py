"""
Supervisor Agent — Gemini-powered watchdog that monitors the browser agent every 90 seconds.

If it detects a loop it:
  1. Stops the main agent (via callback)
  2. Analyses the log AND current screenshot with full project context
  3. Writes a handoff file so the next session knows exactly what to do differently
  4. Saves a session summary so the NEXT run has pattern memory of the last 2 failures
  5. Optionally restarts the agent automatically
"""

import base64
import os
import json
import threading
import time
import re
import requests
from datetime import datetime
from collections import deque

from prompts import (
    SUPERVISOR_SYSTEM,
    SUPERVISOR_ANALYSIS_TEMPLATE,
    SUPERVISOR_HANDOFF_TEMPLATE,
)

# ── Gemini model ──────────────────────────────
GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HANDOFF_FILE = os.path.join(BASE_DIR, "supervisor_handoff.json")
SESSION_HISTORY_FILE = os.path.join(BASE_DIR, "supervisor_session_history.json")
SITE_MEMORY_DIR = os.path.join(BASE_DIR, "site_memory")


def _load_api_key():
    """Load Gemini API key from env or well-known files."""
    for env in ("GEMINI_API_KEY", "GOOGLE_AI_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(env, "").strip()
        if v:
            return v
    home = os.path.expanduser("~")
    for fname in (".gemini_api_key", ".google_ai_key"):
        path = os.path.join(home, fname)
        if os.path.isfile(path):
            with open(path) as f:
                key = f.read().strip()
            if key:
                return key
    return ""


def _load_site_memory():
    """Load all site memory JSON files into a single string."""
    parts = []
    if os.path.isdir(SITE_MEMORY_DIR):
        for fname in os.listdir(SITE_MEMORY_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(SITE_MEMORY_DIR, fname), encoding="utf-8") as f:
                        data = json.load(f)
                    lessons = data.get("lessons", [])
                    tips = [l["text"] for l in lessons if l.get("type") == "tip"]
                    if tips:
                        parts.append(f"[{fname}]\n" + "\n".join(f"• {t}" for t in tips))
                except Exception:
                    pass
    return "\n\n".join(parts) if parts else "(none)"


def _load_session_history() -> list:
    """Load the last 2 supervisor session summaries from disk."""
    if not os.path.isfile(SESSION_HISTORY_FILE):
        return []
    try:
        with open(SESSION_HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_session_entry(entry: dict):
    """Append a session summary, keeping only the last 2 on disk."""
    history = _load_session_history()
    history.append(entry)
    history = history[-2:]
    try:
        with open(SESSION_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"🛡️  [Supervisor] Could not save session history: {e}")


def _encode_image(path: str) -> str | None:
    """Base64-encode an image file. Returns None if unavailable."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def _format_session_history(history: list) -> str:
    """Format the last 2 session summaries into readable text for the prompt."""
    if not history:
        return "(no previous sessions recorded)"
    parts = []
    for i, h in enumerate(history, 1):
        parts.append(
            f"--- Previous Session {i} ({h.get('ts', 'unknown time')}) ---\n"
            f"Task: {h.get('task', '?')[:200]}\n"
            f"URL when stuck: {h.get('url', '?')}\n"
            f"Loop type: {h.get('loop_type', '?')}\n"
            f"Stuck on: {h.get('stuck_on', '?')}\n"
            f"Root cause: {h.get('root_cause', '?')}\n"
            f"Fix applied: {h.get('fix_instruction', '?')}\n"
            f"Log excerpt:\n{h.get('log_excerpt', '')[-800:]}"
        )
    return "\n\n".join(parts)


class SupervisorAgent:
    """
    Background watchdog. Starts a thread that wakes every `check_interval` seconds,
    reads the shared log buffer AND the latest screenshot, and asks Gemini whether
    the agent is stuck. Has memory of the last 2 sessions to detect recurring patterns.
    """

    def __init__(self, check_interval=90):
        self.check_interval = check_interval
        self.api_key = _load_api_key()
        self.site_memory = _load_site_memory()

        # Shared state — set by the UI before starting
        self.log_buffer: deque = deque(maxlen=500)
        self.agent_ref = None           # BrowserAgent instance
        self.stop_callback = None       # callable() → stops the agent
        self.restart_callback = None    # callable(handoff_text, url) → restarts agent
        self.current_task = ""
        self.current_url = ""

        self._thread = None
        self._running = False
        self._last_check_lines = 0
        self._consecutive_clean = 0

        # Progress tracking
        self._last_progress_time = time.time()
        self._last_milestone_count = 0
        self._last_known_url = ""
        self.STUCK_TIMEOUT = 180        # seconds with no URL/milestone progress

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        if not self.api_key:
            print("⚠️  [Supervisor] No Gemini API key found — supervisor disabled.")
            return
        self._running = True
        self._last_progress_time = time.time()
        self._last_milestone_count = 0
        self._last_known_url = self.current_url
        self._thread = threading.Thread(target=self._loop, daemon=True, name="supervisor")
        self._thread.start()
        print(f"🛡️  [Supervisor] Started — checking every {self.check_interval}s with {GEMINI_MODEL}")
        history = _load_session_history()
        if history:
            print(f"🛡️  [Supervisor] Loaded {len(history)} previous session(s) for pattern memory.")

    def stop(self):
        self._running = False

    def log(self, line: str):
        """Called by the UI's print hook to feed lines into the buffer."""
        self.log_buffer.append(line)

    # ── Internal loop ────────────────────────────────────────────────────────

    def _loop(self):
        time.sleep(self.check_interval)  # let the agent warm up first
        while self._running:
            try:
                self._check()
            except Exception as e:
                print(f"⚠️  [Supervisor] Check error: {e}")
            time.sleep(self.check_interval)

    def _check(self):
        lines = list(self.log_buffer)
        if len(lines) < 10:
            return

        new_lines = lines[max(0, self._last_check_lines - 50):]
        self._last_check_lines = len(lines)

        if not new_lines:
            return

        # ── Track real progress ───────────────────────────────────────────────
        current_milestone_count = (
            len(getattr(self.agent_ref, "completed_milestones", []))
            if self.agent_ref else 0
        )
        if current_milestone_count > self._last_milestone_count:
            self._last_milestone_count = current_milestone_count
            self._last_progress_time = time.time()
            print(f"🛡️  [Supervisor] Progress: {current_milestone_count} milestones saved.")

        if self.current_url and self.current_url != self._last_known_url:
            self._last_known_url = self.current_url
            self._last_progress_time = time.time()
            print(f"🛡️  [Supervisor] Progress: URL changed to {self.current_url[:80]}")

        time_since_progress = time.time() - self._last_progress_time

        # ── Signal-based heuristic ────────────────────────────────────────────
        recent_text = "\n".join(new_lines[-60:])
        loop_signals = [
            "SCROLL OSCILLATION",
            "Hard blocking",
            "Duplicate note suppressed",
            "scroll loop",
            "EXHAUSTED",
            "loop detected",
        ]
        signal_count = sum(recent_text.count(s) for s in loop_signals)

        if signal_count < 3 and time_since_progress < self.STUCK_TIMEOUT:
            self._consecutive_clean += 1
            return

        if signal_count < 3:
            print(f"🛡️  [Supervisor] No progress for {int(time_since_progress)}s — calling Gemini to assess.")
        self._consecutive_clean = 0

        # ── Gather agent state ────────────────────────────────────────────────
        milestones = []
        iterations = 0
        screenshot_path = None
        if self.agent_ref:
            milestones = getattr(self.agent_ref, "completed_milestones", [])
            iterations = getattr(self.agent_ref, "iterations_on_current_page", 0)
            screenshot_path = getattr(self.agent_ref, "last_screenshot", None)
            active_plan = getattr(self.agent_ref, "current_page_plan", "")

        # ── Load cross-session memory ─────────────────────────────────────────
        session_history = _load_session_history()
        history_text = _format_session_history(session_history)

        prompt = SUPERVISOR_ANALYSIS_TEMPLATE.format(
            task_summary=self.current_task[:300],
            current_url=self.current_url or "unknown",
            milestones=", ".join(milestones) if milestones else "none yet",
            active_plan=active_plan,
            iterations=iterations,
            log_lines=len(new_lines),
            recent_log="\n".join(new_lines[-150:]),
            site_memory=self.site_memory[:3000],
            time_since_progress=int(time_since_progress),
            signal_count=signal_count,
            session_history=history_text,
            screenshot_note="A screenshot of the current browser state is attached." if screenshot_path else "No screenshot available.",
        )

        result = self._call_gemini(prompt, screenshot_path=screenshot_path)
        if not result:
            return

        if not result.get("stuck"):
            print(f"🛡️  [Supervisor] Agent looks healthy.")
            return

        # ── Loop detected ─────────────────────────────────────────────────────
        loop_type = result.get("loop_type", "unknown")
        stuck_on = result.get("stuck_on", "?")
        root_cause = result.get("root_cause", "?")
        fix = result.get("fix_instruction", "")
        next_step = result.get("next_step", "")
        continue_url = result.get("continue_url", self.current_url or "")
        screen_summary = result.get("screenshot_summary", "")

        print(f"\n🛡️  [Supervisor] ⚠️  LOOP DETECTED — {loop_type}")
        print(f"🛡️  [Supervisor] Stuck on: {stuck_on}")
        print(f"🛡️  [Supervisor] Root cause: {root_cause}")
        print(f"🛡️  [Supervisor] Fix: {fix}")
        if screen_summary:
            print(f"🛡️  [Supervisor] Screen: {screen_summary}")

        # Save session summary for next run's pattern memory
        _save_session_entry({
            "ts": datetime.now().isoformat(),
            "task": self.current_task[:200],
            "url": self.current_url,
            "loop_type": loop_type,
            "stuck_on": stuck_on,
            "root_cause": root_cause,
            "fix_instruction": fix,
            "screenshot_summary": screen_summary,
            "log_excerpt": "\n".join(new_lines[-80:]),
        })

        # Build handoff context
        handoff_text = SUPERVISOR_HANDOFF_TEMPLATE.format(
            loop_type=loop_type,
            stuck_on=stuck_on,
            root_cause=root_cause,
            fix_instruction=fix,
            next_step=next_step,
            milestones="\n".join(f"  ✅ {m}" for m in milestones) if milestones else "  (none yet)",
            active_plan=active_plan,
            continue_url=continue_url,
            screen_summary=f"\nSCREEN STATE WHEN STOPPED:\n{screen_summary}" if screen_summary else "",
        )

        # Write handoff file
        handoff_data = {
            "ts": datetime.now().isoformat(),
            "loop_type": loop_type,
            "stuck_on": stuck_on,
            "root_cause": root_cause,
            "fix_instruction": fix,
            "next_step": next_step,
            "milestones": milestones,
            "continue_url": continue_url,
            "screenshot_summary": screen_summary,
            "handoff_text": handoff_text,
        }
        try:
            with open(HANDOFF_FILE, "w", encoding="utf-8") as f:
                json.dump(handoff_data, f, indent=2)
            print(f"🛡️  [Supervisor] Handoff written to {HANDOFF_FILE}")
        except Exception as e:
            print(f"🛡️  [Supervisor] Could not write handoff: {e}")

        # Stop current agent
        if self.stop_callback:
            print("🛡️  [Supervisor] Stopping agent...")
            try:
                self.stop_callback()
            except Exception as e:
                print(f"🛡️  [Supervisor] Stop failed: {e}")

        # Restart with handoff
        if self.restart_callback:
            time.sleep(3)
            print("🛡️  [Supervisor] Restarting agent with handoff context...")
            try:
                self.restart_callback(handoff_text, continue_url)
            except Exception as e:
                print(f"🛡️  [Supervisor] Restart failed: {e}")

    # ── Gemini API call (multimodal) ──────────────────────────────────────────

    def _call_gemini(self, prompt: str, screenshot_path: str = None) -> dict | None:
        # Build parts — always include text, attach screenshot if available
        parts = [{"text": prompt}]
        if screenshot_path:
            img_b64 = _encode_image(screenshot_path)
            if img_b64:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": img_b64,
                    }
                })
                print(f"🛡️  [Supervisor] Screenshot attached: {os.path.basename(screenshot_path)}")

        payload = {
            "system_instruction": {"parts": [{"text": SUPERVISOR_SYSTEM}]},
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": 4096,
                "temperature": 0.2,
            },
        }
        try:
            resp = requests.post(
                GEMINI_ENDPOINT,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                },
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            # Handle API-level errors returned in the body
            if "error" in data:
                print(f"🛡️  [Supervisor] Gemini API error: {data['error']}")
                return None

            candidates = data.get("candidates", [])
            if not candidates:
                print(f"🛡️  [Supervisor] Gemini returned no candidates. Full response: {json.dumps(data)[:500]}")
                return None

            text = candidates[0]["content"]["parts"][0]["text"].strip()

            # Strip markdown fences
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*```$", "", text)

            # Find the JSON object in the response (handles prose wrapping)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)

            return json.loads(text)

        except json.JSONDecodeError as e:
            print(f"🛡️  [Supervisor] Gemini parse error: {e}")
            print(f"🛡️  [Supervisor] Raw text was: {text[:500] if 'text' in dir() else 'unavailable'}")
            return None
        except requests.HTTPError as e:
            print(f"🛡️  [Supervisor] HTTP {e.response.status_code}: {e.response.text[:400]}")
            return None
        except Exception as e:
            print(f"🛡️  [Supervisor] Gemini call failed: {e}")
            return None


# ── Module-level singleton ────────────────────────────────────────────────────
supervisor = SupervisorAgent(check_interval=90)
