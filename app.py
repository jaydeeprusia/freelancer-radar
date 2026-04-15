import json
import pycountry
import streamlit as st
import pandas as pd
from utils import load_data, normalize_data
from scoring import (
    calculate_score,
    get_component_scores,
    decision,
    generate_insights,
    DEFAULT_WEIGHTS,
)
from filters import apply_filters
from fetcher import fetch_projects

st.set_page_config(layout="wide")
st.title("🚀 Freelancer Alpha Dashboard")

# ── Fetch UI ─────────────────────────────────────────────────────────────────
st.header("🌐 Fetch Projects from Freelancer API")

auth_token = st.text_input("Freelancer Auth Token", type="password")
query = st.text_input("Search Query", "python")
col1, col2, col3 = st.columns(3)
limit = col1.slider("Projects per page", 10, 50, 20, step=5)
pages = col2.slider("Pages", 1, 20, 5)
max_price = col3.slider("Max Budget (USD)", 0, 5000, 1000, step=100)
refresh_cache = st.checkbox("Refresh Cache")

COUNTRY_OPTIONS = {
    f"{c.name} ({c.alpha_2.lower()})": c.alpha_2.lower()
    for c in sorted(pycountry.countries, key=lambda x: x.name)
}
LANGUAGE_OPTIONS = {
    f"{l.name} ({l.alpha_2})": l.alpha_2
    for l in sorted(pycountry.languages, key=lambda x: x.name)
    if hasattr(l, "alpha_2")
}

selected_countries = st.multiselect(
    "Countries (API filter)", options=list(COUNTRY_OPTIONS.keys()), default=[]
)
default_lang = [k for k in LANGUAGE_OPTIONS if LANGUAGE_OPTIONS[k] == "en"]
selected_languages = st.multiselect(
    "Languages (API filter)",
    options=list(LANGUAGE_OPTIONS.keys()),
    default=default_lang[:1],
)

if st.button("🚀 Fetch Projects"):
    if not auth_token:
        st.error("Enter auth token")
    else:
        countries = [COUNTRY_OPTIONS[c] for c in selected_countries]
        languages = [LANGUAGE_OPTIONS[l] for l in selected_languages]
        df = fetch_projects(
            auth_token,
            query,
            limit,
            max_price,
            pages,
            refresh_cache,
            countries,
            languages,
        )
        st.session_state["df"] = df
        st.success(f"Fetched {len(df)} projects")

# ── Upload fallback ───────────────────────────────────────────────────────────
file = st.file_uploader("Upload Freelancer JSON", type=["json"])
df = None

if "df" in st.session_state:
    df = st.session_state["df"]
elif file:
    df = load_data(file)

if df is None:
    st.info("Fetch or upload a JSON file to begin")
    st.stop()

df = normalize_data(df)

# ═════════════════════════════════════════════════════════════════════════════
# ⚙️  SCORING CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════
with st.expander("⚙️ Scoring Configuration", expanded="loaded_preset" in st.session_state):
    st.markdown("Adjust weights and toggle factors. Weights are auto-normalised.")

    preset_col, save_col, load_col = st.columns([2, 1, 1])
    preset_name = preset_col.text_input("Preset name", "my_preset")

    weights, enabled = {}, {}
    factor_labels = {
        "skill": "🎯 Skill Match",
        "budget": "💰 Budget",
        "competition": "⚔️ Competition",
        "client": "👤 Client Quality",
        "urgency": "🔥 Urgency",
        "freshness": "🕐 Freshness",
        "complexity": "🧠 Complexity",
    }

    loaded_preset = st.session_state.get("loaded_preset", {})

    # Initialise widget state with defaults on first run
    for k in factor_labels:
        if f"w_{k}" not in st.session_state:
            st.session_state[f"w_{k}"] = DEFAULT_WEIGHTS[k]
        if f"e_{k}" not in st.session_state:
            st.session_state[f"e_{k}"] = True

    # Apply loaded preset values into widget keys before rendering
    if loaded_preset:
        for k in factor_labels:
            if k in loaded_preset.get("weights", {}):
                st.session_state[f"w_{k}"] = float(loaded_preset["weights"][k])
            if k in loaded_preset.get("enabled", {}):
                st.session_state[f"e_{k}"] = bool(loaded_preset["enabled"][k])
        del st.session_state["loaded_preset"]

    for key, label in factor_labels.items():
        c1, c2, c3 = st.columns([2, 3, 1])
        c1.markdown(f"**{label}**")
        weights[key] = c2.slider(
            f"w_{key}", 0.0, 1.0, step=0.05,
            key=f"w_{key}", label_visibility="collapsed"
        )
        enabled[key] = c3.checkbox(
            f"e_{key}",
            key=f"e_{key}", label_visibility="collapsed"
        )

    total_w = sum(v for k, v in weights.items() if enabled.get(k))
    st.caption(f"Active weight sum: **{total_w:.2f}** (auto-normalised during scoring)")

    if save_col.button("💾 Save Preset"):
        preset = {"weights": weights, "enabled": enabled}
        fname = f"{preset_name}.json"
        with open(fname, "w") as f:
            json.dump(preset, f, indent=2)
        st.success(f"Saved {fname}")

    uploaded_preset = load_col.file_uploader(
        "📂 Load Preset", type=["json"], key="preset_upload"
    )
    if load_col.button("📂 Apply Preset") and uploaded_preset:
        st.session_state["loaded_preset"] = json.load(uploaded_preset)
        st.rerun()

