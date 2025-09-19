import io
import json
import os

import numpy as np
import pandas as pd

_here = os.path.dirname(__file__)
_project_root = os.path.abspath(os.path.join(_here, ".."))
_file_dir_path = os.path.join(_here, "file_dir.json")
_file_map_cache = None


def get_file_map():
    """Load the CSV path mapping from file_dir.json."""
    global _file_map_cache
    if _file_map_cache is None:
        with open(_file_dir_path, encoding="utf-8") as handle:
            data = json.load(handle)
        file_map = {}
        for key, rel_path in data.items():
            file_map[key] = os.path.join(_project_root, rel_path)
        _file_map_cache = file_map
    return dict(_file_map_cache)


def load_dataset(key, **read_csv_kwargs):
    """Read a CSV file by its logical key."""
    file_map = get_file_map()
    if key not in file_map:
        available = ", ".join(sorted(file_map.keys()))
        raise KeyError(f"Unknown dataset key '{key}'. Available keys: {available}")
    return pd.read_csv(file_map[key], **read_csv_kwargs)


def preprocess_activity_consumption(drop_columns=None, dataset_key="활동소비내역"):
    """Drop unused columns from the activity consumption table."""
    df = load_dataset(dataset_key).copy()
    default_drop = [
        "SGG_CD",
        "ROAD_NM_ADDR",
        "LOTNO_ADDR",
        "ROAD_NM_CD",
        "LOTNO_CD",
        "BRNO",
        "PAYMENT_DT",
        "CONSUME_HIS_SEQ",
        "CONSUME_HIS_SNO",
    ]
    columns_to_drop = list(default_drop)
    if drop_columns:
        for column in drop_columns:
            if column not in columns_to_drop:
                columns_to_drop.append(column)
    return df.drop(columns=columns_to_drop, errors="ignore")


_activity_codebook_csv = """idx,cd_a,cd_b,cd_nm
1055,ACT,"1","취식"
1056,ACT,"2","쇼핑 / 구매"
1057,ACT,"3","체험 활동 / 입장 및 관람"
1058,ACT,"4","단순 구경 / 산책 / 걷기"
1059,ACT,"5","휴식"
1060,ACT,"6","기타 활동"
1094,ACT,"7","환승/경유"
1096,ACT,"99","없음"
"""


def load_activity_codebook():
    """Return the codebook used to label activity types."""
    return pd.read_csv(io.StringIO(_activity_codebook_csv), usecols=["cd_b", "cd_nm"])


def preprocess_activity_history(dataset_key="활동내역", codebook=None):
    """Fill sparse fields and attach readable activity names."""
    df = load_dataset(dataset_key).copy()

    sort_keys = ["TRAVEL_ID", "VISIT_AREA_ID", "ACTIVITY_TYPE_CD", "ACTIVITY_TYPE_SEQ"]
    available_sort_keys = [column for column in sort_keys if column in df.columns]
    if available_sort_keys:
        df = df.sort_values(available_sort_keys)

    fill_columns = ["ACTIVITY_DTL", "RSVT_YN", "EXPND_SE", "ADMISSION_SE"]
    available_fill_columns = [column for column in fill_columns if column in df.columns]
    group_keys = [column for column in ["TRAVEL_ID", "VISIT_AREA_ID", "ACTIVITY_TYPE_CD"] if column in df.columns]
    if available_fill_columns and group_keys:
        df[available_fill_columns] = df.groupby(group_keys)[available_fill_columns].ffill()

    code_df = codebook.copy() if codebook is not None else load_activity_codebook()
    code_df = code_df.rename(columns={"cd_nm": "ACTIVITY_TYPE_NM"})
    code_df["cd_b"] = code_df["cd_b"].astype(str)
    df["ACTIVITY_TYPE_CD"] = df["ACTIVITY_TYPE_CD"].astype(str)
    df = df.merge(code_df, left_on="ACTIVITY_TYPE_CD", right_on="cd_b", how="left")
    return df.drop(columns=["cd_b"], errors="ignore")


