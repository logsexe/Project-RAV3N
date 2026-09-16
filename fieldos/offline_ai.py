from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(slots=True, frozen=True)
class AIStatus:
    available: bool
    model: str
    detail: str


class OfflineAI:
    """Small local-only Ollama adapter for FIELD//OS.

    The adapter never executes model output. It only sends a prompt to the
    loopback/local endpoint selected by the operator and returns generated text.
    """

    def __init__(self) -> None:
        self.base_url = os.environ.get("FIELDOS_AI_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.environ.get("FIELDOS_AI_MODEL", "qwen2.5:1.5b")

    def status(self, timeout: float = 0.8) -> AIStatus:
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
            return AIStatus(False, self.model, f"OFFLINE // {type(exc).__name__}")
        names = [str(item.get("name", "")) for item in payload.get("models", [])]
        available = self.model in names or any(name.split(":", 1)[0] == self.model.split(":", 1)[0] for name in names)
        detail = "READY" if available else "SERVICE READY // MODEL NOT FOUND"
        return AIStatus(available, self.model, detail)

    def ask(self, prompt: str, context: str = "", timeout: float = 90.0) -> str:
        prompt = prompt.strip()
        if not prompt:
            return "Enter a question."
        system = (
            "You are FIELD//OS ASSIST, an offline assistant on the RVN-01 field computer. "
            "Be concise, distinguish uncertainty, and use supplied local knowledge when present. "
            "Never claim to have executed commands or changed hardware."
        )
        if context.strip():
            system += "\n\nLOCAL KNOWLEDGE:\n" + context[:12000]
        body = json.dumps({"model": self.model, "prompt": prompt, "system": system, "stream": False}).encode("utf-8")
        request = Request(f"{self.base_url}/api/generate", data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
            return f"ASSIST unavailable: {type(exc).__name__}. Check the local Ollama service and model."
        return str(payload.get("response", "")).strip() or "No response returned by the local model."
