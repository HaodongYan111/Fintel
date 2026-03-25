import streamlit as st
from typing import Dict, Any, List, Optional

import pandas as pd

from server import Server
from tools.radar_chart import create_esg_radar_chart

# ------------------------------------------------------------
# Bank list
# ------------------------------------------------------------
try:
    from tools.dutch_banks import list_dutch_banks

    BANK_LIST = [b for b in list_dutch_banks() if b in {"ING Group", "ABN AMRO", "Rabobank"}]
except Exception:
    BANK_LIST = ["ING Group", "ABN AMRO", "Rabobank"]


# ------------------------------------------------------------
# Backend server (cached)
# ------------------------------------------------------------
@st.cache_resource
def get_server() -> Server:
    return Server()


server = get_server()


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(page_title="Dutch Bank ESG Intelligence System", page_icon="📊", layout="centered")

st.sidebar.title("⚙️ Configuration")
mode = st.sidebar.radio("Mode", ["Single Bank Analysis", "Compare Banks"])
st.sidebar.markdown("---")
st.sidebar.caption("Free-data pipeline: Yahoo Finance + Google News RSS + Rubric Engine")


# ------------------------------------------------------------
# PDF Extract
# ------------------------------------------------------------
def extract_pdf_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    try:
        from PyPDF2 import PdfReader
    except Exception:
        st.error("❌ PyPDF2 not installed. Please run: `pip install PyPDF2`")
        return ""

    try:
        reader = PdfReader(uploaded_file)
        text_chunks = []
        for page in reader.pages:
            text_chunks.append(page.extract_text() or "")
        return "\n".join(text_chunks)
    except Exception as e:
        st.warning(f"⚠️ PDF parsing failed: {e}")
        return ""


# ------------------------------------------------------------
# UI helpers
# ------------------------------------------------------------
def render_score_cards(scores: Dict[str, Any]):
    pillar = scores.get("pillar_scores", {}) or {}
    e = float(pillar.get("E", scores.get("E", 0.0)) or 0.0)
    s = float(pillar.get("S", scores.get("S", 0.0)) or 0.0)
    g = float(pillar.get("G", scores.get("G", 0.0)) or 0.0)
    final = float(scores.get("final", 0.0) or 0.0)
    label = scores.get("label", "N/A")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Environmental (E)", f"{e:.1f}")
    c2.metric("Social (S)", f"{s:.1f}")
    c3.metric("Governance (G)", f"{g:.1f}")
    c4.metric("Final ESG Score", f"{final:.1f}", label)


def render_mc_table(scores: Dict[str, Any]):
    mc = scores.get("mc", {}) or {}
    st.markdown("### 🎯 Monte-Carlo Confidence Band")
    st.table(
        {
            "Metric": ["Mean", "P05 (Conservative)", "P50 (Median)", "P95 (Optimistic)"],
            "Value": [
                float(mc.get("mean", 0.0) or 0.0),
                float(mc.get("p05", 0.0) or 0.0),
                float(mc.get("p50", 0.0) or 0.0),
                float(mc.get("p95", 0.0) or 0.0),
            ],
        }
    )


def render_radar(scores: Dict[str, Any], bank: str):
    pillar = scores.get("pillar_scores", {}) or {}
    e = float(pillar.get("E", scores.get("E", 0.0)) or 0.0)
    s = float(pillar.get("S", scores.get("S", 0.0)) or 0.0)
    g = float(pillar.get("G", scores.get("G", 0.0)) or 0.0)

    try:
        fig = create_esg_radar_chart(e, s, g, bank_name=bank)
        st.pyplot(fig, clear_figure=True)
    except Exception as ex:
        st.warning(f"⚠️ Radar chart failed: {ex}")