def label_encode_series(series):
    """Encode a pandas Series and return the codes plus a value-to-code map."""
    codes, uniques = pd.factorize(series, sort=True)
    encoded = pd.Series(codes, index=series.index, name=f"{series.name}_ENC")
    mapping = {}
    for index, value in enumerate(uniques):
        mapping[value] = index
    return encoded, mapping


def preprocess_lodging_consumption(
    dataset_key="숙박소비내역",
    travel_dataset_key="여행",
    encode_columns=("RSVT_YN", "LODGING_TYPE_CD", "PAYMENT_MTHD_SE"),
):
    """Tidy the lodging consumption data and encode categorical fields."""
    df = load_dataset(dataset_key).copy()
    travel = load_dataset(travel_dataset_key, usecols=["TRAVEL_ID", "TRAVEL_START_YMD"]).copy()

    if "PAYMENT_DT" in df.columns:
        df["PAYMENT_DT"] = pd.to_datetime(df["PAYMENT_DT"], errors="coerce")
    travel["TRAVEL_START_YMD"] = pd.to_datetime(travel["TRAVEL_START_YMD"], errors="coerce")

    df = df.merge(travel, on="TRAVEL_ID", how="left")
    if "PAYMENT_DT" in df.columns:
        df["PAYMENT_DT"] = df["PAYMENT_DT"].fillna(df["TRAVEL_START_YMD"])
        df["PAYMENT_DT"] = pd.to_datetime(df["PAYMENT_DT"], errors="coerce")

    drop_columns = [
        "CHK_IN_DT_MIN",
        "CHK_OUT_DT_MIN",
        "TRAVEL_START_YMD",
        "BRNO",
        "ROAD_NM_CD",
        "LOTNO_CD",
        "PAYMENT_ETC",
    ]
    df = df.drop(columns=drop_columns, errors="ignore")

    for column in ["ROAD_NM_ADDR", "LOTNO_ADDR", "STORE_NM"]:
        if column in df.columns:
            df[column] = df[column].fillna("정보없음")

    lodge_map = {
        1: "호텔",
        2: "펜션",
        3: "콘도미니엄",
        4: "모텔/여관",
        5: "유스호스텔",
        6: "캠핑",
        7: "전통숙소",
        8: "민박",
        9: "기타",
        10: "게스트하우스",
        11: "리조트",
        12: "농어촌/휴양마을",
    }
    if "LODGING_TYPE_CD" in df.columns and "LODGING_TYPE_NM" not in df.columns:
        df["LODGING_TYPE_NM"] = df["LODGING_TYPE_CD"].map(lodge_map)

    encoders = {}
    for column in encode_columns:
        if column in df.columns:
            encoded, mapping = label_encode_series(df[column])
            df[encoded.name] = encoded
            encoders[column] = mapping

    return df, encoders


def preprocess_traveller_master(dataset_key="여행객_Master"):
    """Clean the traveller master table."""
    df = load_dataset(dataset_key).copy()
    drop_columns = []
    for column in ["JOB_ETC", "EDU_FNSH_SE"]:
        if column in df.columns:
            drop_columns.append(column)
    if drop_columns:
        df = df.drop(columns=drop_columns)

    if "HOUSE_INCOME" in df.columns:
        df["HOUSE_INCOME"] = df["HOUSE_INCOME"].fillna(df["HOUSE_INCOME"].median())
    for column in ["TRAVEL_MOTIVE_2", "TRAVEL_MOTIVE_3"]:
        if column in df.columns:
            df[column] = df[column].fillna(0)

    return df.reset_index(drop=True)


