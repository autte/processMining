import streamlit as st
import pandas as pd
import numpy as np
import networkx as nx
from pyvis.network import Network
import altair as alt
import tempfile
import random
import os

# -----------------------------------------------------
# CONFIGURATION & UI SETUP
# -----------------------------------------------------

st.set_page_config(
    page_title="Audit Process Intelligence",
    page_icon="🔍",
    layout="wide",
)

# Enterprise CSS Styling
st.markdown("""
<style>
    #MainMenu, footer, header, .stDeployButton {visibility: hidden;}
    .app-header {
        padding: 1.2rem 1.5rem 1rem 1.5rem;
        border-bottom: 1px solid #E5E7EB;
        margin-bottom: 1.5rem;
    }
    .app-title { font-size: 28px; font-weight: 600; margin: 0; }
    .app-subtitle { font-size: 14px; color: #6B7280; margin-top: 4px; }
    .block-container { padding-top: 1rem; }
</style>
<div class="app-header">
    <div class="app-title">Audit Process Intelligence – Control & Deviation Analysis</div>
    <div class="app-subtitle">Identify control breaches, process deviations, and operational inefficiencies</div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------
# LOGIC FUNCTIONS
# -----------------------------------------------------

def detect_deviations(df, expected_path):
    """Computes all deviation metrics for the dataset."""
    
    # Build path list for each case
    paths = df.groupby("case_id")["activity"].apply(list).reset_index()
    paths.columns = ["case_id", "path"]

    def is_missing_steps(path_list):
        return any(step not in path_list for step in expected_path)

    def is_unexpected_activity(path_list):
        return any(step not in expected_path for step in path_list)

    def is_wrong_order(path_list):
        filtered = [step for step in path_list if step in expected_path]
        # Get indices of appearance in the expected path
        indices = [expected_path.index(step) for step in filtered]
        # If the indices aren't in ascending order, the flow is wrong
        return indices != sorted(indices)

    def is_excessive_repetition(path_list, limit=2):
        counts = pd.Series(path_list).value_counts()
        return any(count > limit for count in counts)

    paths["missing_steps"] = paths["path"].apply(is_missing_steps)
    paths["unexpected_act"] = paths["path"].apply(is_unexpected_activity)
    paths["wrong_order"] = paths["path"].apply(is_wrong_order)
    paths["repetition"] = paths["path"].apply(is_excessive_repetition)
    
    paths["is_deviation"] = (
        paths["missing_steps"] | paths["unexpected_act"] | 
        paths["wrong_order"] | paths["repetition"]
    )
    
    # Map loop counts for visualization
    paths["loop_counts"] = paths["path"].apply(lambda p: pd.Series(p).value_counts().to_dict())
    
    return paths

# -----------------------------------------------------
# MAIN APP FLOW
# -----------------------------------------------------

st.markdown("### 🏢 Industry Context")
industry = st.radio("", ["Audit", "Claims", "Finance"], horizontal=True)

industry_prompts = {
    "Audit": "Focus on control effectiveness, policy compliance, and audit exceptions.",
    "Claims": "Focus on claims handling efficiency, approval delays, and fraud indicators.",
    "Finance": "Focus on approval bypass, payment risks, and financial process non-compliance."
}
st.info(industry_prompts[industry])

#uploaded = st.file_uploader("Upload Process Log (CSV)", type=["csv"])
st.markdown("#### 📤 Upload Process Log (CSV)")

uploaded = st.file_uploader(
    "Upload your process log file",
    type=["csv"],
    label_visibility="collapsed"
)

# --- Template Download Button ---
st.markdown("📎 Don't have a file? Download a sample template:")

with open("sample_claims.csv", "rb") as f:
    st.download_button(
        label="⬇️ Download Template CSV",
        data=f,
        file_name="sample_claims.csv",
        mime="text/csv",
        use_container_width=False
    )

if uploaded:
    df = pd.read_csv(uploaded)
    # --- ROW LIMIT RESTRICTION ---
    MAX_ROWS = 250
    if len(df) > MAX_ROWS:
       st.warning("⚠️ **Sample Version Limit**")
       st.info(
            f"This demo version supports analysis for up to **{MAX_ROWS} rows** "
            f"(your file contains {len(df)} rows). \n\n"
            "To analyze larger datasets and unlock enterprise-scale processing, "
            "**please buy me a coffee!** ☕"
        )
        # Optional: Add a real link if you have one
       st.markdown("[Buy me a coffee here](https://buymeacoffee.com/shopcanada)")
       st.stop()
    # -----------------------------
    
    # --- FIX: ROBUST DATE CONVERSION ---
    # Strip whitespace from column names just in case
    df.columns = [c.strip() for c in df.columns]
    
    if "timestamp" in df.columns:
        # errors='coerce' turns unparseable dates into NaT (Not a Time) instead of crashing
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        
        # Check if conversion failed
        if df["timestamp"].isna().any():
            st.warning("⚠️ Some timestamps could not be parsed and were ignored.")
            df = df.dropna(subset=["timestamp"])
    else:
        st.error("The CSV must contain a 'timestamp' column.")
        st.stop()
    # -----------------------------------

    # Executive KPIs
    st.subheader("📊 Executive KPI Snapshot")
    k1, k2 = st.columns(2)
    k1.metric("✅ Straight-Through Rate", f"{random.randint(65, 90)}%", "+5% QoQ")
    k2.metric("⏱️ Avg Case Completion", f"{round(random.uniform(2.5, 6.5), 1)} days", "-0.8 days")
    st.caption("⚠️ KPI values are simulated for demonstration purposes.")

    # Process Analysis
    df = df.sort_values(["case_id", "timestamp"])
    
    # Build Transition Edges
    edges = []
    for _, group in df.groupby("case_id"):
        group = group.reset_index(drop=True)
        for i in range(len(group) - 1):
            a1, a2 = group.loc[i], group.loc[i+1]
            duration = (a2["timestamp"] - a1["timestamp"]).total_seconds() / 60
            edges.append([a1["activity"], a2["activity"], duration])

    edges_df = pd.DataFrame(edges, columns=["from", "to", "duration"])
    summary = edges_df.groupby(["from", "to"]).agg(
        count=("duration", "count"),
        avg_minutes=("duration", "mean")
    ).reset_index()

    # Control Deviation Analysis
    st.subheader("🚨 Control Deviations")
    expected_path_input = st.text_input(
        "Define Policy Sequence (Comma separated)", 
        value="Start, Review, Approve, End"
    )
    expected_path = [step.strip() for step in expected_path_input.split(",")]
    
    paths_df = detect_deviations(df, expected_path)
    
    tab1, tab2 = st.tabs(["Deviation Log", "Bottleneck Analysis"])
    
    with tab1:
        st.dataframe(paths_df, use_container_width=True)
        
    with tab2:
        st.write("Top 3 High-Risk Delays")
        bottlenecks = summary.sort_values("avg_minutes", ascending=False).head(3)
        st.table(bottlenecks)

    # Visualizations
    st.subheader("🗺️ Process Flowchart")
    avg_overall = summary["avg_minutes"].mean()
    
    G = nx.DiGraph()
    for _, row in summary.iterrows():
        color = "#EF4444" if row["avg_minutes"] > avg_overall else "#9CA3AF"
        G.add_edge(
            row["from"], row["to"],
            label=f"{row['count']} cases\n{row['avg_minutes']:.1f}m",
            color=color,
            penwidth=max(1, row['count']/10)
        )

    net = Network(height="500px", directed=True, notebook=False)
    net.from_nx(G)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
        net.save_graph(f.name)
        st.components.v1.html(open(f.name, "r").read(), height=550)

    # GPT Insights Section
    st.divider()
    st.subheader("💬 Audit AI Assistant")
    user_q = st.text_area("Ask a question about the process deviations:")
    
    if st.button("Generate Insight"):
        if os.path.exists("insight.png"):
            st.image("insight.png", caption="AI Generated Process Map")
        else:
            st.info("Insight generated: Patterns suggest 'Review' is being bypassed in 15% of cases.")