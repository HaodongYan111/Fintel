import streamlit as st
from agents import run_multiagent_pipeline

# ============================================================
#   B17 Finance Multi-Agent – Professional Web UI
# ============================================================

st.set_page_config(
    page_title="Finance Multi-Agent",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========= Global CSS: professional light finance style =========
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Optional: hide default Streamlit chrome */
header {visibility: hidden;}
footer {visibility: hidden;}

/* Overall background */
.stApp {
    background-color: #F4F6FA;
}

/* Main container */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1500px;
}

/* Title */
.app-title {
    font-size: 32px;
    font-weight: 800;
    color: #111827;
    letter-spacing: -0.03em;
    margin-bottom: 2px;
}

/* Subtitle */
.app-subtitle {
    font-size: 14px;
    color: #4B5563;
    margin-bottom: 8px;
}

/* Accent line */
.app-divider {
    border-bottom: 2px solid #2563EB;
    margin-top: 6px;
    margin-bottom: 20px;
}

/* Left input panel */
.input-panel {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}

/* Right main card */
.output-card {
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
    padding: 22px 24px;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}

/* Sources card */
.source-card {
    background: #F9FAFB;
    border-radius: 10px;
    border: 1px solid #E5E7EB;
    padding: 16px 20px;
    margin-top: 16px;
}

/* Debug card */
.debug-card {
    background: #FFFFFF;
    border-radius: 10px;
    border: 1px solid #E5E7EB;
    padding: 14px 18px;
    margin-top: 14px;
}

/* Labels */
.label-small {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 4px;
}

/* Inputs */
textarea, input {
    border-radius: 8px !important;
    border: 1px solid #D1D5DB !important;
    background-color: #FFFFFF !important;
    font-size: 14px !important;
}

/* Button */
.stButton>button {
    background-color: #2563EB;
    color: #FFFFFF;
    border-radius: 999px;
    border: none;
    padding: 8px 20px;
    font-size: 14px;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #1D4ED8;
}

/* Info text */
.helper-text {
    font-size: 12px;
    color: #6B7280;
}

/* Final answer text */
.analysis-body {
    font-size: 14px;
    line-height: 1.55;
    color: #111827;
}
</style>
""", unsafe_allow_html=True)

# ================= Header =================
st.markdown('<div class="app-title">B17 Finance Multi-Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Institutional-grade macro, sector, credit, and portfolio analysis – powered by your local model.</div>',
    unsafe_allow_html=True
)
st.markdown('<div class="app-divider"></div>', unsafe_allow_html=True)

# ================= Layout =================
left_col, right_col = st.columns([1.05, 2.0], gap="large")

# -------- Left: Input panel --------
with left_col:
    st.markdown('<div class="input-panel">', unsafe_allow_html=True)

    st.markdown('<div class="label-small">Finance question</div>', unsafe_allow_html=True)
    question = st.text_area(
        label="",
        placeholder="Example: How does a higher-for-longer interest rate regime affect large U.S. banks and institutional portfolios?",
        height=150,
    )

    st.markdown('<div class="label-small" style="margin-top:10px;">Primary ticker (optional)</div>', unsafe_allow_html=True)
    ticker = st.text_input(
        label="",
        placeholder="e.g., JPM  (leave blank for pure macro / credit / portfolio questions)",
    )

    show_debug = st.checkbox("Show technical / agent breakdown", value=False)

    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
    run = st.button("Run institutional analysis", use_container_width=True)

    st.markdown(
        '<div class="helper-text" style="margin-top:10px;">'
        'Tip: Ask cross-asset questions like “How would a mild U.S. recession reshape bank funding risk and portfolio duration decisions?”'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

# -------- Right: Output / Results --------
with right_col:
    if run:
        if not question.strip():
            st.error("Please enter a finance question.")
        else:
            with st.spinner("Running multi-agent analysis…"):
                result = run_multiagent_pipeline(
                    question.strip(),
                    ticker.strip().upper() or None,
                )

            # ===== Final report card =====
            st.markdown('<div class="output-card">', unsafe_allow_html=True)
            st.subheader("Final institutional analysis")
            st.markdown('<div class="analysis-body">', unsafe_allow_html=True)
            st.write(result.get("answer", ""))
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ===== Sources (citations) =====
            sources = result.get("sources", [])
            if sources:
                st.markdown('<div class="source-card">', unsafe_allow_html=True)
                st.markdown("#### Sources", unsafe_allow_html=False)
                for i, s in enumerate(sources, 1):
                    title = s.get("title") or "Untitled source"
                    url = s.get("url")
                    origin = s.get("source")
                    if url:
                        if origin:
                            st.markdown(f"{i}. [{title}]({url})  \n<sub>{origin}</sub>", unsafe_allow_html=False)
                        else:
                            st.markdown(f"{i}. [{title}]({url})", unsafe_allow_html=False)
                    else:
                        if origin:
                            st.markdown(f"{i}. {title}  \n<sub>{origin}</sub>", unsafe_allow_html=False)
                        else:
                            st.markdown(f"{i}. {title}", unsafe_allow_html=False)
                st.markdown('</div>', unsafe_allow_html=True)

            # ===== Debug / technical details =====
            if show_debug:
                st.markdown('<div class="debug-card">', unsafe_allow_html=True)
                st.markdown("#### Technical details", unsafe_allow_html=False)
                st.write("**Active Tier-1 tags:**", result.get("tags", []))
                st.write("**Tier-2 specializations:**", result.get("tier2_subtags", {}))

                with st.expander("Per-agent raw outputs"):
                    st.write(result.get("agent_outputs", {}))

                with st.expander("Synthesizer raw text (before wrapper + sources):"):
                    st.write(result.get("raw_final", ""))

                st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Before running: show a small hint card instead of empty space
        st.markdown('<div class="output-card">', unsafe_allow_html=True)
        st.subheader("How to use this tool")
        st.markdown(
            """
This interface is designed for **institutional-style finance questions**, for example:

- *How does a higher-for-longer rate regime reshape bank profitability, funding costs, and credit risk?*  
- *What are the portfolio implications of a mild U.S. recession for duration and credit exposure?*  
- *How could renewed stress in commercial real estate affect regional banks and credit conditions?*

On the left:
- Enter your question (optionally add a primary ticker such as `JPM`).
- Click **“Run institutional analysis”**.

On the right:
- You will see a structured research-style note (Executive Summary, Macro, Sector, Credit, Portfolio, Scenarios, Risks).
- A **Sources** section lists the underlying data / news / web items used to support the answer.
            """,
            unsafe_allow_html=False,
        )
        st.markdown('</div>', unsafe_allow_html=True)