def preprocess_visit_area_info(
    dataset_key="방문지정보",
    exclude_codes=(21, 22, 23),
    drop_columns=None,
    return_base_table=False,
):
    """Create per-travel aggregates from the visit area table."""
    df = load_dataset(dataset_key).copy()

    default_drop = [
        "ROAD_NM_ADDR",
        "LOTNO_ADDR",
        "X_COORD",
        "Y_COORD",
        "ROAD_NM_CD",
        "LOTNO_CD",
        "POI_ID",
        "POI_NM",
        "RESIDENCE_TIME_MIN",
        "VISIT_CHC_REASON_CD",
        "LODGING_TYPE_CD",
        "SGG_CD",
    ]
    columns_to_drop = list(default_drop)
    if drop_columns:
        for column in drop_columns:
            if column not in columns_to_drop:
                columns_to_drop.append(column)
    df = df.drop(columns=columns_to_drop, errors="ignore")

    for column in ["VISIT_START_YMD", "VISIT_END_YMD"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    filtered = df
    if "VISIT_AREA_TYPE_CD" in df.columns:
        filtered = df[~df["VISIT_AREA_TYPE_CD"].isin(set(exclude_codes))].copy()

    parts = []

    if not filtered.empty:
        if "DGSTFN" in filtered.columns:
            parts.append(filtered.groupby("TRAVEL_ID")["DGSTFN"].mean().rename("DGSTFN_AVG"))
        if "REVISIT_INTENTION" in filtered.columns:
            parts.append(filtered.groupby("TRAVEL_ID")["REVISIT_INTENTION"].mean().rename("REVISIT_AVG"))
        if "RCMDTN_INTENTION" in filtered.columns:
            parts.append(filtered.groupby("TRAVEL_ID")["RCMDTN_INTENTION"].mean().rename("RCMDTN_AVG"))

        if {"VISIT_START_YMD", "VISIT_END_YMD"}.issubset(df.columns):
            trip_days = df.groupby("TRAVEL_ID").apply(
                lambda x: (x["VISIT_END_YMD"].max() - x["VISIT_START_YMD"].min()).days + 1
                if x["VISIT_START_YMD"].notna().any() and x["VISIT_END_YMD"].notna().any()
                else np.nan
            ).rename("TRIP_DAYS")
            parts.append(trip_days)

        if "VISIT_AREA_NM" in filtered.columns:
            move_count = filtered.groupby("TRAVEL_ID")["VISIT_AREA_NM"].count().rename("MOVE_CNT")
            parts.append(move_count)

        if "REVISIT_YN" in filtered.columns:
            def visit_rate(series):
                total = len(series)
                if total == 0:
                    return np.nan
                return (series.astype(str).str.upper() == "Y").sum() / total

            rate = filtered.groupby("TRAVEL_ID")["REVISIT_YN"].apply(visit_rate).rename("VISIT_RATE")
            parts.append(rate)

    if parts:
        aggregated = pd.concat(parts, axis=1).reset_index()
    else:
        aggregated = pd.DataFrame(
            columns=["TRAVEL_ID", "DGSTFN_AVG", "REVISIT_AVG", "RCMDTN_AVG", "TRIP_DAYS", "MOVE_CNT", "VISIT_RATE"]
        )

    if return_base_table:
        return df.reset_index(drop=True), aggregated
    return aggregated


def get_preprocessing_dir(output_dir=None):
    """Return the folder where preprocessed data should be stored."""
    if output_dir:
        return output_dir
    return os.path.join(_project_root, "data", "training", "preprocessing")


def ensure_preprocessing_dir(output_dir=None):
    """Create the preprocessing folder if it does not already exist."""
    path_value = get_preprocessing_dir(output_dir)
    os.makedirs(path_value, exist_ok=True)
    return path_value


def save_dataframe(df, filename, output_dir=None):
    """Save a DataFrame as CSV inside the preprocessing folder."""
    folder = ensure_preprocessing_dir(output_dir)
    filepath = os.path.join(folder, filename)
    df.to_csv(filepath, index=False)
    return filepath


def save_activity_consumption(output_dir=None, **preprocess_kwargs):
    """Run the activity consumption preprocessing and save the result."""
    df = preprocess_activity_consumption(**preprocess_kwargs)
    return save_dataframe(df, "activity_consumption.csv", output_dir)


def save_activity_history(output_dir=None, **preprocess_kwargs):
    """Run the activity history preprocessing and save the result."""
    df = preprocess_activity_history(**preprocess_kwargs)
    return save_dataframe(df, "activity_history.csv", output_dir)


def _encode_mapping_for_json(encoders):
    """Convert label encoder mappings into JSON friendly dicts."""
    result = {}
    for column, mapping in encoders.items():
        safe_mapping = {}
        for value, index in mapping.items():
            if isinstance(value, float) and np.isnan(value):
                key = "NaN"
            else:
                key = str(value)
            safe_mapping[key] = int(index)
        result[column] = safe_mapping
    return result


def save_lodging_consumption(output_dir=None, **preprocess_kwargs):
    """Run the lodging preprocessing, save the table, and write encoders."""
    df, encoders = preprocess_lodging_consumption(**preprocess_kwargs)
    data_path = save_dataframe(df, "lodging_consumption.csv", output_dir)
    if encoders:
        folder = ensure_preprocessing_dir(output_dir)
        encoder_path = os.path.join(folder, "lodging_encoders.json")
        with open(encoder_path, "w", encoding="utf-8") as handle:
            json.dump(_encode_mapping_for_json(encoders), handle, ensure_ascii=False, indent=2)
    return data_path


def save_traveller_master(output_dir=None, **preprocess_kwargs):
    """Run the traveller preprocessing and save the cleaned table."""
    df = preprocess_traveller_master(**preprocess_kwargs)
    return save_dataframe(df, "traveller_master.csv", output_dir)


def save_travel_table(output_dir=None, dataset_key="여행"):
    """Save a cleaned travel table with duplicate columns removed."""
    df = load_dataset(dataset_key).copy()

    # TRAVEL_MISSION is identical to TRAVEL_PURPOSE, so drop to avoid duplication
    if "TRAVEL_MISSION" in df.columns:
        df = df.drop(columns=["TRAVEL_MISSION"], errors="ignore")

    # write the cleaned version for downstream merges/EDA
    return save_dataframe(df, "travel.csv", output_dir)


def save_visit_area_info(output_dir=None, save_base_table=False, **preprocess_kwargs):
    """Run the visit area preprocessing and save the aggregated result."""
    if save_base_table:
        base_df, summary_df = preprocess_visit_area_info(return_base_table=True, **preprocess_kwargs)
        base_path = save_dataframe(base_df, "visit_area_base.csv", output_dir)
    else:
        summary_df = preprocess_visit_area_info(**preprocess_kwargs)
        base_path = None
    summary_path = save_dataframe(summary_df, "visit_area_summary.csv", output_dir)
    if save_base_table:
        return base_path, summary_path
    return summary_path


def save_all_preprocessed_data(output_dir=None, save_visit_base=False):
    """Run every preprocessing step and save each result to disk."""
    paths = {}
    paths["activity_consumption"] = save_activity_consumption(output_dir=output_dir)
    paths["activity_history"] = save_activity_history(output_dir=output_dir)
    paths["lodging_consumption"] = save_lodging_consumption(output_dir=output_dir)
    paths["traveller_master"] = save_traveller_master(output_dir=output_dir)
    paths["travel"] = save_travel_table(output_dir=output_dir)
    if save_visit_base:
        base_path, summary_path = save_visit_area_info(output_dir=output_dir, save_base_table=True)
        paths["visit_area_base"] = base_path
        paths["visit_area_summary"] = summary_path
    else:
        paths["visit_area_summary"] = save_visit_area_info(output_dir=output_dir)
    return paths
