import pycountry
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

query = st.text_input("Search Query (e.g. python, trading, scraping)", "python")
limit = st.slider("Projects per page", 10, 50, 20, step=5)
pages = st.slider("Number of pages (simulate unlimited)", 1, 20, 5)
max_price = st.slider("Max Budget Filter (USD)", 0, 5000, 1000, step=100)
refresh_cache = st.checkbox("Refresh Cache")

COUNTRY_OPTIONS = {f"{c.name} ({c.alpha_2.lower()})": c.alpha_2.lower() for c in sorted(pycountry.countries, key=lambda x: x.name)}
LANGUAGE_OPTIONS = {f"{l.name} ({l.alpha_2})": l.alpha_2 for l in sorted(pycountry.languages, key=lambda x: x.name) if hasattr(l, 'alpha_2')}

selected_countries = st.multiselect("Countries", options=list(COUNTRY_OPTIONS.keys()), default=[])
default_lang = [k for k in LANGUAGE_OPTIONS if LANGUAGE_OPTIONS[k] == "en"]
selected_languages = st.multiselect("Languages", options=list(LANGUAGE_OPTIONS.keys()), default=default_lang[:1])

if st.button("🚀 Fetch Projects"):
    if not auth_token:
        st.error("Enter auth token")
    else:
        countries = [COUNTRY_OPTIONS[c] for c in selected_countries]
        languages = [LANGUAGE_OPTIONS[l] for l in selected_languages]
        df = fetch_projects(auth_token, query, limit, max_price, pages, refresh_cache, countries, languages)

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

    min_budget = st.sidebar.slider("Minimum Budget (USD)", 0, 500, 100, step=10)
    max_bids = st.sidebar.slider("Max Bids", 0, 500, 20, step=5)
    min_score = st.sidebar.slider("Minimum Score", 0, 100, 40)
    lang_options = df["language"].dropna().unique().tolist()
    languages = st.sidebar.multiselect(
        "Preferred Languages",
        options=lang_options,
        default=[x for x in ["en"] if x in lang_options],
        format_func=lambda x: (lang := pycountry.languages.get(alpha_2=x)) and f"{x} ({lang.name})" or x,
    )

    loc_options = df["location_code"].dropna().unique().tolist()
    location = st.sidebar.multiselect(
        "Preferred Locations",
        options=loc_options,
        default=[x for x in ["in"] if x in loc_options],
        format_func=lambda x: (country := pycountry.countries.get(alpha_2=x.upper())) and f"{x} ({country.name})" or x,
    )

    # Scoring
    df["score"] = df.apply(lambda row: calculate_score(row, keyword_list), axis=1)
    df["decision"] = df["score"].apply(decision)

    # Apply filters
    df_filtered = apply_filters(df, keyword_list, min_budget, max_bids, min_score, languages, location)

    # Sort
    df_filtered = df_filtered.sort_values(by="score", ascending=False)

    # Display table
    st.subheader("📊 Project Opportunities")

    display_cols = [
        "title",
        "budget_min",
        "budget_max",
        "currency_code",
        "bid_count",
        "client_verified",
        "score",
        "decision",
        "submitdate",
    ]

    st.dataframe(df_filtered[display_cols], width='stretch', height=500)

    # Select project
    selected_index = st.selectbox(
        "Select Project",
        df_filtered.index,
        format_func=lambda x: f"{x}: {df_filtered.loc[x, 'title']}",
        placeholder="Type to search or select a project..."
    )

    if selected_index:
        row = df_filtered.loc[selected_index]
        sign = (
            row["currency"]["sign"]
            if "currency" in row and "sign" in row["currency"]
            else "?"
        )
        code = (
            row["currency"]["code"]
            if "currency" in row and "code" in row["currency"]
            else "NA"
        )

        st.markdown("## 📌 Project Details")
        url = f"https://www.freelancer.com/projects/{row['seo_url']}"
        st.markdown(f"##### Title: [{row['title']}]({url})")
        escaped_sign = f"\\{sign}"
        st.write(f"**Budget:** {escaped_sign}{row['budget_min']} - {escaped_sign}{row['budget_max']} ({code})")
        st.write(f"**Bids:** {row['bid_count']}")
        st.write(f"**Client Verified:** {row['client_verified']}")
        st.write(f"**Score:** {row['score']} ({row['decision']})")
        st.write(f"**Skills:** {', '.join(row['skills_list'])}")

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
