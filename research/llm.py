import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3")
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:11434/v1")

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_API_BASE,
)

# ===== GLOBAL HIGH-PRECISION FINANCE GUARDRAIL =====
GLOBAL_SYSTEM_GUARDRAIL = """
You are a professional finance assistant operating in strict high-precision mode.

Hard constraints:
- NEVER fabricate specific numerical values (prices, EPS, yields, GDP %, CPI %, dates, etc.)
- You may only use concrete numbers that appear in the provided context.
- If information is missing, explicitly say it is "uncertain", "not confirmed", or "no precise data available".
- When numbers are not available, answer qualitatively and structurally instead of guessing.
- You must remain within the domains of:
    - finance, macroeconomics, banking, credit, risk management,
    - markets, portfolio theory, corporate finance, and related logic.
- It is always better to be conservative and transparent about uncertainty than overconfident and wrong.
"""


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Call local LLM with:
      - global finance guardrail
      - task-specific system prompt
    """
    final_system_prompt = GLOBAL_SYSTEM_GUARDRAIL + "\n\n" + system_prompt

    resp = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        temperature=temperature,
        messages=[
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()