"""
local_llm.py
-------------
Local LLaMA3 client (no synthetic fallbacks).

- Calls a local LLaMA3 model (e.g., Ollama at http://localhost:11434/api/generate).
- If the local model is unavailable or returns empty output, we raise an error to avoid fake data.
- Always returns a narrative plus a single JSON object on the last line with all rubric fields (enforced by the caller prompt).
"""

from __future__ import annotations

import hashlib
import os
import random
import time
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv


@dataclass
class LocalLLMConfig:
    temperature: float = 0.65
    seed_salt: str = "esg-intel"
    model: str = "llama3"
    endpoint: str = "http://localhost:11434/api/generate"
    timeout: int = int(os.getenv("LLM_TIMEOUT", "120"))
    num_predict: int = int(os.getenv("LLM_NUM_PREDICT", "1024"))
    max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    debug: bool = False


class LocalLLM:
    def __init__(self, config: Optional[LocalLLMConfig] = None) -> None:
        load_dotenv()
        self.config = config or LocalLLMConfig()

    # ------------------------------------------------------------------ #
    def ask(
        self,
        prompt: str,
        bank_name: Optional[str] = None,
        question: Optional[str] = None,
        pdf_text: Optional[str] = None,
    ) -> str:
        bank = bank_name or self._infer_bank_from_prompt(prompt) or "Unknown Bank"
        rng = self._fresh_rng(bank)
        augmented_prompt = self._augment_prompt(prompt, bank, question, pdf_text, rng)

        last_err: Optional[Exception] = None
        # Retries: keep full generation budget for best quality, only back off wait between attempts
        profiles = [(self.config.timeout, self.config.num_predict) for _ in range(self.config.max_retries)]

        for attempt, (attempt_timeout, attempt_tokens) in enumerate(profiles, start=1):
            try:
                llm_output = self._call_local_llm(augmented_prompt, attempt_timeout, attempt_tokens)
                if not llm_output or not llm_output.strip():
                    raise RuntimeError("empty response")
                return llm_output
            except Exception as exc:
                last_err = exc
                time.sleep(0.4 * attempt)

        raise RuntimeError(
            f"Local LLaMA3 call failed after {self.config.max_retries} attempts: {last_err}. "
            f"Ensure the model '{self.config.model}' is running at {self.config.endpoint} "
            f"and consider lowering LLM_TIMEOUT/LLM_NUM_PREDICT if timeouts persist."
        )

    # ------------------------------------------------------------------ #
    def _call_local_llm(self, prompt: str, timeout_s: int, num_predict: int) -> str:
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": num_predict,
            },
        }
        try:
            resp = requests.post(
                self.config.endpoint,
                json=payload,
                timeout=(10, timeout_s),  # (connect, read)
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Local LLaMA3 HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            return data.get("response", "") or ""
        except Exception as exc:
            raise RuntimeError(f"Local LLaMA3 call failed: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Helpers for synthetic path
    # ------------------------------------------------------------------ #
    def _fresh_rng(self, bank: str) -> random.Random:
        salt = f"{bank}-{self.config.seed_salt}-{time.time()}-{random.random()}"
        seed_int = int(hashlib.sha256(salt.encode()).hexdigest(), 16) % (2**32)
        return random.Random(seed_int + int(self.config.temperature * 10))

    def _augment_prompt(self, prompt: str, bank: str, question: Optional[str], pdf_text: Optional[str], rng: random.Random) -> str:
        entropy = hashlib.sha256(f"{bank}-{rng.random()}-{time.time()}".encode()).hexdigest()[:12]
        evidence = (pdf_text or "").strip()
        evidence = evidence[:4000] + ("...[truncated]" if len(evidence) > 4000 else "")
        extra = (
            f"\n\n[Bank:{bank}][Focus:{question or 'general ESG'}]"
            f"[Entropy:{entropy}]"
            f"[Evidence:{('none' if not evidence else evidence)}]"
            "\nOn the very last line, output exactly one valid JSON object with all rubric fields."
        )
        return prompt + extra

    # ------------------------------------------------------------------ #
    def _infer_bank_from_prompt(self, prompt: str) -> Optional[str]:
        if not prompt:
            return None
        markers = ["Analyse the ESG performance of", "Analyse the ESG performance", "Target bank:"]
        for m in markers:
            if m.lower() in prompt.lower():
                tail = prompt.lower().split(m.lower())[-1]
                return tail.strip().split()[0:3][0].title() if tail else None
        return None
