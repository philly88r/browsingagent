"""
Structured task orchestration for long browser-agent jobs.

The supervisor owns the task graph. The browser worker receives only the
currently active assignment plus a compact ledger, which keeps each worker
bounded instead of carrying the whole run in its prompt history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class TaskNode:
    id: str
    title: str
    instructions: str
    status: str = "pending"
    attempts: int = 0
    evidence: list[str] = field(default_factory=list)

    def compact(self) -> str:
        label = self.title.strip() or self.id
        return f"{self.id}: {label} [{self.status}]"


class TaskGraph:
    """Small sequential task graph for browser work."""

    def __init__(self, nodes: list[TaskNode] | None = None):
        self.nodes = nodes or []
        self.created_at = datetime.now().isoformat()

    @classmethod
    def from_instruction(cls, instruction: str) -> "TaskGraph":
        text = (instruction or "").strip()
        nodes = cls._extract_module_nodes(text)
        if not nodes:
            nodes = cls._extract_line_nodes(text)
        if not nodes and text:
            nodes = [TaskNode("task-1", "Complete requested browser task", text)]
        return cls(nodes)

    @staticmethod
    def _extract_module_nodes(text: str) -> list[TaskNode]:
        matches = list(re.finditer(r"(?im)^Module\s+(\d+)\s*:\s*(.+)$", text))
        if not matches:
            return []

        asin_match = re.search(r"(?is)ASIN to apply:\s*(.+)$", text)
        task_end = asin_match.start() if asin_match else len(text)
        nodes: list[TaskNode] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else task_end
            module_text = text[start:end].strip()
            module_num = match.group(1)
            title = f"Module {module_num}: {match.group(2).strip()}"
            nodes.append(TaskNode(f"module-{module_num}", title, module_text))

        # Preserve high-level setup instructions with the first real worker so
        # the agent can log in/open the builder and immediately continue Module 1.
        preamble = text[:matches[0].start()].strip()
        if preamble and nodes:
            nodes[0].instructions = preamble + "\n\n" + nodes[0].instructions

        if asin_match:
            nodes.append(TaskNode("apply-asin", "Apply completed A+ content to ASIN", asin_match.group(0).strip()))
        return nodes

    @staticmethod
    def _extract_line_nodes(text: str) -> list[TaskNode]:
        lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
        if len(lines) <= 1:
            return []

        nodes: list[TaskNode] = []
        buffer: list[str] = []
        counter = 1
        for line in lines:
            looks_like_step = bool(re.match(r"^(\d+[\).]|step\s+\d+[:.-])\s*", line, re.I))
            if looks_like_step and buffer:
                body = "\n".join(buffer).strip()
                nodes.append(TaskNode(f"task-{counter}", buffer[0][:80], body))
                counter += 1
                buffer = []
            buffer.append(re.sub(r"^(\d+[\).]|step\s+\d+[:.-])\s*", "", line, flags=re.I))

        if buffer:
            body = "\n".join(buffer).strip()
            nodes.append(TaskNode(f"task-{counter}", buffer[0][:80], body))
        return nodes if len(nodes) > 1 else []

    def current(self) -> TaskNode | None:
        for node in self.nodes:
            if node.status in ("pending", "in_progress"):
                if node.status == "pending":
                    node.status = "in_progress"
                    node.attempts += 1
                return node
        return None

    def mark_completed_from_note(self, note: str) -> None:
        current = self.current()
        if not current:
            return
        current.status = "done"
        current.evidence.append(note)

    def mark_blocked(self, reason: str) -> None:
        current = self.current()
        if not current:
            return
        current.status = "blocked"
        current.evidence.append(reason)

    def summary(self) -> str:
        if not self.nodes:
            return "(no structured task graph)"
        return "\n".join(f"  - {node.compact()}" for node in self.nodes)

    def worker_context(self, max_chars: int = 1800) -> str:
        node = self.current()
        if not node:
            return "All structured subtasks are complete."
        instructions = node.instructions
        if len(instructions) > max_chars:
            instructions = instructions[:max_chars] + "\n...[assignment truncated]..."
        return (
            f"CURRENT WORKER ASSIGNMENT: {node.id} - {node.title}\n"
            f"STATUS: {node.status}; ATTEMPT: {node.attempts}\n"
            f"ONLY work on this assignment until it is complete or blocked. "
            f"When complete, issue NOTE with 'COMPLETED: {node.title}'.\n\n"
            f"{instructions}"
        )
