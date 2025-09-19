import os

import pandas as pd

import json
from collections import Counter


def get_project_root():
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def get_preprocessed_dir():
    root = get_project_root()
    return os.path.join(root, "data", "training", "preprocessing")


def read_preprocessed_csv(filename):
    folder = get_preprocessed_dir()
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing preprocessed file: {path}")
    return pd.read_csv(path)


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
        merged["activity_payment_sum"] = (
            merged["activity_payment_sum"].round().astype(int)
        )
    return merged


def aggregate_activity_history(df):
    if df.empty:
        return pd.DataFrame(columns=["TRAVEL_ID", "activity_history_rows", "activity_type_unique"])

    counts = df.groupby("TRAVEL_ID").size().rename("activity_history_rows")
    unique_types = df.groupby("TRAVEL_ID")["ACTIVITY_TYPE_CD"].nunique().rename("activity_type_unique")

    merged = pd.concat([counts, unique_types], axis=1).reset_index()
    return merged


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
        merged["lodging_payment_sum"] = (
            merged["lodging_payment_sum"].round().astype(int)
        )
    return merged


def prepare_visit_summary(df):
    if df.empty:
        columns = [
            "TRAVEL_ID",
            "visit_dgstfn_avg",
            "visit_revisit_avg",
            "visit_rcmdtn_avg",
            "visit_trip_days",
            "visit_move_cnt",
            "visit_rate",
        ]
        return pd.DataFrame(columns=columns)

    rename_map = {
        "DGSTFN_AVG": "visit_dgstfn_avg",
        "REVISIT_AVG": "visit_revisit_avg",
        "RCMDTN_AVG": "visit_rcmdtn_avg",
        "TRIP_DAYS": "visit_trip_days",
        "MOVE_CNT": "visit_move_cnt",
        "VISIT_RATE": "visit_rate",
    }
    result = df.rename(columns=rename_map)
    return result


def load_file_map():
    here = os.path.dirname(__file__)
    json_path = os.path.join(here, "file_dir.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Cannot find mapping file: {json_path}")
    with open(json_path, encoding="utf-8") as handle:
        data = json.load(handle)
    file_map = {}
    root = get_project_root()
    for key, rel_path in data.items():
        file_map[key] = os.path.join(root, rel_path)
    return file_map


def load_travel_table():
    preprocessed_path = os.path.join(get_preprocessed_dir(), "travel.csv")
    if os.path.exists(preprocessed_path):
        return pd.read_csv(preprocessed_path)

    file_map = load_file_map()
    if "여행" not in file_map:
        raise KeyError("'여행' key is missing from file_dir.json")
    travel_path = file_map["여행"]
    return pd.read_csv(travel_path).drop(columns=["TRAVEL_MISSION"], errors="ignore")


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

    travel_df = expand_multi_value_column(
        travel_df,
        "TRAVEL_MISSION_CHECK",
        "TRAVEL_MISSION_CHECK_",
        ";",
        top_n=10,
    )

    travel_df["TRAVEL_PURPOSE_COUNT"] = travel_df.get("TRAVEL_PURPOSE_COUNT", 0)
    travel_df["TRAVEL_PURPOSE_OTHER"] = travel_df.get("TRAVEL_PURPOSE_OTHER", 0)

    return travel_df


def build_final_dataset():
    activity_consumption = read_preprocessed_csv("activity_consumption.csv")
    activity_history = read_preprocessed_csv("activity_history.csv")
    lodging = read_preprocessed_csv("lodging_consumption.csv")
    traveller_master = read_preprocessed_csv("traveller_master.csv")
    visit_summary = read_preprocessed_csv("visit_area_summary.csv")

    activity_consume_summary = aggregate_activity_consumption(activity_consumption)
    activity_history_summary = aggregate_activity_history(activity_history)
    lodging_summary = aggregate_lodging(lodging)
    visit_summary_ready = prepare_visit_summary(visit_summary)

    travel_table = load_travel_table()
    travel_table = expand_travel_categorical_codes(travel_table)

    travel_features = travel_table.copy()
    travel_features = travel_features.merge(activity_consume_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(activity_history_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(lodging_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(visit_summary_ready, on="TRAVEL_ID", how="left")

    numeric_fill_zero = [
        "activity_payment_sum",
        "activity_payment_count",
        "activity_store_count",
        "activity_history_rows",
        "activity_type_unique",
        "lodging_payment_sum",
        "lodging_payment_count",
        "lodging_store_count",
    ]

    for column in numeric_fill_zero:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].fillna(0)

    count_columns = [
        "activity_payment_count",
        "activity_store_count",
        "activity_history_rows",
        "activity_type_unique",
        "lodging_payment_count",
        "lodging_store_count",
    ]
    for column in count_columns:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].astype(int)

    sum_columns = [
        "activity_payment_sum",
        "lodging_payment_sum",
    ]
    for column in sum_columns:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].round().astype(int)

    final_df = travel_features.merge(traveller_master, on="TRAVELER_ID", how="left")
    return final_df


def save_final_dataset():
    df = build_final_dataset()
    output_dir = get_preprocessed_dir()
    output_path = os.path.join(output_dir, "final_traveler.csv")
    df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    path = save_final_dataset()
    print(f"Saved merged dataset to {path}")