# ── Scoring ───────────────────────────────────────────────────────────────────
keywords_raw = st.sidebar.text_input(
    "Skills (comma separated)", "python, api, automation, ai"
)
keyword_list = [k.strip().lower() for k in keywords_raw.split(",") if k.strip()]

df["score"] = df.apply(
    lambda r: calculate_score(r, keyword_list, weights, enabled), axis=1
)
df["decision"] = df["score"].apply(decision)

# ═════════════════════════════════════════════════════════════════════════════
# 🔍  SIDEBAR FILTERS
# ═════════════════════════════════════════════════════════════════════════════
st.sidebar.header("🔍 Filters")

min_budget = st.sidebar.slider("Min Budget (USD)", 0, 5000, 0, step=50)
min_bid = st.sidebar.slider("Min Bids", 0, 100, 0)
max_bids = st.sidebar.slider("Max Bids", 0, 500, 50, step=5)
min_score = st.sidebar.slider("Min Score", 0, 100, 0)
max_hrs = st.sidebar.slider("Max Hours Since Posted", 1, 720, 720)
verified_only = st.sidebar.checkbox("Verified Clients Only")
featured_only = st.sidebar.checkbox("Featured Only")
urgent_only = st.sidebar.checkbox("Urgent Only")

skill_min, skill_max = st.sidebar.slider("Skill Count Range", 0, 20, (0, 20))

lang_opts = df["language"].dropna().unique().tolist()
filter_languages = st.sidebar.multiselect(
    "Language",
    options=lang_opts,
    default=[x for x in ["en"] if x in lang_opts],
    format_func=lambda x: (lang := pycountry.languages.get(alpha_2=x))
    and f"{x} ({lang.name})"
    or x,
)

loc_opts = [c for c in df["location_code"].dropna().unique().tolist() if c != "NA"]
filter_locations = st.sidebar.multiselect(
    "Client Location",
    options=loc_opts,
    default=[x for x in ["in"] if x in loc_opts],
    format_func=lambda x: (c := pycountry.countries.get(alpha_2=x.upper()))
    and f"{x} ({c.name})"
    or x,
)

# ── Apply filters ─────────────────────────────────────────────────────────────
df_filtered = apply_filters(
    df,
    keyword_list,
    min_budget,
    max_bids,
    min_score,
    filter_languages,
    filter_locations if filter_locations else None,
    max_hours_posted=float(max_hrs),
    verified_only=verified_only,
    featured_only=featured_only,
    urgent_only=urgent_only,
    min_skill_count=skill_min,
    max_skill_count=skill_max,
    min_bid_count=min_bid,
)
df_filtered = df_filtered.sort_values("score", ascending=False)

if df_filtered.empty:
    st.warning("No projects match the current filters.")
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# 📊  TABLE
# ═════════════════════════════════════════════════════════════════════════════
st.subheader(f"📊 Project Opportunities ({len(df_filtered)} results)")

