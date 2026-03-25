# answer_builder.py
from llm import call_llm


def generate_summary(raw_answer: str) -> str:
    system_prompt = """
You are a strategy consultant at a top firm (e.g., McKinsey).
Summarize the following professional FINANCE analysis into 3–5 sharp,
concise bullet points that a senior stakeholder could read in 30 seconds.

Style:
- Each bullet = one clear idea
- No fluff, no repetition
- Focus on macro / sector / credit / portfolio implications
- Output ONLY bullet points (e.g., "- ...").
"""
    return call_llm(system_prompt, raw_answer, temperature=0.1)


def generate_risk_warning(raw_answer: str) -> str:
    system_prompt = """
You are a compliance officer at a global financial institution.

Given the analysis, write 2–3 sentences of a GENERAL risk warning that:
- highlights market uncertainty and model limitations,
- states that the information is not personalized investment advice,
- reminds the reader to consider their own circumstances and regulations.
"""
    return call_llm(system_prompt, raw_answer, temperature=0.1)


def wrap_final_answer(raw_answer: str) -> str:
    summary = generate_summary(raw_answer)
    risk = generate_risk_warning(raw_answer)

    return f"""
# Final Professional Finance Answer
{raw_answer}

---

## 📌 Executive Summary
{summary}

## ⚠️ Risk Warning (General Disclaimer)
{risk}
""".strip()
