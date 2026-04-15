from utils import convert_to_currency


def apply_filters(df, keyword_filter, min_budget, max_bids, min_score, languages, locations=None):
    if keyword_filter:
        df = df[
            df["skills_list"].apply(
                lambda skills: any(
                    keyword.lower() in [s.lower() for s in skills]
                    for keyword in keyword_filter
                )
            )
        ]

    if "currency_code" in df.columns:
        currency_codes = df["currency_code"].unique()
        min_budget_dict = {
            code: convert_to_currency(min_budget, code) for code in currency_codes
        }
        df = df[
            df.apply(
                lambda row: row["budget_max"] >= min_budget_dict[row["currency_code"]],
                axis=1,
            )
        ]
    else:
        df = df[df["budget_max"] >= min_budget]

    df = df[df["bid_count"] <= max_bids]
    df = df[df["score"] >= min_score]

    if languages:
        df = df[df["language"].isin(languages)]

    if locations:
        df = df[df["location_code"].isin(locations)]

    return df
