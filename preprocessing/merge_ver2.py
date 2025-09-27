import os
import pandas as pd
from sklearn.preprocessing import StandardScaler

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
    columns = ["TRAVEL_ID", "activity_payment_sum"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df = df.copy()
    if "PAYMENT_AMT_WON" in df.columns:
        df["PAYMENT_AMT_WON"] = pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)
    else:
        df["PAYMENT_AMT_WON"] = 0
    total = df.groupby("TRAVEL_ID")["PAYMENT_AMT_WON"].sum().rename("activity_payment_sum")
    result = total.reset_index()
    result["activity_payment_sum"] = result["activity_payment_sum"].fillna(0).round().astype(int)
    return result

def aggregate_activity_history(df):
    if df.empty:
        return pd.DataFrame(columns=["TRAVEL_ID", "activity_history_rows", "activity_type_unique"])
    counts = df.groupby("TRAVEL_ID").size().rename("activity_history_rows")
    unique_types = df.groupby("TRAVEL_ID")["ACTIVITY_TYPE_CD"].nunique().rename("activity_type_unique")
    return pd.concat([counts, unique_types], axis=1).reset_index()

def aggregate_lodging(df):
    columns = ["TRAVEL_ID", "lodging_payment_sum"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    df = df.copy()
    if "PAYMENT_AMT_WON" in df.columns:
        df["PAYMENT_AMT_WON"] = pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)
    else:
        df["PAYMENT_AMT_WON"] = 0
    total = df.groupby("TRAVEL_ID")["PAYMENT_AMT_WON"].sum().rename("lodging_payment_sum")
    result = total.reset_index()
    result["lodging_payment_sum"] = result["lodging_payment_sum"].fillna(0).round().astype(int)
    return result

def prepare_visit_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["TRAVEL_ID", "visit_move_cnt", "IS_FAILED_TRIP"])

    columns_to_keep = ["TRAVEL_ID", "MOVE_CNT", "IS_FAILED_TRIP"]
    existing = [column for column in columns_to_keep if column in df.columns]
    result = df[existing].copy()
    if "MOVE_CNT" in result.columns:
        result = result.rename(columns={"MOVE_CNT": "visit_move_cnt"})
    if "visit_move_cnt" not in result.columns:
        result["visit_move_cnt"] = 0
    return result

def build_final_dataset(mode="train"):
    activity_consumption = read_preprocessed_csv_for_all_years("activity_consumption.csv", mode=mode)
    lodging = read_preprocessed_csv_for_all_years("lodging_consumption.csv", mode=mode)
    visit_summary = read_preprocessed_csv_for_all_years("visit_area_summary.csv", mode=mode)
    travel_table = read_preprocessed_csv_for_all_years("travel.csv", mode=mode)

    activity_consume_summary = aggregate_activity_consumption(activity_consumption)
    lodging_summary = aggregate_lodging(lodging)
    visit_summary_ready = prepare_visit_summary(visit_summary)

    travel_features = travel_table.copy()
    travel_features = travel_features.merge(activity_consume_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(lodging_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(visit_summary_ready, on="TRAVEL_ID", how="left")

    feature_defaults = {
        "TRAVEL_LENGTH": 0,
        "activity_payment_sum": 0,
        "lodging_payment_sum": 0,
        "visit_move_cnt": 0,
    }
    for column, default in feature_defaults.items():
        if column in travel_features.columns:
            travel_features[column] = pd.to_numeric(travel_features[column], errors="coerce").fillna(default)

    travel_features["total_payment"] = travel_features["activity_payment_sum"] + travel_features["lodging_payment_sum"]

    if "IS_FAILED_TRIP" in travel_features.columns:
        travel_features["IS_FAILED_TRIP"] = pd.to_numeric(
            travel_features["IS_FAILED_TRIP"], errors="coerce"
        )

    final_columns = [
        "TRAVEL_ID",
        "TRAVEL_LENGTH",
        "total_payment",
        "visit_move_cnt",
        "IS_FAILED_TRIP",
    ]
    existing_final_columns = [column for column in final_columns if column in travel_features.columns]
    final_df = travel_features[existing_final_columns].copy()

    missing_required_columns = [column for column in final_columns if column not in final_df.columns]
    if missing_required_columns:
        raise ValueError(
            "Missing required columns in final dataset: " + ", ".join(missing_required_columns)
        )

    if "IS_FAILED_TRIP" in final_df.columns:
        final_df = final_df.dropna(subset=["IS_FAILED_TRIP"])
        final_df["IS_FAILED_TRIP"] = final_df["IS_FAILED_TRIP"].astype(int)

    for column in ["TRAVEL_LENGTH", "total_payment", "visit_move_cnt"]:
        if column in final_df.columns:
            final_df[column] = final_df[column].astype(int)

    # Derive per-day metrics while protecting against zero-length trips.
    per_day_mappings = {
        "total_payment_per_day": "total_payment",
        "visit_move_cnt_per_day": "visit_move_cnt",
    }
    if "TRAVEL_LENGTH" in final_df.columns:
        length_series = final_df["TRAVEL_LENGTH"].replace(0, pd.NA).astype(float)
        for new_column, source_column in per_day_mappings.items():
            if source_column in final_df.columns:
                per_day_values = final_df[source_column] / length_series
                final_df[new_column] = per_day_values.fillna(0)
    else:
        for new_column in per_day_mappings:
            final_df[new_column] = 0

    # Scale the payment columns
    scaler = StandardScaler()
    if "total_payment" in final_df.columns:
        final_df["total_payment"] = scaler.fit_transform(final_df[["total_payment"]])
    
    if "total_payment_per_day" in final_df.columns:
        scaler_per_day = StandardScaler()
        final_df["total_payment_per_day"] = scaler_per_day.fit_transform(final_df[["total_payment_per_day"]])

    per_day_columns = list(per_day_mappings.keys())
    final_df = final_df[existing_final_columns + per_day_columns]

    return final_df

def save_final_dataset(mode="train", output_dir=None):
    df = build_final_dataset(mode=mode)
    if output_dir is None:
        output_dir = get_final_dir(mode=mode)
    os.makedirs(output_dir, exist_ok=True)
    # output_path = os.path.join(output_dir, "travel_insight.csv")
    output_path = os.path.join(output_dir, "travel_insight_pruned.csv")
    df.to_csv(output_path, index=False)
    return output_path

if __name__ == "__main__":
    path = save_final_dataset(mode="train")
    print(f"Saved merged training dataset to {path}")
