from utils import convert_to_currency


def apply_filters(
    df,
    keyword_filter: list[str],
    min_budget: float,
    max_bids: int,
    min_score: float,
    languages: list[str],
    locations: list[str] | None = None,
    max_hours_posted: float | None = None,
    verified_only: bool = False,
    featured_only: bool = False,
    urgent_only: bool = False,
    min_skill_count: int = 0,
    max_skill_count: int = 999,
    min_bid_count: int = 0,
    client_countries: list[str] | None = None,
):
    if keyword_filter:
        df = df[
            df["skills_list"].apply(
                lambda skills: any(
                    kw.lower() in [s.lower() for s in skills]
                    for kw in keyword_filter
                )
            )
        ]

    if "currency_code" in df.columns:
        codes = df["currency_code"].unique()
        min_budget_map = {c: convert_to_currency(min_budget, c) for c in codes}
        df = df[
            df.apply(lambda r: r["budget_max"] >= min_budget_map[r["currency_code"]], axis=1)
        ]
    else:
        df = df[df["budget_max"] >= min_budget]

    df = df[df["bid_count"].between(min_bid_count, max_bids)]
    df = df[df["score"] >= min_score]

    if languages:
        df = df[df["language"].isin(languages)]

    if locations:
        df = df[df["location_code"].isin(locations)]

    if client_countries:
        df = df[df["client_country_code"].isin(client_countries)]

    if max_hours_posted is not None:
        df = df[df["time_since_posted_hrs"] <= max_hours_posted]

    if verified_only:
        df = df[df["client_verified"] == True]

    if featured_only:
        df = df[df["flag_featured"] == True]

    if urgent_only:
        df = df[df["flag_urgent"] == True]

    df = df[df["skill_count"].between(min_skill_count, max_skill_count)]

    return df
