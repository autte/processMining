import streamlit as st
# -----------------------------------------------------
# QUESTION & ANSWER (ChatGPT Integration)
# -----------------------------------------------------


# Must be the first Streamlit command
st.set_page_config(
    page_title="A's Process Mining Viewer",
    page_icon=".streamlit/icon.png",
    layout="wide",
)


# Hide Streamlit UI elements
hide_streamlit_style = """
    <style>
        /* Hide MainMenu (the 3 dots) */
        #MainMenu {visibility: hidden;}

        /* Hide Streamlit footer */
        footer {visibility: hidden;}

        /* Hide deploy button */
        .stDeployButton {display: none;}

        /* Hide header entirely */
        header {visibility: hidden;}

        /* Hide top-right hamburger menu */
        .css-1adrfps {visibility: hidden;}

        /* Hide floating toolbar inside the app */
        .st-emotion-cache-16idsys {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title(" A's Protocol - Process Mining Viewer")
import pandas as pd
import networkx as nx
from pyvis.network import Network
import altair as alt
import tempfile


uploaded = st.file_uploader("Upload CSV (case_id, activity, timestamp)", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    # -----------------------------------------------------
    # KPI IMAGE SECTION
    # -----------------------------------------------------
    st.subheader("📊 Sam's KPI and power BI Miner")
    kpi_url = st.text_input("Enter KPI Image URL")

    if kpi_url:
        st.image(kpi_url, caption="KPI Indicator", use_column_width=True)
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sort data
    df = df.sort_values(["case_id", "timestamp"])

    # Build edges (event → next event)
    edges = []
    for case_id, group in df.groupby("case_id"):
        group = group.reset_index(drop=True)
        for i in range(len(group) - 1):
            a1 = group.loc[i]
            a2 = group.loc[i+1]
            duration = (a2["timestamp"] - a1["timestamp"]).total_seconds() / 60
            edges.append([a1["activity"], a2["activity"], duration])

    edges_df = pd.DataFrame(edges, columns=["from", "to", "duration"])

    # -----------------------------------------------------
    # TRANSITION SUMMARY
    # -----------------------------------------------------
    summary = edges_df.groupby(["from", "to"]).agg(
        count=("duration", "count"),
        avg_minutes=("duration", "mean")
    ).reset_index()

    st.subheader("Transition Statistics")
    st.dataframe(summary)

    # -----------------------------------------------------
    # PROCESS VARIANTS + DEVIATIONS
    # -----------------------------------------------------
    st.subheader("Process Variants & Deviations")

    # Build path list for each case
    paths = df.groupby("case_id")["activity"].apply(list).reset_index()
    paths.columns = ["case_id", "path"]

    # Expected process model (customize for your business)
    expected_path = ["Start", "Review", "Approve", "End"]

    # Deviation rules
    def missing_steps_func(path_list):
        return any(step not in path_list for step in expected_path)

    def unexpected_activities_func(path_list):
        return any(step not in expected_path for step in path_list)

    def wrong_order_func(path_list):
        filtered = [step for step in path_list if step in expected_path]
        indices = [expected_path.index(step) for step in filtered]
        return indices != sorted(indices)

    def is_deviation_func(path_list):
        return (
            missing_steps_func(path_list)
            or unexpected_activities_func(path_list)
            or wrong_order_func(path_list)
            or path_list != expected_path
        )
        
    def missing_steps_func(path_list):
        """Did the required steps appear AT LEAST once?"""
        return any(step not in path_list for step in expected_path)    


    def unexpected_activities_func(path_list):
        """Did the path contain activities not in the model?"""
        return any(step not in expected_path for step in path_list)


    def wrong_order_func(path_list):
        """
        Are required steps in the correct ORDER,
        even if other steps are repeated or occur in between?
        """
        filtered = [step for step in path_list if step in expected_path]
        indices = [expected_path.index(step) for step in filtered]
        return indices != sorted(indices)


    def excessive_repetition_func(path_list, max_loops=5):
        """
        Did a step appear too many times? (possible fraud or inefficiency)
        Example: Reject appears 7 times.
        """
        counts = pd.Series(path_list).value_counts()
        return any(count > max_loops for count in counts)
        

    def is_deviation_func(path_list):
        """
        Full deviation detection:
        - missing required steps
        - extra illegal steps
        - wrong order
        - too many loops
        """
        return (
            missing_steps_func(path_list)
            or unexpected_activities_func(path_list)
            or wrong_order_func(path_list)
            or excessive_repetition_func(path_list)
        )

    # Apply deviation functions
    paths["missing_steps"] = paths["path"].apply(missing_steps_func)
    paths["unexpected_activities"] = paths["path"].apply(unexpected_activities_func)
    paths["wrong_order"] = paths["path"].apply(wrong_order_func)
    paths["is_deviation"] = paths["path"].apply(is_deviation_func)
    paths["loop_counts"] = paths["path"].apply(
    lambda p: pd.Series(p).value_counts().to_dict()
)

    st.dataframe(paths)
     # ---------------------------------------------------------
    # CASES WITH REPEATED STEPS (LOOPS)
    # ---------------------------------------------------------
    loop_cases = paths[
        paths["loop_counts"].apply(lambda x: any(v > 1 for v in x.values()))
    ]

    st.subheader("🔁 Cases with Loops (Repeated Activities)")
    st.dataframe(loop_cases)


    # -----------------------------------------------------
    # BOTTLENECK DETECTION
    # -----------------------------------------------------
    st.subheader("Top Bottlenecks (Slowest Steps)")

    bottlenecks = summary.sort_values("avg_minutes", ascending=False).head(3)
    st.dataframe(bottlenecks)

    avg_overall = summary["avg_minutes"].mean()

    # -----------------------------------------------------
    # FLOWCHART (PyVis)
    # -----------------------------------------------------
    st.subheader("Process Flowchart")

    G = nx.DiGraph()

    for _, row in summary.iterrows():
        color = "red" if row["avg_minutes"] > avg_overall else "gray"
        G.add_edge(
            row["from"], row["to"],
            label=f"{row['count']} cases\n{row['avg_minutes']:.1f} min",
            color=color
        )

    net = Network(height="500px", directed=True)
    net.from_nx(G)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
        net.save_graph(f.name)
        html_path = f.name

    st.components.v1.html(open(html_path, "r").read(), height=550)

    # -----------------------------------------------------
    # BAR CHART (Altair)
    # -----------------------------------------------------
    st.subheader("Average Duration per Transition")

    chart = alt.Chart(summary).mark_bar().encode(
        x=alt.X("from:N", title="From Activity"),
        xOffset="to:N",
        y=alt.Y("avg_minutes:Q", title="Avg Duration (Minutes)"),
        color="to:N",
        tooltip=["from", "to", "avg_minutes", "count"]
    ).properties(height=400)

    st.altair_chart(chart, use_container_width=True)
    # -----------------------------------------------------
    # CHATGPT QUESTION & ANSWER SECTION
    # -----------------------------------------------------
    st.subheader("💬 Ask GPT Anything About Your Process")
    # Create OpenAI client
    #client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # User question
    user_question = st.text_area("Enter your question about the uploaded process log:")

    if st.button("Get Answer"):
        with st.spinner("Thinking..."):
            try:
                # Load image stored in the same folder as flow_viewer.py
                st.image("insight.png", caption="Process Insight Image", use_column_width=True)
            except Exception as e:
                st.error(f"Error loading image: {e}")

      