def render_subscore_table(scores: Dict[str, Any]):
    sub_scores = scores.get("sub_scores", {}) or {}
    if not sub_scores:
        return

    rows = []
    for pillar, items in sub_scores.items():
        if not isinstance(items, dict):
            continue
        for name, val in items.items():
            rows.append({"Pillar": pillar, "Indicator": name, "Score": val})

    if rows:
        st.markdown("### 📑 Rubric Sub-Scores")
        df = pd.DataFrame(rows)
        # ---------- Rubric Sub-Scores ----------
        df = pd.DataFrame(rows).sort_values(["Pillar", "Indicator"], ignore_index=True)

        styled = (
            df.style
            .set_properties(**{
                "font-size": "15px",
                "text-align": "left",
                "line-height": "1.6",
                "padding": "6px 10px"
            })
        )

        # 高度足够显示全部内容
        table_height = 140 + 30 * len(df)

        st.dataframe(
            styled,
            use_container_width=False,
            width=850,          # 稍宽一些以容纳长指标名
            height=table_height,
            hide_index=True
        )



def render_sources_block(result: Dict[str, Any]):
    """
    Show Yahoo snapshot + News sources in a clean way.
    Compatible with server.py response.
    """
    yahoo = result.get("yahoo", {}) or {}
    news = result.get("news", {}) or {}
    items = news.get("items", []) or []
    query = news.get("query", "")

    with st.expander("🔎 Data Sources (Yahoo + Google News RSS)", expanded=False):
        c1, c2 = st.columns([1, 1])

        with c1:
            st.markdown("**Yahoo Finance Snapshot (free)**")
            if yahoo.get("ok"):
                st.write(yahoo.get("snapshot", ""))
            else:
                st.info(f"Yahoo snapshot unavailable: {yahoo.get('error', 'unknown')}")
                st.caption("Tip: `pip install yfinance pandas` and ensure ticker mapping is available.")

        with c2:
            st.markdown("**News Sources (Google News RSS, free)**")
            if query:
                st.caption(f"Query: {query}")
            if not items:
                st.info("No news items fetched.")
            else:
                for it in items[:10]:
                    title = it.get("headline", "(no title)")
                    url = it.get("url", "")
                    src = it.get("source", "")
                    pub = it.get("published", "")
                    line = f"- [{title}]({url})" if url else f"- {title}"
                    if src:
                        line += f" — *{src}*"
                    if pub:
                        line += f" — {pub}"
                    st.markdown(line)


def scores_to_row(bank: str, scores: Dict[str, Any]) -> Dict[str, Any]:
    pillar = scores.get("pillar_scores", {}) or {}
    e = float(pillar.get("E", scores.get("E", 0.0)) or 0.0)
    s = float(pillar.get("S", scores.get("S", 0.0)) or 0.0)
    g = float(pillar.get("G", scores.get("G", 0.0)) or 0.0)
    final = float(scores.get("final", 0.0) or 0.0)
    label = scores.get("label", "N/A")
    return {"Bank": bank, "E": e, "S": s, "G": g, "Final": final, "Label": label}


def render_compare_charts(df: pd.DataFrame):
    if df.empty:
        return

    st.markdown("### 📈 Charts")

    try:
        import altair as alt
    except Exception:
        st.caption("Altair not available; skipping charts.")
        return

    # ---------- Final ESG Score (瘦一点的柱状图) ----------
    st.markdown("**Final ESG Score**")
    df_final = df[["Bank", "Final"]].reset_index(drop=True)

    chart_final = (
        alt.Chart(df_final)
        .mark_bar()
        .encode(
            x=alt.X("Bank:N", sort="-y"),
            y=alt.Y("Final:Q"),
            tooltip=["Bank", "Final"],
        )
        # 控制宽 / 高，不用自适应整行宽度
        .properties(width=360, height=260)
    )
    st.altair_chart(chart_final, use_container_width=False)

    # ---------- E / S / G Comparison ----------
    st.markdown("**E / S / G Comparison**")
    melted = df.melt(
        id_vars=["Bank"],
        value_vars=["E", "S", "G"],
        var_name="Pillar",
        value_name="Score",
    )

    chart_esg = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("Bank:N", sort="-y"),
            y=alt.Y("Score:Q"),
            xOffset="Pillar:N",
            color="Pillar:N",
            tooltip=["Bank", "Pillar", "Score"],
        )
        .properties(width=380, height=260)
    )

    st.altair_chart(chart_esg, use_container_width=False)



