import os
import pandas as pd
import json
from collections import Counter

# Define the years to be processed
AVAILABLE_YEARS = ["2022", "2023"]

def get_project_root():
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))

def get_preprocessed_dir(mode="train", year=None):
    root = get_project_root()
    if year:
        return os.path.join(root, "data", mode, year, "preprocessing")
    # Fallback for final directory or non-year-specific paths
    return os.path.join(root, "data", mode, "preprocessing")

def get_final_dir(mode="train"):
    root = get_project_root()
    return os.path.join(root, "data", mode, "final")

def read_preprocessed_csv_for_all_years(filename, mode="train"):
    """Read and concatenate a given preprocessed CSV from all available years."""
    all_dfs = []
    for year in AVAILABLE_YEARS:
        folder = get_preprocessed_dir(mode=mode, year=year)
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            all_dfs.append(df)
        else:
            print(f"Warning: Preprocessed file not found for year {year} at {path}. Skipping.")
    
    if not all_dfs:
        raise FileNotFoundError(f"No preprocessed file named '{filename}' found for any year in mode '{mode}'.")
    
    return pd.concat(all_dfs, ignore_index=True)

def aggregate_activity_consumption(df):
    columns = ["TRAVEL_ID", "activity_payment_sum", "activity_payment_count", "activity_store_count"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df = df.copy()
    df["PAYMENT_AMT_WON"] = pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)
    total = df.groupby("TRAVEL_ID")["PAYMENT_AMT_WON"].sum().rename("activity_payment_sum")
    count = df.groupby("TRAVEL_ID").size().rename("activity_payment_count")
    stores = df.groupby("TRAVEL_ID")["STORE_NM"].nunique().rename("activity_store_count")
    merged = pd.concat([total, count, stores], axis=1).reset_index()
    for column in columns[1:]:
        if column in merged.columns:
            merged[column] = merged[column].fillna(0)
    if "activity_payment_sum" in merged.columns:
        merged["activity_payment_sum"] = merged["activity_payment_sum"].round().astype(int)
    return merged

def aggregate_activity_history(df):
    if df.empty:
        return pd.DataFrame(columns=["TRAVEL_ID", "activity_history_rows", "activity_type_unique"])
    counts = df.groupby("TRAVEL_ID").size().rename("activity_history_rows")
    unique_types = df.groupby("TRAVEL_ID")["ACTIVITY_TYPE_CD"].nunique().rename("activity_type_unique")
    return pd.concat([counts, unique_types], axis=1).reset_index()

def aggregate_lodging(df):
    columns = ["TRAVEL_ID", "lodging_payment_sum", "lodging_payment_count", "lodging_store_count"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    df = df.copy()
    df["PAYMENT_AMT_WON"] = pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)
    total = df.groupby("TRAVEL_ID")["PAYMENT_AMT_WON"].sum().rename("lodging_payment_sum")
    count = df.groupby("TRAVEL_ID").size().rename("lodging_payment_count")
    stores = df.groupby("TRAVEL_ID")["STORE_NM"].nunique().rename("lodging_store_count")
    merged = pd.concat([total, count, stores], axis=1).reset_index()
    for column in columns[1:]:
        if column in merged.columns:
            merged[column] = merged[column].fillna(0)
    if "lodging_payment_sum" in merged.columns:
        merged["lodging_payment_sum"] = merged["lodging_payment_sum"].round().astype(int)
    return merged

def prepare_visit_summary(df):
    if df.empty:
        columns = [
            "TRAVEL_ID", "visit_dgstfn_avg", "visit_revisit_avg", "visit_rcmdtn_avg",
            "visit_trip_days", "visit_move_cnt", "visit_rate",
        ]
        return pd.DataFrame(columns=columns)
    rename_map = {
        "DGSTFN_AVG": "visit_dgstfn_avg", "REVISIT_AVG": "visit_revisit_avg",
        "RCMDTN_AVG": "visit_rcmdtn_avg", "TRIP_DAYS": "visit_trip_days",
        "MOVE_CNT": "visit_move_cnt", "VISIT_RATE": "visit_rate",
    }
    return df.rename(columns=rename_map)

def _extract_codes(value, delimiter=";"):
    if pd.isna(value):
        return []
    codes = []
    for part in str(value).split(delimiter):
        code = part.strip()
        if code:
            codes.append(code)
    return codes

def expand_multi_value_column(df, column, prefix, delimiter=";", top_n=10):
    if column not in df.columns:
        return df
    code_lists = df[column].apply(lambda x: _extract_codes(x, delimiter))
    counter = Counter()
    for codes in code_lists:
        counter.update(codes)
    top_codes = [code for code, _ in counter.most_common(top_n)]
    for code in top_codes:
        col_name = f"{prefix}{code}"
        df[col_name] = code_lists.apply(lambda codes: int(code in codes))
    df[f"{prefix}OTHER"] = code_lists.apply(
        lambda codes: int(any(code not in top_codes for code in codes)) if codes else 0
    )
    df[f"{prefix}COUNT"] = code_lists.apply(len)
    return df