display_cols = [
    "title",
    "budget_min_usd",
    "budget_max_usd",
    "currency_code",
    "bid_count",
    "client_verified",
    "client_reputation",
    "time_since_posted_hrs",
    "skill_count",
    "flag_urgent",
    "flag_featured",
    "score",
    "decision",
    "submitdate",
]
display_cols = [c for c in display_cols if c in df_filtered.columns]
table_df = df_filtered[display_cols].rename(
    columns={
        "budget_min_usd": "min_usd",
        "budget_max_usd": "max_usd",
        "time_since_posted_hrs": "hrs_ago",
        "client_reputation": "reputation",
    }
)
table_selection = st.dataframe(
    table_df,
    width="stretch",
    height=400,
    key="project_table",
    on_select="rerun",
    selection_mode="single-row",
)

selected_project_key = "selected_project_index"
if selected_project_key not in st.session_state or st.session_state[selected_project_key] not in df_filtered.index:
    st.session_state[selected_project_key] = df_filtered.index[0]

selected_rows = getattr(getattr(table_selection, "selection", None), "rows", [])
if selected_rows:
    selected_row = selected_rows[0]
    if 0 <= selected_row < len(df_filtered):
        st.session_state[selected_project_key] = df_filtered.iloc[selected_row].name

# ═════════════════════════════════════════════════════════════════════════════
# 📌  PROJECT DETAIL
# ═════════════════════════════════════════════════════════════════════════════
selected_index = st.selectbox(
    "Select Project",
    df_filtered.index,
    key=selected_project_key,
    format_func=lambda x: f"{df_filtered.loc[x, 'score']:.0f} | {df_filtered.loc[x, 'title']}",
)

row = df_filtered.loc[selected_index]
sign = (
    row["currency"].get("sign", "$") if isinstance(row.get("currency"), dict) else "$"
)
code = (
    row["currency"].get("code", "NA") if isinstance(row.get("currency"), dict) else "NA"
)

st.markdown("## 📌 Project Details")
url = f"https://www.freelancer.com/projects/{row.get('seo_url', '')}"
st.markdown(f"##### [{row['title']}]({url})")

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Budget (local)",
    f"{sign}{row['budget_min']:.0f}–{sign}{row['budget_max']:.0f} {code}",
)
c2.metric("Budget (USD)", f"${row.get('avg_budget_usd', 0):.0f}")
c3.metric("Bids", int(row["bid_count"]))
c4.metric("Score", f"{row['score']} ({row['decision']})")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Client Verified", "✅" if row["client_verified"] else "❌")
c6.metric("Reputation", f"{row.get('client_reputation', 0):.1f}/5")
c7.metric("Posted", f"{row.get('time_since_posted_hrs', 0):.1f}h ago")
c8.metric("Skills", int(row.get("skill_count", 0)))

flags = []
if row.get("flag_urgent"):
    flags.append("🔥 Urgent")
if row.get("flag_featured"):
    flags.append("⭐ Featured")
if row.get("flag_nda"):
    flags.append("🔒 NDA")
if row.get("flag_premium"):
    flags.append("💎 Premium")
if flags:
    st.markdown(" ".join(flags))

st.write(f"**Skills:** {', '.join(row['skills_list'])}")
st.write(f"**Client Country:** {row.get('client_country_code', 'NA').upper()}")
st.write(f"**Account Age:** {row.get('client_account_age_days', 0):.0f} days")

# ── Score breakdown ───────────────────────────────────────────────────────────
with st.expander("📐 Score Breakdown"):
    components = get_component_scores(row, keyword_list)
    comp_df = pd.DataFrame(
        [
            {
                "Factor": k.title(),
                "Raw Score": v,
                "Weight": weights.get(k, DEFAULT_WEIGHTS[k]),
                "Enabled": enabled.get(k, True),
            }
            for k, v in components.items()
        ]
    )
    st.dataframe(comp_df, width="stretch")

# ── Description ───────────────────────────────────────────────────────────────
st.markdown("### 🧾 Description")
st.write(row["description"])

# ── AI Insights ───────────────────────────────────────────────────────────────
st.markdown("### 🧠 AI Insights")
good, risks = generate_insights(row)

icol1, icol2 = st.columns(2)
with icol1:
    st.markdown("**✅ Why this is good**")
    if good:
        for g in good:
            st.success(g)
    else:
        st.info("No strong positives detected")

with icol2:
    st.markdown("**⚠️ Risk Factors**")
    if risks:
        for r_ in risks:
            st.warning(r_)
    else:
        st.success("No significant risks detected")

# ── Export ────────────────────────────────────────────────────────────────────
if st.button("📤 Export Top 15"):
    df_filtered.head(15).to_csv("shortlist.csv", index=False)
    st.success("Exported shortlist.csv")