# ============================================================
# MODE 1 — Single Bank Analysis
# ============================================================
if mode == "Single Bank Analysis":
    st.title("🔍 Single Bank ESG Analysis")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        bank = st.selectbox("Select a Dutch Bank", BANK_LIST)
        manual_bank = st.text_input("Or type bank name manually (optional)")
        if manual_bank.strip():
            bank = manual_bank.strip()

        year = st.text_input("Year / Period (optional)", placeholder="e.g. 2023 or 2020–2024")

        # Make the box larger to avoid truncation
        question = st.text_area(
            "ESG Question (optional)",
            placeholder=(
                "Example: Assess ING’s ESG performance in 2023 focusing on: "
                "(1) climate transition & financed emissions, "
                "(2) AML/KYC enforcement risks, "
                "(3) board oversight & CSRD readiness."
            ),
            height=160,
        )
        st.caption("Tip: You can paste long multi-part questions here; the box is intentionally tall.")

    with col_right:
        uploaded_pdf = st.file_uploader("Upload ESG / Sustainability PDF (optional)", type=["pdf"])

    st.markdown("---")

    if st.button("Run ESG Analysis", type="primary"):
        # 先看 compare 模式有没有跑过，且有没有这个 bank 的结果
        cache = st.session_state.get("compare_cache")
        if cache and bank in (cache.get("per_bank_results") or {}):
            # 直接用 compare_banks 得到的完整结果，保证和 ESG Comparison Table 一致
            st.info("✅ Using cached comparison result for this bank (same as ESG Comparison Table).")
            result = cache["per_bank_results"][bank]
        else:
            # 没有缓存，就正常跑一遍 LLM（可能会很慢）
            st.info("⏳ Running analysis…")
            pdf_text = extract_pdf_text(uploaded_pdf)

            result = server.analyze_bank(
                bank=bank,
                question=question or "",
                year=year or "",
                pdf_text=pdf_text,
                pdf_filename=uploaded_pdf.name if uploaded_pdf else None,
            )

        if not result.get("ok"):
            st.error(f"❌ Failed: {result.get('error')}")
            with st.expander("Traceback"):
                st.code(result.get("traceback", ""))
        else:
            scores = result["scores"]
            final_report = result.get("final_report", "")
            used_fallback = (result.get("raw", {}) or {}).get("used_fallback_from_yahoo", False)


            if used_fallback:
                st.warning("ℹ️ LLM categories looked low-information; scores were auto-derived from Yahoo/news signals to ensure differentiation.")

            # Cards
            render_score_cards(scores)

            # Radar + MC
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("### 📊 ESG Radar Chart")
                render_radar(scores, result.get("bank", bank))
            with c2:
                render_mc_table(scores)

            # Subscores
            render_subscore_table(scores)

            # Report + Sources
            st.markdown("---")
            tabs = st.tabs(["📘 Final Report", "🧾 Sources"])
            with tabs[0]:
                st.markdown(final_report if final_report else "_No report returned._")
            with tabs[1]:
                render_sources_block(result)


