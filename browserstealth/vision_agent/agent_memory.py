"""
Site-specific memory store. Saves knowledge about how pages/sites work
so the agent can recall it on future runs and avoid repeating mistakes.
Stored as JSON per domain in the site_memory/ directory.
"""

import json
import os
import re
from urllib.parse import urlparse
from datetime import datetime


class AgentMemory:

    def __init__(self):
        self.memory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_memory')
        os.makedirs(self.memory_dir, exist_ok=True)
        self.max_lessons = 50
        self.max_recall_chars = 4000

    # ─── internal helpers ───────────────────────────────────────────────────

    def _domain(self, url):
        parsed = self._parse_url(url)
        netloc = (parsed.netloc or '').replace('www.', '').strip().lower()
        return netloc or 'unknown'

    def _parse_url(self, url):
        raw_url = (url or '').strip()
        if not raw_url:
            return urlparse('http://unknown')
        if not raw_url.startswith(('http://', 'https://')):
            raw_url = 'http://' + raw_url
        return urlparse(raw_url)

    def _path(self, url):
        return os.path.join(self.memory_dir, f"{self._domain(url)}.json")

    def _load(self, url):
        p = self._path(url)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                corrupt_path = f"{p}.corrupt_{timestamp}"
                try:
                    os.replace(p, corrupt_path)
                except OSError:
                    pass
                print(f"   [Memory] Corrupt JSON for {self._domain(url)} backed up to {os.path.basename(corrupt_path)}: {e}")
            except OSError as e:
                print(f"   [Memory] Failed to read {os.path.basename(p)}: {e}")
        return {'domain': self._domain(url), 'lessons': [], 'pages': {}}

    def _save(self, url, data):
        path = self._path(url)
        temp_path = f"{path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, path)

    # ─── public API ─────────────────────────────────────────────────────────

    def recall(self, url):
        """Return a concise string of everything known about this site/page."""
        data = self._load(url)
        parts = []

        # Lessons
        lessons = data.get('lessons', [])
        if lessons:
            recent = lessons[-10:]  # last 10
            parts.append("KNOWN LESSONS FOR THIS SITE:")
            for l in recent:
                parts.append(f"  - [{l.get('type','info')}] {l['text']}")

        # Page-specific knowledge
        page_key = self._page_key(url)
        pages = data.get('pages', {})
        matched_pattern = None
        matched_info = None
        if page_key in pages:
            matched_pattern = page_key
            matched_info = pages[page_key]
        else:
            for pattern, info in pages.items():
                if pattern in page_key or page_key.startswith(pattern):
                    matched_pattern = pattern
                    matched_info = info
                    break

        if matched_pattern and matched_info:
            parts.append(f"\nKNOWN PAGE STRUCTURE for '{matched_pattern}':")
            if matched_info.get('fields'):
                parts.append("  Fields in order: " + " → ".join(matched_info['fields']))
            if matched_info.get('notes'):
                parts.append("  Notes: " + "; ".join(matched_info['notes']))

        final_text = "\n".join(parts) if parts else ""
        if len(final_text) > self.max_recall_chars:
            return final_text[:self.max_recall_chars] + "\n...[Memory Truncated]..."
        return final_text

    def save_lesson(self, url, text, lesson_type='tip'):
        """Save a lesson learned (tip, fix, warning) for this site."""
        data = self._load(url)
        for lesson in data['lessons']:
            if lesson.get('text') == text:
                lesson['ts'] = datetime.now().isoformat()
                lesson['type'] = lesson_type
                lesson['url'] = url
                data['lessons'].remove(lesson)
                data['lessons'].append(lesson)
                self._save(url, data)
                print(f"   [Memory] Refreshed {lesson_type}: {text[:80]}")
                return
        data['lessons'].append({
            'text': text,
            'type': lesson_type,
            'url': url,
            'ts': datetime.now().isoformat()
        })
        data['lessons'] = data['lessons'][-self.max_lessons:]
        self._save(url, data)
        print(f"   [Memory] Saved {lesson_type}: {text[:80]}")

    def save_page_plan(self, url, fields, notes=None):
        """Save the discovered field order and notes for a specific page."""
        data = self._load(url)
        key = self._page_key(url)
        data.setdefault('pages', {})[key] = {
            'fields': fields,
            'notes': notes or [],
            'ts': datetime.now().isoformat()
        }
        self._save(url, data)
        print(f"   [Memory] Saved page structure for {key}: {len(fields)} fields")

    def _page_key(self, url):
        """Normalize URL to a stable page key (strip query/fragment, keep path)."""
        try:
            parsed = self._parse_url(url)
            domain = (parsed.netloc or '').replace('www.', '').strip().lower() or 'unknown'
            path = parsed.path or '/'
            path = re.sub(r'\b[0-9]+\b', '{id}', path)
            path = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '{id}', path)
            path = re.sub(r'/+', '/', path).rstrip('/') or '/'
            return f"{domain}{path}"
        except Exception:
            return url[:60]
