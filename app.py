import streamlit as st
import pandas as pd
from utils import load_data, normalize_data
from scoring import calculate_score, decision
from filters import apply_filters
from fetcher import fetch_projects

st.set_page_config(layout="wide")
st.title("🚀 Freelancer Alpha Dashboard")

st.header("🌐 Fetch Projects from Freelancer API")

auth_token = st.text_input("Freelancer Auth Token", type="password")

limit = st.slider("Projects per page", 10, 50, 20)
pages = st.slider("Number of pages (simulate unlimited)", 1, 20, 5)
max_price = st.slider("Max Budget Filter", 0, 5000, 100)

if st.button("🚀 Fetch Projects"):
    if not auth_token:
        st.error("Enter auth token")
    else:
        df = fetch_projects(auth_token, limit, max_price, pages)

        st.session_state["df"] = df
        st.success(f"Fetched {len(df)} projects")

# Upload
file = st.file_uploader("Upload Freelancer JSON", type=["json"])

df = None

if "df" in st.session_state:
    df = st.session_state["df"]

elif file:
    df = load_data(file)

if df is not None:
    df = normalize_data(df)

    # Sidebar Filters
    st.sidebar.header("Filters")

    keywords = st.sidebar.text_input(
        "Skills (comma separated)", "python, api, automation, ai"
    )
    keyword_list = [k.strip().lower() for k in keywords.split(",")]

    min_budget = st.sidebar.slider("Minimum Budget", 0, 5000, 100)
    max_bids = st.sidebar.slider("Max Bids", 0, 50, 20)
    min_score = st.sidebar.slider("Minimum Score", 0, 100, 40)

    # Scoring
    df["score"] = df.apply(lambda row: calculate_score(row, keyword_list), axis=1)
    df["decision"] = df["score"].apply(decision)

    # Apply filters
    df_filtered = apply_filters(df, keyword_list, min_budget, max_bids, min_score)

    # Sort
    df_filtered = df_filtered.sort_values(by="score", ascending=False)

    # Display table
    st.subheader("📊 Project Opportunities")

    display_cols = [
        "title",
        "budget_min",
        "budget_max",
        "bid_count",
        "client_verified",
        "score",
        "decision",
    ]

    st.dataframe(df_filtered[display_cols], use_container_width=True)

    # Select project
    selected_index = st.selectbox("Select Project", df_filtered.index)

    if selected_index:
        row = df_filtered.loc[selected_index]

        st.markdown("## 📌 Project Details")
        st.write(f"**Title:** {row['title']}")
        st.write(f"**Budget:** {row['budget_min']} - {row['budget_max']}")
        st.write(f"**Bids:** {row['bid_count']}")
        st.write(f"**Client Verified:** {row['client_verified']}")
        st.write(f"**Score:** {row['score']} ({row['decision']})")

        st.markdown("### 🧾 Description")
        st.write(row["description"])

        st.markdown("### 🧠 AI Insight")
        insight = []
        if row["bid_count"] < 5:
            insight.append("Low competition")
        if row["client_verified"]:
            insight.append("Trusted client")
        if row["budget_max"] > 500:
            insight.append("Decent budget")

        st.success(", ".join(insight))

    # Export
    if st.button("📤 Export Top 15"):
        top15 = df_filtered.head(15)
        top15.to_csv("shortlist.csv", index=False)
        st.success("Exported shortlist.csv")

else:
    st.info("Upload your JSON file to begin")