def expand_travel_categorical_codes(travel_df):
    travel_df = expand_multi_value_column(travel_df, "TRAVEL_PURPOSE", "TRAVEL_PURPOSE_", ";")
    travel_df["TRAVEL_PURPOSE_COUNT"] = travel_df.get("TRAVEL_PURPOSE_COUNT", 0)
    travel_df["TRAVEL_PURPOSE_OTHER"] = travel_df.get("TRAVEL_PURPOSE_OTHER", 0)
    return travel_df

def _load_mis_codes(json_path):
    """Load all numeric MIS codes (cd_b) from the given tag-code JSON.

    Returns a list of strings sorted by numeric value, e.g., ["1", "2", ..., "26"].
    Skips codes where cd_b is non-numeric or where del_flag indicates deletion.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    codes = []
    for item in data:
        if item.get("cd_a") != "MIS":
            continue
        if str(item.get("del_flag", "N")).upper() == "Y":
            continue
        cd_b = str(item.get("cd_b", "")).strip()
        if cd_b.isdigit():
            codes.append(cd_b)

    # sort numerically but keep as strings for consistent column names
    codes = sorted(set(codes), key=lambda x: int(x))
    return codes

def _encode_mis_multi_hot(series: pd.Series, codes):
    """Given a Series of semicolon-separated code strings, return a DataFrame of 0/1 per code.

    - series: e.g., TRAVEL_PURPOSE or TRAVEL_MISSION_CHECK
    - codes: list of string codes (e.g. ["1", "2", ...])
    """
    code_lists = series.apply(lambda x: set(_extract_codes(x, ";")) if not pd.isna(x) else set())
    data = {}
    for code in codes:
        data[code] = code_lists.apply(lambda s: int(code in s))
    return pd.DataFrame(data)

def apply_mis_one_hot(final_df: pd.DataFrame) -> pd.DataFrame:
    """Drop existing TRAVEL_PURPOSE_* encodings and append MIS-based one-hot columns for
    TRAVEL_PURPOSE and TRAVEL_MISSION_CHECK to the rightmost side of the DataFrame.
    """
    df = final_df.copy()

    # Prepare MIS codes from the tag-code JSON
    json_path = os.path.join(
        get_project_root(),
        "data",
        "tag_code",
        "training",
        "json",
        "tc_codeb_코드B.json",
    )
    mis_codes = _load_mis_codes(json_path)

    # 1) Drop previously encoded TRAVEL_PURPOSE_* columns (but keep the raw TRAVEL_PURPOSE)
    to_drop = [
        c
        for c in df.columns
        if c.startswith("TRAVEL_PURPOSE_") and c != "TRAVEL_PURPOSE"
    ]
    if to_drop:
        df = df.drop(columns=to_drop)

    # 2) Build and append new one-hot columns using MIS codes
    if "TRAVEL_PURPOSE" in df.columns:
        purpose_oh = _encode_mis_multi_hot(df["TRAVEL_PURPOSE"], mis_codes)
        purpose_oh.columns = [f"TRAVEL_PURPOSE_CD_{c}" for c in mis_codes]
    else:
        purpose_oh = pd.DataFrame(index=df.index)

    if "TRAVEL_MISSION_CHECK" in df.columns:
        mission_oh = _encode_mis_multi_hot(df["TRAVEL_MISSION_CHECK"], mis_codes)
        mission_oh.columns = [f"TRAVEL_MISSION_CHECK_CD_{c}" for c in mis_codes]
    else:
        mission_oh = pd.DataFrame(index=df.index)

    # Ensure integer dtype (0/1)
    for sub in (purpose_oh, mission_oh):
        for col in sub.columns:
            sub[col] = sub[col].astype(int)

    # Concatenate to the right (appended columns appear at end)
    df = pd.concat([df, purpose_oh, mission_oh], axis=1)
    return df

def build_final_dataset(mode="train"):
    # Load and concatenate data from all years
    activity_consumption = read_preprocessed_csv_for_all_years("activity_consumption.csv", mode=mode)
    activity_history = read_preprocessed_csv_for_all_years("activity_history.csv", mode=mode)
    lodging = read_preprocessed_csv_for_all_years("lodging_consumption.csv", mode=mode)
    traveller_master = read_preprocessed_csv_for_all_years("traveller_master.csv", mode=mode)
    visit_summary = read_preprocessed_csv_for_all_years("visit_area_summary.csv", mode=mode)
    travel_table = read_preprocessed_csv_for_all_years("travel.csv", mode=mode)

    # Aggregate data
    activity_consume_summary = aggregate_activity_consumption(activity_consumption)
    activity_history_summary = aggregate_activity_history(activity_history)
    lodging_summary = aggregate_lodging(lodging)
    visit_summary_ready = prepare_visit_summary(visit_summary)

    # Merge features (skip PURPOSE one-hot expansion per request)
    travel_features = travel_table.copy()
    travel_features = travel_features.merge(activity_consume_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(activity_history_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(lodging_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(visit_summary_ready, on="TRAVEL_ID", how="left")

    # Fill missing values
    if "activity_payment_sum" in travel_features.columns:
        activity_median = travel_features["activity_payment_sum"].median()
        travel_features["activity_payment_sum"] = travel_features["activity_payment_sum"].fillna(activity_median)
    if "lodging_payment_sum" in travel_features.columns:
        lodging_median = travel_features["lodging_payment_sum"].median()
        travel_features["lodging_payment_sum"] = travel_features["lodging_payment_sum"].fillna(lodging_median)
    
    numeric_fill_zero = [
        "activity_payment_count", "activity_store_count", "activity_history_rows",
        "activity_type_unique", "lodging_payment_count", "lodging_store_count",
    ]
    for column in numeric_fill_zero:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].fillna(0)

    # Final type casting
    count_columns = [
        "activity_payment_count", "activity_store_count", "activity_history_rows",
        "activity_type_unique", "lodging_payment_count", "lodging_store_count",
    ]
    for column in count_columns:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].astype(int)
    sum_columns = ["activity_payment_sum", "lodging_payment_sum"]
    for column in sum_columns:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].round().astype(int)

    # Final merge with traveller master
    final_df = travel_features.merge(traveller_master, on="TRAVELER_ID", how="left")

    # ---------------------------------------------------------------------
    # Complex feature engineering (from complex_features.md)
    # 1) activity_per_day = activity_payment_count / visit_trip_days
    # 2) spending_per_day = (activity_payment_sum + lodging_payment_sum) / visit_trip_days
    # 3) activity_to_lodging_ratio = activity_payment_sum / (lodging_payment_sum + 1)
    # 4) companions_per_family = TRAVEL_COMPANIONS_NUM / FAMILY_MEMB
    # Safe guards against division-by-zero/NaN
    # ---------------------------------------------------------------------
    def _safe_div(numer, denom):
        denom_safe = denom.copy()
        # Replace non-positive or NaN denominators with 1 to avoid div-by-zero
        denom_safe = denom_safe.fillna(0)
        denom_safe = denom_safe.where(denom_safe > 0, other=1)
        return numer.fillna(0) / denom_safe

    if "activity_payment_count" in final_df.columns and "visit_trip_days" in final_df.columns:
        final_df["activity_per_day"] = _safe_div(
            final_df["activity_payment_count"].astype(float),
            final_df["visit_trip_days"].astype(float),
        )

    if (
        "activity_payment_sum" in final_df.columns
        and "lodging_payment_sum" in final_df.columns
        and "visit_trip_days" in final_df.columns
    ):
        total_spend = final_df["activity_payment_sum"].astype(float).fillna(0) + \
                      final_df["lodging_payment_sum"].astype(float).fillna(0)
        final_df["spending_per_day"] = _safe_div(
            total_spend,
            final_df["visit_trip_days"].astype(float),
        )

    if "activity_payment_sum" in final_df.columns and "lodging_payment_sum" in final_df.columns:
        final_df["activity_to_lodging_ratio"] = final_df["activity_payment_sum"].astype(float).fillna(0) / (
            final_df["lodging_payment_sum"].astype(float).fillna(0) + 1.0
        )

    if "TRAVEL_COMPANIONS_NUM" in final_df.columns and "FAMILY_MEMB" in final_df.columns:
        final_df["companions_per_family"] = _safe_div(
            final_df["TRAVEL_COMPANIONS_NUM"].astype(float),
            final_df["FAMILY_MEMB"].astype(float),
        )

    # Drop identifier after feature engineering
    if "TRAVELER_ID" in final_df.columns:
        final_df = final_df.drop(columns=["TRAVELER_ID"])

    # Drop unnecessary SGG columns
    sgg_cols_to_drop = ["TRAVEL_LIKE_SGG_1", "TRAVEL_LIKE_SGG_2", "TRAVEL_LIKE_SGG_3"]
    final_df = final_df.drop(columns=sgg_cols_to_drop, errors="ignore")

    # Drop specific visit satisfaction-related columns per request
    cols_to_drop = [
        "visit_dgstfn_avg",
        "visit_revisit_avg",
        "visit_rcmdtn_avg",
    ]
    final_df = final_df.drop(columns=cols_to_drop, errors="ignore")

    # remove null
    final_df = final_df.dropna()

    # Skip MIS-based one-hot encoding for PURPOSE and MISSION CHECK (removed by request)

    return final_df

def save_final_dataset(mode="train", output_dir=None):
    df = build_final_dataset(mode=mode)
    if output_dir is None:
        output_dir = get_final_dir(mode=mode)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "travel_insight.csv")
    df.to_csv(output_path, index=False)
    return output_path

if __name__ == "__main__":
    path = save_final_dataset(mode="train")
    print(f"Saved merged training dataset to {path}")
