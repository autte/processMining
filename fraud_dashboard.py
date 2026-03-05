import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import plotly.express as px

st.set_page_config(layout="wide")

st.title("Billing Fraud Detection with Knowledge Graph")

# ---------------------------
# LOAD DATA
# ---------------------------

df = pd.read_csv("billing_data.csv")

date_cols = [
"CREATETIME",
"EFFECTIVEDATE",
"UPDATETIME",
"PRE_CREATEDT",
"PRE_EFFDT",
"PRE_UPDT",
"POLICYPEREFFDATE",
"POLICYPEREXPIRDATE"
]

for c in date_cols:
    df[c] = pd.to_datetime(df[c], errors="coerce")

# ---------------------------
# FRAUD DETECTION RULES
# ---------------------------

fraud_cases = []

for i,row in df.iterrows():

    risk = 0
    reasons = []

    # rule 1 effective date manipulation
    if row["EFFECTIVEDATE"] < row["CREATETIME"]:
        risk += 20
        reasons.append("effective date earlier than create date")

    # rule 2 policy period violation
    if row["EFFECTIVEDATE"] < row["POLICYPEREFFDATE"] or row["EFFECTIVEDATE"] > row["POLICYPEREXPIRDATE"]:
        risk += 25
        reasons.append("transaction outside policy period")

    # rule 3 large transaction
    if abs(row["TRANSACTIONAMOUNT_AMT"]) > 1000:
        risk += 15
        reasons.append("large transaction")

    # rule 4 description change
    if str(row["DESCRIPTION"]) != str(row["PRE_DESC"]):
        risk += 10
        reasons.append("description changed")

    # rule 5 event type change
    if str(row["EVENTTYPE"]) != str(row["PRE_EVENTTYPE"]):
        risk += 15
        reasons.append("event type changed")

    if risk > 0:

        fraud_cases.append({
        "publicid":row["PUBLICID"],
        "policy":row["POLICYNUMBER"],
        "account":row["ACCOUNTNAME"],
        "user":row["CREATEUSERID"],
        "amount":row["TRANSACTIONAMOUNT_AMT"],
        "risk_score":risk,
        "reasons":",".join(reasons),
        "created":row["CREATETIME"]
        })

fraud_df = pd.DataFrame(fraud_cases)

# ---------------------------
# KPI
# ---------------------------

col1,col2,col3 = st.columns(3)

col1.metric("Total Events",len(df))
col2.metric("Fraud Cases",len(fraud_df))

if len(df)>0:
    col3.metric("Fraud Rate %",round(len(fraud_df)/len(df)*100,2))

st.divider()

# ---------------------------
# TIMELINE
# ---------------------------

st.subheader("Transaction Timeline")

timeline = df.groupby(df["CREATETIME"].dt.date)["TRANSACTIONAMOUNT_AMT"].sum().reset_index()

fig = px.line(timeline,x="CREATETIME",y="TRANSACTIONAMOUNT_AMT")

st.plotly_chart(fig,use_container_width=True)

# ---------------------------
# FILTERS
# ---------------------------

st.sidebar.header("Filters")

policy_filter = st.sidebar.multiselect(
"Policy",
df["POLICYNUMBER"].unique()
)

if policy_filter:
    fraud_df = fraud_df[fraud_df["policy"].isin(policy_filter)]

# ---------------------------
# FRAUD TABLE
# ---------------------------

st.subheader("Fraud Cases")

st.dataframe(fraud_df,use_container_width=True)

# ---------------------------
# CASE INVESTIGATION
# ---------------------------

if len(fraud_df)>0:

    case_id = st.selectbox("Select Case",fraud_df["publicid"])

    case = df[df["PUBLICID"]==case_id].iloc[0]

    st.subheader("Case Details")

    st.write(case)

    # ---------------------------
    # VERSION COMPARISON
    # ---------------------------

    st.subheader("Version Comparison")

    compare = pd.DataFrame({
    "Field":["EVENTTYPE","DESCRIPTION","CREATETIME","EFFECTIVEDATE"],
    "Current":[
        case["EVENTTYPE"],
        case["DESCRIPTION"],
        case["CREATETIME"],
        case["EFFECTIVEDATE"]
    ],
    "Previous":[
        case["PRE_EVENTTYPE"],
        case["PRE_DESC"],
        case["PRE_CREATEDT"],
        case["PRE_EFFDT"]
    ]
    })

    st.table(compare)

    # ---------------------------
    # KNOWLEDGE GRAPH
    # ---------------------------

    st.subheader("Knowledge Graph")

    G = nx.Graph()

    event = case["PUBLICID"]
    policy = case["POLICYNUMBER"]
    account = case["ACCOUNTNAME"]
    user = case["CREATEUSERID"]

    G.add_node(event)
    G.add_node(policy)
    G.add_node(account)
    G.add_node(user)

    G.add_edge(event,policy)
    G.add_edge(event,account)
    G.add_edge(event,user)

    net = Network(height="500px",width="100%")

    for node in G.nodes():
        net.add_node(node,label=node)

    for edge in G.edges():
        net.add_edge(edge[0],edge[1])

    net.save_graph("graph.html")

    HtmlFile=open("graph.html","r",encoding="utf-8")

    st.components.v1.html(HtmlFile.read(),height=500)

    # ---------------------------
    # AI EXPLANATION
    # ---------------------------

    case_info = fraud_df[fraud_df["publicid"]==case_id].iloc[0]

    explanation = f"""
    Event {case_id} is flagged.

    Risk Score: {case_info.risk_score}

    Reasons:
    {case_info.reasons}

    Policy: {case_info.policy}

    Amount: {case_info.amount}
    """

    st.warning(explanation)