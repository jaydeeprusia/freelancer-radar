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

st.set_page_config(
    page_title="Freelancer Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stExpander"] { border: 1px solid #2e3347; border-radius: 8px; }
    .stButton > button { border-radius: 6px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📡 Freelancer Radar")
st.caption(
    "Find, score, and shortlist Freelancer.com projects before anyone else bids."
)
st.divider()

# ── Fetch UI ──────────────────────────────────────────────────────────────────
with st.expander(
    "🌐 Fetch Projects from Freelancer API", expanded="df" not in st.session_state
):
    auth_token = st.text_input(
        "Freelancer Auth Token",
        type="password",
        placeholder="Paste your freelancer-auth-v2 token",
    )
    st.warning(
        "⚠️ Never share this token — it gives full Freelancer account access.", icon="🔐"
    )

    query = st.text_input(
        "Search Query", "python", placeholder="e.g. python, scraping, trading bot"
    )

    col1, col2, col3 = st.columns(3)
    limit = col1.slider("Projects per page", 10, 50, 20, step=10)
    pages = col2.slider("Pages to fetch", 1, 20, 5)
    max_price = col3.slider("Max Budget (USD)", 0, 5000, 1000, step=100)

    fc1, fc2 = st.columns(2)
    COUNTRY_OPTIONS = {
        f"{c.name} ({c.alpha_2.lower()})": c.alpha_2.lower()
        for c in sorted(pycountry.countries, key=lambda x: x.name)
    }
    LANGUAGE_OPTIONS = {
        f"{l.name} ({l.alpha_2})": l.alpha_2
        for l in sorted(pycountry.languages, key=lambda x: x.name)
        if hasattr(l, "alpha_2")
    }

    selected_countries = fc1.multiselect(
        "Countries", options=list(COUNTRY_OPTIONS.keys()), default=[]
    )
    default_lang = [k for k in LANGUAGE_OPTIONS if LANGUAGE_OPTIONS[k] == "en"]
    selected_languages = fc2.multiselect(
        "Languages", options=list(LANGUAGE_OPTIONS.keys()), default=default_lang[:1]
    )

    bc1, bc2 = st.columns([1, 4])
    refresh_cache = bc2.checkbox("🔄 Refresh Cache")
    if bc1.button("🚀 Fetch Projects", width="stretch"):
        if not auth_token:
            st.error("Enter your auth token first.")
        else:
            with st.spinner("Fetching projects..."):
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
            st.success(f"✅ Fetched **{len(df)}** projects")

# ── Upload fallback ───────────────────────────────────────────────────────────
file = st.file_uploader("📁 Or upload a Freelancer API JSON file", type=["json"])
df = None

if "df" in st.session_state:
    df = st.session_state["df"]
elif file:
    df = load_data(file)

if df is None:
    st.info("👆 Fetch projects or upload a JSON file to get started.")
    st.stop()

assert isinstance(df, pd.DataFrame)
df = normalize_data(df)

# ═════════════════════════════════════════════════════════════════════════════
# ⚙️  SCORING CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════
with st.expander(
    "⚙️ Scoring Configuration", expanded="loaded_preset" in st.session_state
):
    st.caption(
        "Adjust factor weights and toggle them on/off. Weights are auto-normalised."
    )
    st.divider()

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

    for k in factor_labels:
        if f"w_{k}" not in st.session_state:
            st.session_state[f"w_{k}"] = DEFAULT_WEIGHTS[k]
        if f"e_{k}" not in st.session_state:
            st.session_state[f"e_{k}"] = True

    if loaded_preset:
        for k in factor_labels:
            if k in loaded_preset.get("weights", {}):
                st.session_state[f"w_{k}"] = float(loaded_preset["weights"][k])
            if k in loaded_preset.get("enabled", {}):
                st.session_state[f"e_{k}"] = bool(loaded_preset["enabled"][k])
        del st.session_state["loaded_preset"]

    weights, enabled = {}, {}
    for key, label in factor_labels.items():
        c1, c2, c3 = st.columns([2, 4, 1])
        c1.markdown(f"**{label}**")
        weights[key] = c2.slider(
            f"w_{key}",
            0.0,
            1.0,
            step=0.05,
            key=f"w_{key}",
            label_visibility="collapsed",
        )
        enabled[key] = c3.checkbox("on", key=f"e_{key}", label_visibility="collapsed")

    total_w = sum(v for k, v in weights.items() if enabled.get(k))
    st.caption(f"Active weight sum: `{total_w:.2f}` — auto-normalised during scoring")
    st.divider()

    pc1, pc2 = st.columns([2, 1])
    preset_name = pc1.text_input(
        "Preset name",
        "my_preset",
        label_visibility="collapsed",
        placeholder="Preset name",
    )

    preset_json = json.dumps({"weights": weights, "enabled": enabled}, indent=2)
    pc2.download_button(
        "💾 Save Preset",
        preset_json,
        f"{preset_name}.json",
        "application/json",
        width="stretch",
    )

    uploaded_preset = st.file_uploader(
        "📂 Load Preset (.json)", type=["json"], key="preset_upload"
    )
    if st.button("📂 Apply Preset", width="stretch") and uploaded_preset:
        st.session_state["loaded_preset"] = json.load(uploaded_preset)
        st.rerun()

# ── Scoring ───────────────────────────────────────────────────────────────────
st.sidebar.title("📡 Freelancer Radar")
st.sidebar.divider()
st.sidebar.header("🎯 Skill Keywords")

all_skills = sorted(
    {
        s.lower()
        for skills in df["skills_list"].dropna()
        for s in (skills if isinstance(skills, list) else [])
    }
)

if not all_skills:
    st.sidebar.info("No skills found in data. Try a broader query.")
    keyword_list = []
else:
    default_kw = [
        s for s in ["python", "api", "automation", "ai"] if s in all_skills
    ] or all_skills[:4]
    selected_kw = st.sidebar.multiselect(
        "Skills",
        options=all_skills,
        default=default_kw,
        help="Select skills to match against projects",
    )
    keyword_list = selected_kw

df["score"] = df.apply(
    lambda r: calculate_score(r, keyword_list, weights, enabled), axis=1
)
df["score"] = df["score"].round().astype(int)
df["decision"] = df["score"].apply(decision)

# ═════════════════════════════════════════════════════════════════════════════
# 🔍  SIDEBAR FILTERS
# ═════════════════════════════════════════════════════════════════════════════
st.sidebar.divider()
st.sidebar.header("🔍 Filters")

min_budget = st.sidebar.slider("Min Budget (USD)", 0, 5000, 0, step=50)
min_bid = st.sidebar.slider("Min Bids", 0, 100, 0)
max_bids = st.sidebar.slider("Max Bids", 0, 500, 50, step=5)
min_score = st.sidebar.slider("Min Score", 0, 100, 0)
max_hrs = st.sidebar.slider("Max Hours Since Posted", 1, 720, 720)

st.sidebar.divider()
verified_only = st.sidebar.checkbox("✅ Verified Clients Only")
featured_only = st.sidebar.checkbox("⭐ Featured Only")
urgent_only = st.sidebar.checkbox("🔥 Urgent Only")

st.sidebar.divider()
skill_min, skill_max = st.sidebar.slider("Skill Count Range", 0, 20, (0, 20))

lang_opts = df["language"].dropna().unique().tolist()
filter_languages = st.sidebar.multiselect(
    "Language",
    options=lang_opts,
    default=[x for x in ["en"] if x in lang_opts],
    format_func=lambda x: (lang := pycountry.languages.get(alpha_2=x))
    and f"{x} — {lang.name}"
    or x,
)

loc_opts = [c for c in df["location_code"].dropna().unique().tolist() if c != "NA"]
filter_locations = st.sidebar.multiselect(
    "Client Location",
    options=loc_opts,
    default=[x for x in ["in"] if x in loc_opts],
    format_func=lambda x: (c := pycountry.countries.get(alpha_2=x.upper()))
    and f"{x.upper()} — {c.name}"
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

# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tab_projects, tab_analytics = st.tabs(["📋 Projects", "📊 Analytics"])

with tab_projects:
    if df_filtered.empty:
        st.warning(
            "⚠️ No projects match the current filters. Try relaxing some constraints."
        )
    else:
        bid_col, consider_col, skip_col, total_col = st.columns(4)
        bid_col.metric("🟢 BID", len(df_filtered[df_filtered["decision"] == "BID"]))
        consider_col.metric(
            "🟡 CONSIDER", len(df_filtered[df_filtered["decision"] == "CONSIDER"])
        )
        skip_col.metric("🔴 SKIP", len(df_filtered[df_filtered["decision"] == "SKIP"]))
        total_col.metric("📋 Total", len(df_filtered))

        st.divider()
        st.subheader("📊 Project Opportunities")

        display_cols = [
            "title",
            "budget_min_usd",
            "budget_max_usd",
            "bid_count",
            "client_verified",
            "client_reputation",
            "time_since_posted_hrs",
            "skill_count",
            "score",
            "decision",
            "submitdate",
        ]
        display_cols = [c for c in display_cols if c in df_filtered.columns]

        view_df = (
            df_filtered[display_cols]
            .rename(
                columns={
                    "budget_min_usd": "min_usd",
                    "budget_max_usd": "max_usd",
                    "time_since_posted_hrs": "hrs_ago",
                    "client_reputation": "reputation",
                }
            )
            .copy()
        )
        table_event = st.dataframe(
            view_df,
            width="stretch",
            height=420,
            key="project_table",
            on_select="rerun",
            selection_mode="single-row",
        )

        selected_project_key = "selected_index"
        if (
            selected_project_key not in st.session_state
            or st.session_state[selected_project_key] not in df_filtered.index
        ):
            st.session_state[selected_project_key] = df_filtered.index[0]

        selected_rows = getattr(getattr(table_event, "selection", None), "rows", [])
        if selected_rows:
            row_pos = selected_rows[0]
            if 0 <= row_pos < len(df_filtered):
                st.session_state[selected_project_key] = df_filtered.index[row_pos]

        # ── Project detail ────────────────────────────────────────────────────
        st.divider()
        default_idx = st.session_state.get("selected_index", df_filtered.index[0])
        if default_idx not in df_filtered.index:
            default_idx = df_filtered.index[0]
            st.session_state["selected_index"] = default_idx

        selected_index = st.selectbox(
            "🔎 Select Project",
            df_filtered.index,
            key="selected_index",
            format_func=lambda x: f"{df_filtered.loc[x, 'score']}  |  {df_filtered.loc[x, 'title']}",
        )

        row = df_filtered.loc[selected_index]
        sign = (
            row["currency"].get("sign", "$")
            if isinstance(row.get("currency"), dict)
            else "$"
        )
        code = (
            row["currency"].get("code", "NA")
            if isinstance(row.get("currency"), dict)
            else "NA"
        )

        url = f"https://www.freelancer.com/projects/{row.get('seo_url', '')}"
        st.markdown(f"## [{row['title']}]({url})")

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
            st.markdown("  ".join(f"`{f}`" for f in flags))

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Min Budget", f"{sign}{row['budget_min']:.0f} {code}")
        m2.metric("Max Budget", f"{sign}{row['budget_max']:.0f} {code}")
        m3.metric("Avg (USD)", f"${row.get('avg_budget_usd', 0):.0f}")
        m4.metric("Bids", int(row["bid_count"]))

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Score", int(row["score"]))
        m6.metric("Decision", row["decision"])
        m7.metric("Posted", f"{row.get('time_since_posted_hrs', 0):.1f}h ago")
        m8.metric("Verified", "✅" if row["client_verified"] else "❌")

        st.divider()
        d1, d2 = st.columns(2)
        d1.markdown(
            f"**🌍 Client Country:** `{row.get('client_country_code', 'NA').upper()}`"
        )
        d1.markdown(f"**⭐ Reputation:** `{row.get('client_reputation', 0):.1f} / 5`")
        d1.markdown(
            f"**📅 Account Age:** `{row.get('client_account_age_days', 0):.0f} days`"
        )
        d2.markdown(f"**🛠 Skills:** {', '.join(f'`{s}`' for s in row['skills_list'])}")

        with st.expander("📐 Score Breakdown"):
            components = get_component_scores(row, keyword_list)
            comp_df = pd.DataFrame(
                [
                    {
                        "Factor": k.title(),
                        "Raw Score": v,
                        "Weight": f"{weights.get(k, DEFAULT_WEIGHTS[k]):.2f}",
                        "Enabled": "✅" if enabled.get(k, True) else "❌",
                    }
                    for k, v in components.items()
                ]
            )
            st.dataframe(comp_df, width="stretch", hide_index=True)

        with st.expander("🧾 Description", expanded=True):
            st.write(row["description"])

        st.divider()
        st.subheader("🧠 Insights")
        good, risks = generate_insights(row)
        icol1, icol2 = st.columns(2)
        with icol1:
            st.markdown("**✅ Why this is good**")
            for g in good:
                st.success(g)
            if not good:
                st.info("No strong positives detected.")
        with icol2:
            st.markdown("**⚠️ Risk Factors**")
            for r_ in risks:
                st.warning(r_)
            if not risks:
                st.success("No significant risks detected.")

        st.divider()
        csv_data = df_filtered.head(15).to_csv(index=False)
        st.download_button(
            "📤 Export Top 15 to CSV", csv_data, "shortlist.csv", "text/csv"
        )

with tab_analytics:
    if df_filtered.empty:
        st.info("No data to visualise. Adjust filters.")
    else:
        st.subheader("📊 Score Distribution")
        score_dist = (
            df_filtered["decision"]
            .value_counts()
            .reindex(["BID", "CONSIDER", "SKIP"], fill_value=0)
        )
        st.bar_chart(score_dist)

        st.divider()
        st.subheader("💰 Budget vs Competition")
        scatter_df = df_filtered[
            ["avg_budget_usd", "bid_count", "decision", "title"]
        ].copy()
        scatter_df = scatter_df.rename(
            columns={"avg_budget_usd": "Budget (USD)", "bid_count": "Bid Count"}
        )
        st.scatter_chart(scatter_df, x="Budget (USD)", y="Bid Count", color="decision")

        st.divider()
        st.subheader("🛠 Top Skills")
        from collections import Counter

        skill_counts = Counter(
            s
            for skills in df_filtered["skills_list"].dropna()
            for s in (skills if isinstance(skills, list) else [])
        )
        top_skills = pd.DataFrame(
            skill_counts.most_common(20), columns=["Skill", "Count"]
        ).set_index("Skill")
        st.bar_chart(top_skills)