# ============================================================
# MODE 2 — Compare Banks
# ============================================================
elif mode == "Compare Banks":
    st.title("🏆 Compare Dutch Banks")

    st.markdown("Compare banks using the same focus question. The system uses free sources (Yahoo + Google News RSS) and a rubric engine.")

    banks = st.multiselect("Select banks to compare", BANK_LIST, default=BANK_LIST[:3])

    year = st.text_input("Year / Period (optional, applied to all banks)", "")

    comparison_question = st.text_area(
        "Comparison Question / Focus (optional)",
        placeholder=(
            "Compare these banks on:\n"
            "1) Climate transition credibility (targets, financed emissions, taxonomy alignment)\n"
            "2) AML/KYC & compliance risk (recent enforcement, control maturity)\n"
            "3) Governance strength (board oversight, remuneration linkage, CSRD readiness)\n"
            "Then provide a ranked conclusion and key limitations."
        ),
        height=180,
    )

    uploaded_pdf = st.file_uploader("Upload a common ESG PDF (optional, shared across all banks)", type=["pdf"])

    st.markdown("---")

    if st.button("Run Comparison", type="primary"):
        if not banks:
            st.warning("Please select at least one bank.")
            st.stop()

        st.info("⏳ Running comparison…")

        pdf_text = extract_pdf_text(uploaded_pdf)
        pdf_texts = {b: pdf_text for b in banks}

        result = server.compare_banks(
            banks=banks,
            year=year or "",
            pdf_texts=pdf_texts,
            comparison_question=comparison_question or "",
        )

        if not result.get("ok", False):
            st.error(f"❌ Comparison failed: {result.get('error')}")
            with st.expander("Traceback"):
                st.code(result.get("traceback", ""))
            st.stop()

        scores_map = result.get("results", {}) or {}  # bank -> scores
        per_bank_results = result.get("per_bank_results", {}) or {}  # bank -> full result (optional)
        # 把这次 compare 的结果塞进 session_state，给 Single 模式复用
        st.session_state["compare_cache"] = {
            "scores_map": scores_map,
            "per_bank_results": per_bank_results,
            "year": year or "",
            "comparison_question": comparison_question or "",
        }
        summary = result.get("comparison_summary", "")
        errors = result.get("errors", {}) or {}

        if errors:
            st.warning("Some banks failed to analyse (see details below).")
            with st.expander("Per-bank errors"):
                st.write(errors)

        # Table
        st.markdown("### 📊 ESG Comparison Table")
        rows = [scores_to_row(bank, sc) for bank, sc in scores_map.items()]
        df = pd.DataFrame(rows).sort_values("Final", ascending=False)

        # 调整样式：字体、对齐、间距
        styled = (
            df.style
            .set_properties(**{
                "font-size": "15px",
                "text-align": "center",
                "line-height": "1.6",
                "padding": "6px 8px"
            })
        )

        # 自动计算高度（完全展示，不滚动）
        table_height = 120 + 32 * len(df)

        st.dataframe(
            styled,
            use_container_width=False,  # 不再拉伸全宽
            width=820,                  # 宽度锁定在 800~850 都行
            height=table_height,
            hide_index=True
        )

        
        # Charts
        render_compare_charts(df)

        # Summary
        st.markdown("---")
        st.markdown("### 📘 Comparison Summary (LLM)")
        st.markdown(summary if summary else "_No summary returned._")

        # Radar for every bank
        st.markdown("---")
        st.markdown("### 📡 Radar Charts (All Selected Banks)")
        bank_order = df["Bank"].tolist()

        cols_per_row = 3
        for i in range(0, len(bank_order), cols_per_row):
            row_banks = bank_order[i : i + cols_per_row]
            cols = st.columns(len(row_banks))
            for j, b in enumerate(row_banks):
                with cols[j]:
                    st.markdown(f"**{b}**")
                    render_radar(scores_map[b], b)

        # Drill-down
        st.markdown("---")
        st.markdown("### 🔍 Drill-down (per bank)")
        for b in bank_order:
            with st.expander(f"Details — {b}", expanded=False):
                sc = scores_map[b]
                render_score_cards(sc)
                c1, c2 = st.columns([1, 1])
                with c1:
                    render_radar(sc, b)
                with c2:
                    render_mc_table(sc)

                render_subscore_table(sc)

                # If server returned per-bank full results, show sources + report
                full = per_bank_results.get(b)
                if isinstance(full, dict):
                    tabs = st.tabs(["📘 Report", "🧾 Sources"])
                    with tabs[0]:
                        st.markdown(full.get("final_report", "") or "_No report returned._")
                    with tabs[1]:
                        render_sources_block(full)
                else:
                    st.caption("No per-bank detailed payload returned by server (this is optional).")
