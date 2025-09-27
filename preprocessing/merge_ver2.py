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
        return pd.DataFrame(columns=["TRAVEL_ID", "activity_history_rows", "ACTIVITY_TYPE_CD"])

    # Count total activities per trip
    activity_counts = df.groupby("TRAVEL_ID").size().rename("activity_history_rows")
    
    # Get mode of activity type
    activity_type_mode = df.groupby('TRAVEL_ID')['ACTIVITY_TYPE_CD'].agg(lambda x: x.mode()[0] if not x.mode().empty else np.nan).rename('ACTIVITY_TYPE_CD')

    summary_df = pd.concat([activity_counts, activity_type_mode], axis=1)
    
    return summary_df.reset_index()



def prepare_visit_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["TRAVEL_ID", "MOVE_CNT", "TRIP_DAYS", "DGSTFN_AVG", "REVISIT_AVG", "RCMDTN_AVG"])

    columns_to_keep = ["TRAVEL_ID", "MOVE_CNT", "TRIP_DAYS", "DGSTFN_AVG", "REVISIT_AVG", "RCMDTN_AVG"]
    existing = [column for column in columns_to_keep if column in df.columns]
    result = df[existing].copy()
    if "MOVE_CNT" not in result.columns:
        result["MOVE_CNT"] = 0
    if "TRIP_DAYS" not in result.columns:
        result["TRIP_DAYS"] = 0
    return result

def build_final_dataset(mode="train"):
    # Load necessary files
    activity_consumption = read_preprocessed_csv_for_all_years("activity_consumption.csv", mode=mode)
    visit_summary = read_preprocessed_csv_for_all_years("visit_area_summary.csv", mode=mode)
    activity_history = read_preprocessed_csv_for_all_years("activity_history.csv", mode=mode)
    travel_table = read_preprocessed_csv_for_all_years("travel.csv", mode=mode)
    traveller_master = read_preprocessed_csv_for_all_years("traveller_master.csv", mode=mode)

    # Aggregate data
    activity_consume_summary = aggregate_activity_consumption(activity_consumption)
    visit_summary_ready = prepare_visit_summary(visit_summary)
    activity_history_summary = aggregate_activity_history(activity_history)

    # Merge traveller_master to get persona and other traveler features
    traveller_master = traveller_master.drop_duplicates(subset=["TRAVELER_ID"])
    final_df = travel_table.merge(traveller_master, on="TRAVELER_ID", how="left")

    # Merge other summaries
    final_df = final_df.merge(visit_summary_ready, on="TRAVEL_ID", how="left")
    final_df = final_df.merge(activity_consume_summary, on="TRAVEL_ID", how="left")
    final_df = final_df.merge(activity_history_summary, on="TRAVEL_ID", how="left")

    # Fill nulls based on data type
    for col in final_df.columns:
        if col == 'TRAVEL_ID':
            continue
        if final_df[col].isnull().any():
            if pd.api.types.is_object_dtype(final_df[col]):
                final_df[col] = final_df[col].fillna("정보없음")
            elif pd.api.types.is_numeric_dtype(final_df[col]):
                median_val = final_df[col].median()
                final_df[col] = final_df[col].fillna(median_val)

    # --- Calculate SUCCESS_SCORE ---
    if all(c in final_df.columns for c in ['DGSTFN_AVG', 'REVISIT_AVG', 'RCMDTN_AVG']):
        avg_satisfaction = (final_df['DGSTFN_AVG'] + final_df['REVISIT_AVG'] + final_df['RCMDTN_AVG']) / 3
        score_A = ((avg_satisfaction - 1) / 4 * 40).clip(0, 40)
    else:
        score_A = 0

    unique_activities = activity_history.groupby('TRAVEL_ID')['ACTIVITY_TYPE_CD'].nunique().rename('unique_activity_count')
    final_df = final_df.merge(unique_activities, on='TRAVEL_ID', how='left')
    final_df['unique_activity_count'] = final_df['unique_activity_count'].fillna(0)
    score_D = final_df['unique_activity_count'].clip(upper=5) * 2
    
    final_df['SUCCESS_SCORE'] = score_A + score_D
    # --- End of SUCCESS_SCORE calculation ---

    if 'activity_payment_sum' in final_df.columns:
        q1 = final_df['activity_payment_sum'].quantile(0.25)
        q3 = final_df['activity_payment_sum'].quantile(0.75)
        def classify_payment(payment):
            if payment <= q1: return 'low'
            elif payment >= q3: return 'high'
            else: return 'med'
        final_df['payment_persona'] = final_df['activity_payment_sum'].apply(classify_payment)

    final_columns = [
        "TRAVEL_ID", "SUCCESS_SCORE", "TRIP_DAYS", "MOVE_CNT", 
        "activity_payment_sum", "activity_history_rows", "ACTIVITY_TYPE_CD",
        "payment_persona", "TRAVEL_PERSONA_PURPOSE",
        # Add new traveler features
        "GENDER", "AGE_GRP", "HOUSE_INCOME", "TRAVEL_MOTIVE_1",
        "TRAVEL_STATUS_ACCOMPANY", "TRAVEL_COMPANIONS_NUM", "RESIDENCE_SGG_CD",
    ] + [f"TRAVEL_STYLE_{i}" for i in range(1, 9)]
    
    existing_final_columns = [column for column in final_columns if column in final_df.columns]
    final_df = final_df[existing_final_columns].copy()

    int_columns = ["TRIP_DAYS", "MOVE_CNT", "activity_payment_sum", "activity_history_rows", "GENDER", "AGE_GRP", "HOUSE_INCOME", "TRAVEL_MOTIVE_1"] + [f"TRAVEL_STYLE_{i}" for i in range(1, 9)]
    for column in int_columns:
        if column in final_df.columns:
            final_df[column] = final_df[column].astype(int)

    per_day_mappings = {
        "move_cnt_per_day": "MOVE_CNT",
        "activity_payment_sum_per_day": "activity_payment_sum",
        "activity_history_rows_per_day": "activity_history_rows",
    }

    if "TRIP_DAYS" in final_df.columns:
        length_series = final_df["TRIP_DAYS"].replace(0, pd.NA).astype(float)
        for new_column, source_column in per_day_mappings.items():
            if source_column in final_df.columns:
                per_day_values = final_df[source_column] / length_series
                final_df[new_column] = per_day_values.fillna(0)
    else:
        for new_column in per_day_mappings:
            final_df[new_column] = 0

    per_day_columns = list(per_day_mappings.keys())
    
    all_final_columns = existing_final_columns + per_day_columns
    final_df = final_df[[col for col in all_final_columns if col in final_df.columns]]

    return final_df

def save_final_dataset(mode="train", output_dir=None):
    df = build_final_dataset(mode=mode)
    
    # Print distribution of SUCCESS_SCORE for analysis
    if 'SUCCESS_SCORE' in df.columns:
        print("--- SUCCESS_SCORE Distribution ---")
        print(df['SUCCESS_SCORE'].describe())
        print("\n")

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
