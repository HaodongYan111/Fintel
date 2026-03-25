# tools/radar_chart.py

import matplotlib.pyplot as plt
import numpy as np


def create_esg_radar_chart(
    e_score=None,
    s_score=None,
    g_score=None,
    bank_name="Bank",
):
    """
    Create a compact radar chart for ESG scores.
    Optimized for Streamlit dashboard (Small Size).
    """

    if isinstance(e_score, dict):
        scores = {
            "E": safe_score(e_score.get("E", 0)),
            "S": safe_score(e_score.get("S", 0)),
            "G": safe_score(e_score.get("G", 0)),
        }
    else:
        scores = {
            "E": safe_score(e_score or 0),
            "S": safe_score(s_score or 0),
            "G": safe_score(g_score or 0),
        }

    labels = list(scores.keys())
    values = list(scores.values())

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

       # 👇 尺寸改成“瘦长型”：竖直稍微高一点，方便截屏贴 PPT
    fig, ax = plt.subplots(figsize=(2,2), subplot_kw=dict(polar=True))

    ax.plot(angles, values, linewidth=1.3, color="#1f77b4")
    ax.fill(angles, values, alpha=0.25, color="#1f77b4")

    ax.set_xticks(angles[:-1])
    # 字体再缩小一点
    ax.set_xticklabels(labels, fontsize=8)

    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_ylim(0, 100)
    # y 轴刻度也更小，整体显得更紧凑
    ax.tick_params(axis="y", labelsize=6)

    # 标题紧凑一点，避免占太多高度
    ax.set_title(f"{bank_name}", fontsize=9, pad=3, y=1.03)

    plt.tight_layout()


    return fig


def safe_score(x):
    try:
        v = float(x)
    except:
        v = 0
    return max(0, min(100, v))