import io
import json
import os


import numpy as np
import pandas as pd

_here = os.path.dirname(__file__)
_project_root = os.path.abspath(os.path.join(_here, ".."))
_file_map_cache = {} # Changed to a dictionary to cache multiple file maps

# Monetary amounts in the raw tables are recorded in Korean won and tend to dwarf
# other feature scales after aggregation. Converting to thousands keeps relative
# ordering intact while preventing those sums from dominating model training.
_PAYMENT_AMOUNT_SCALE = 1_000.0


def get_file_map(mode="train", year=None):
    """Load the CSV path mapping from the appropriate file_dir.json for a given year."""
    if year is None:
        raise ValueError("The 'year' parameter must be provided.")

    global _file_map_cache
    cache_key = f"{mode}_{year}"
    
    if cache_key not in _file_map_cache:
        if mode == "validation":
            file_name = "file_dir_validation.json"
        else:  # Default to train
            file_name = "file_dir.json"
        
        # Construct path to the year-specific directory
        file_path = os.path.join(_project_root, "data", mode, year, file_name)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The mapping file '{file_name}' was not found in '{os.path.dirname(file_path)}'. Please create it.")

        with open(file_path, encoding="utf-8") as handle:
            data = json.load(handle)
        
        file_map = {}
        for key, rel_path in data.items():
            # Paths in file_dir.json are relative to the project root
            file_map[key] = os.path.join(_project_root, rel_path)
        _file_map_cache[cache_key] = file_map
        
    return dict(_file_map_cache[cache_key])


def load_dataset(key, mode="train", year=None, **read_csv_kwargs):
    """Read a CSV file by its logical key, mode, and year."""
    file_map = get_file_map(mode=mode, year=year)
    if key not in file_map:
        available = ", ".join(sorted(file_map.keys()))
        raise KeyError(f"Unknown dataset key '{key}'. Available keys: {available}")
    return pd.read_csv(file_map[key], **read_csv_kwargs)


def preprocess_activity_consumption(drop_columns=None, dataset_key="활동소비내역", mode="train", year=None):
    """Drop unused columns from the activity consumption table."""
    df = load_dataset(dataset_key, mode=mode, year=year).copy()
    default_drop = []
    columns_to_drop = list(default_drop)
    if drop_columns:
        for column in drop_columns:
            if column not in columns_to_drop:
                columns_to_drop.append(column)
    df = df.drop(columns=columns_to_drop, errors="ignore")

    if "PAYMENT_AMT_WON" in df.columns:
        df["PAYMENT_AMT_WON"] = (
            pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)
        )

    return df


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


def preprocess_activity_history(dataset_key="활동내역", codebook=None, mode="train", year=None):
    """Fill sparse fields and attach readable activity names."""
    df = load_dataset(dataset_key, mode=mode, year=year).copy()

    # 여행 진행 순서를 맞추기 위해 정렬 기준을 지정합니다.

    sort_keys = ["TRAVEL_ID", "VISIT_AREA_ID", "ACTIVITY_TYPE_CD", "ACTIVITY_TYPE_SEQ"]
    available_sort_keys = [column for column in sort_keys if column in df.columns]
    if available_sort_keys:
        df = df.sort_values(available_sort_keys)

    # 누락값을 보완할 열을 골라 앞선 값으로 채울 준비를 합니다.

    fill_columns = ["ACTIVITY_DTL", "RSVT_YN", "EXPND_SE", "ADMISSION_SE"]
    available_fill_columns = [column for column in fill_columns if column in df.columns]
    group_keys = [column for column in ["TRAVEL_ID", "VISIT_AREA_ID", "ACTIVITY_TYPE_CD"] if column in df.columns]
    if available_fill_columns and group_keys:
        # 같은 여행/방문 묶음 안에서는 앞선 값으로 결측을 채웁니다.

        df[available_fill_columns] = df.groupby(group_keys)[available_fill_columns].ffill()

    # 활동 유형 코드를 사람이 읽기 쉬운 이름으로 바꾸기 위해 코드북을 준비합니다.

    code_df = codebook.copy() if codebook is not None else load_activity_codebook()
    code_df = code_df.rename(columns={"cd_nm": "ACTIVITY_TYPE_NM"})
    code_df["cd_b"] = code_df["cd_b"].astype(str)
    df["ACTIVITY_TYPE_CD"] = df["ACTIVITY_TYPE_CD"].astype(str)
    # 코드북과 합쳐서 활동명 열을 붙입니다.

    df = df.merge(code_df, left_on="ACTIVITY_TYPE_CD", right_on="cd_b", how="left")
    # 불필요해진 코드 열은 삭제하고 결과를 반환합니다.

    return df.drop(columns=["cd_b"], errors="ignore")


def preprocess_lodging_consumption(
    dataset_key="숙박소비내역",
    travel_dataset_key="여행",
    mode="train",
    year=None
):
    """Tidy the lodging consumption data and encode categorical fields."""
    df = load_dataset(dataset_key, mode=mode, year=year).copy()
    travel = load_dataset(travel_dataset_key, usecols=["TRAVEL_ID", "TRAVEL_START_YMD"], mode=mode, year=year).copy()

    if "PAYMENT_DT" in df.columns:
        # 결제일을 날짜 형식으로 변환해 계산이 가능하도록 만듭니다.

        df["PAYMENT_DT"] = pd.to_datetime(df["PAYMENT_DT"], errors="coerce")
    # 여행 시작일도 동일하게 날짜 형식으로 정리합니다.

    travel["TRAVEL_START_YMD"] = pd.to_datetime(travel["TRAVEL_START_YMD"], errors="coerce")

    # 여행 정보와 결합해 각 숙박건의 여행 시작일을 참고할 수 있게 합니다.

    df = df.merge(travel, on="TRAVEL_ID", how="left")
    # 결제일이 없으면 여행 시작일로 채워 분석 공백을 줄입니다.

    if "PAYMENT_DT" in df.columns:
        df["PAYMENT_DT"] = df["PAYMENT_DT"].fillna(df["TRAVEL_START_YMD"])
        # 채운 뒤에는 다시 날짜 형식으로 변환해 일관성을 유지합니다.

        df["PAYMENT_DT"] = pd.to_datetime(df["PAYMENT_DT"], errors="coerce")

    # 분석에 쓰이지 않는 열은 미리 목록으로 만들어 제거합니다.

    drop_columns = [
        "CHK_IN_DT_MIN",
        "CHK_OUT_DT_MIN",
        "TRAVEL_START_YMD",
        "BRNO",
        "ROAD_NM_CD",
        "LOTNO_CD",
        "PAYMENT_ETC",
    ]
    # 불필요한 열을 실제로 삭제해 표를 단순화합니다.

    df = df.drop(columns=drop_columns, errors="ignore")

    if "PAYMENT_AMT_WON" in df.columns:
        df["PAYMENT_AMT_WON"] = (
            pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0) / _PAYMENT_AMOUNT_SCALE
        )

    # 주소나 업소명이 비어 있는 경우 기본값으로 채웁니다.

    for column in ["ROAD_NM_ADDR", "LOTNO_ADDR", "STORE_NM"]:
        # 빈 값은 '정보없음'으로 표기해 누락 여부를 명확히 합니다.

        if column in df.columns:
            df[column] = df[column].fillna("정보없음")

    # 숫자 코드만으로는 알아보기 어려운 숙박 유형 이름을 붙입니다.

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
        # 매핑을 이용해 숙박 유형 이름을 추가합니다.

        df["LODGING_TYPE_NM"] = df["LODGING_TYPE_CD"].map(lodge_map)

    # Categorical encoding removed as per request.
    encoders = {}
    return df, encoders


def load_travel_purpose_codebook():
    """Loads the travel purpose codebook from tc_codeb_코드B.json."""
    codebook_path = os.path.join(_project_root, "data", "tag_code", "training", "json", "tc_codeb_코드B.json")
    if not os.path.exists(codebook_path):
        raise FileNotFoundError(f"Codebook not found at {codebook_path}")
    
    df = pd.read_json(codebook_path)
    purpose_codes = df[df['cd_a'] == 'MIS'].copy()
    purpose_codes['cd_b'] = purpose_codes['cd_b'].astype(str)
    return purpose_codes[['cd_b', 'cd_nm']]

def preprocess_traveller_master(dataset_key="여행객_Master", mode="train", year=None):
    """
    여행객 Master 테이블을 전처리하고, 거주지 및 목적지 컬럼을 SGG_CD1 코드로 변환합니다.
    """
    df = load_dataset(dataset_key, mode=mode, year=year).copy()
    
    # Columns to drop
    drop_columns = [
        "TRAVEL_STATUS_YMD", "JOB_ETC", "EDU_FNSH_SE",
        "TRAVEL_LIKE_SIDO_1", "TRAVEL_LIKE_SIDO_2", "TRAVEL_LIKE_SIDO_3",
        "TRAVEL_LIKE_SGG_1", "TRAVEL_LIKE_SGG_2", "TRAVEL_LIKE_SGG_3",
        "TRAVEL_MOTIVE_2", "TRAVEL_MOTIVE_3"
    ]

    df = df.drop(columns=drop_columns, errors="ignore")

    # Manual encoding for GENDER
    if 'GENDER' in df.columns:
        gender_map = {'남': 1, '남자': 1, '여': 2, '여자': 2}
        df['GENDER'] = df['GENDER'].map(gender_map)

    # --- Create Persona Column ---
    if 'TRAVEL_PURPOSE' in df.columns:
        purpose_codebook = load_travel_purpose_codebook()
        df['TRAVEL_PURPOSE'] = df['TRAVEL_PURPOSE'].astype(str)
        df = df.merge(
            purpose_codebook,
            left_on='TRAVEL_PURPOSE',
            right_on='cd_b',
            how='left'
        )
        df = df.drop(columns=['cd_b'], errors='ignore')
        df = df.rename(columns={'cd_nm': 'TRAVEL_PERSONA_PURPOSE'})

    # Null handling
    object_cols = ["TRAVEL_PERSONA", "TRAVEL_MISSION_CHECK", "TRAVEL_PURPOSE", 
                   "TRAVEL_STATUS_RESIDENCE", "TRAVEL_STATUS_DESTINATION", "JOB_NM", "TRAVEL_PERSONA_PURPOSE"]
    for col in object_cols:
        if col in df.columns:
            df[col] = df[col].fillna("정보없음")

    integer_cols = ["AGE_GRP", "HOUSE_INCOME", "GENDER", "TRAVEL_MOTIVE_1"] + [f"TRAVEL_STYLE_{i}" for i in range(1, 9)]
    for col in integer_cols:
        if col in df.columns:
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)

    # 정리된 표의 인덱스를 재정렬하고 결과를 반환합니다.
    return df.reset_index(drop=True)


def preprocess_visit_area_info(
    dataset_key="방문지정보",
    exclude_codes=(21, 22, 23),
    drop_columns=None,
    return_base_table=False,
    mode="train",
    year=None
):
    """
    방문지 정보 테이블에서 여행 단위의 요약 통계를 생성합니다.
    """
    # 1. 원본 데이터 로드 및 기본 전처리
    df = load_dataset(dataset_key, mode=mode, year=year).copy()
    default_drop = [
        "ROAD_NM_ADDR", "LOTNO_ADDR", "X_COORD", "Y_COORD", "ROAD_NM_CD",
        "LOTNO_CD", "POI_ID", "POI_NM", "RESIDENCE_TIME_MIN",
        "LODGING_TYPE_CD", "SGG_CD",
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

    # 2. 여행 단위(TRAVEL_ID)로 통계 집계
    parts = []
    
    # 만족도, 재방문/추천의향 평균 계산 (제외 코드 제외)
    if "VISIT_AREA_TYPE_CD" in df.columns:
        filtered = df[~df["VISIT_AREA_TYPE_CD"].isin(set(exclude_codes))].copy()
    else:
        filtered = df.copy()

    if not filtered.empty:
        if "DGSTFN" in filtered.columns:
            parts.append(filtered.groupby("TRAVEL_ID")["DGSTFN"].mean().rename("DGSTFN_AVG"))
        if "REVISIT_INTENTION" in filtered.columns:
            parts.append(filtered.groupby("TRAVEL_ID")["REVISIT_INTENTION"].mean().rename("REVISIT_AVG"))
        if "RCMDTN_INTENTION" in filtered.columns:
            parts.append(filtered.groupby("TRAVEL_ID")["RCMDTN_INTENTION"].mean().rename("RCMDTN_AVG"))

    if 'VISIT_AREA_TYPE_CD' in df.columns:
        visit_area_type_mode = df.groupby('TRAVEL_ID')['VISIT_AREA_TYPE_CD'].agg(lambda x: x.mode()[0] if not x.mode().empty else np.nan).rename('VISIT_AREA_TYPE_CD')
        parts.append(visit_area_type_mode)
    
    # 여행 기간(TRIP_DAYS) 및 이동 횟수(MOVE_CNT) 계산
    if {"VISIT_START_YMD", "VISIT_END_YMD"}.issubset(df.columns):
        trip_days = df.groupby("TRAVEL_ID").apply(
            lambda x: (x["VISIT_END_YMD"].max() - x["VISIT_START_YMD"].min()).days + 1
            if x["VISIT_START_YMD"].notna().any() and x["VISIT_END_YMD"].notna().any()
            else np.nan
        ).rename("TRIP_DAYS")
        parts.append(trip_days)
    if "VISIT_AREA_NM" in df.columns:
        move_count = df.groupby("TRAVEL_ID")["VISIT_AREA_NM"].count().rename("MOVE_CNT")
        parts.append(move_count)

    # 집계된 모든 통계를 하나의 데이터프레임으로 합칩니다.
    if not parts:
        return pd.DataFrame()
        
    aggregated = pd.concat(parts, axis=1).reset_index()

    if return_base_table:
        return df.reset_index(drop=True), aggregated

    return aggregated


def get_preprocessing_dir(output_dir=None):
    """Return the folder where preprocessed data should be stored."""
    if output_dir:
        # Use the absolute path for consistency
        return os.path.abspath(output_dir)
    # Fallback to default training path if not provided
    return os.path.join(_project_root, "data", "training", "preprocessing")


def ensure_preprocessing_dir(output_dir=None):
    """Create the preprocessing folder if it does not already exist."""
    path_value = get_preprocessing_dir(output_dir)
    os.makedirs(path_value, exist_ok=True)
    return path_value


def save_dataframe(df, filename, output_dir=None):
    """Save a DataFrame as CSV inside the specified output folder."""
    folder = ensure_preprocessing_dir(output_dir)
    filepath = os.path.join(folder, filename)
    df.to_csv(filepath, index=False)
    return filepath


def save_activity_consumption(output_dir=None, mode="train", year=None, **preprocess_kwargs):
    """Run the activity consumption preprocessing and save the result."""
    df = preprocess_activity_consumption(mode=mode, year=year, **preprocess_kwargs)
    return save_dataframe(df, "activity_consumption.csv", output_dir)


def save_activity_history(output_dir=None, mode="train", year=None, **preprocess_kwargs):
    """Run the activity history preprocessing and save the result."""
    df = preprocess_activity_history(mode=mode, year=year, **preprocess_kwargs)
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


def save_lodging_consumption(output_dir=None, mode="train", year=None, **preprocess_kwargs):
    """Run the lodging preprocessing, save the table, and write encoders."""
    df, encoders = preprocess_lodging_consumption(mode=mode, year=year, **preprocess_kwargs)
    data_path = save_dataframe(df, "lodging_consumption.csv", output_dir)
    if encoders:
        folder = ensure_preprocessing_dir(output_dir)
        json_dir = os.path.join(folder, "json")
        os.makedirs(json_dir, exist_ok=True)
        encoder_path = os.path.join(json_dir, "lodging_consumption_encoding.json")
        with open(encoder_path, "w", encoding="utf-8") as handle:
            json.dump(_encode_mapping_for_json(encoders), handle, ensure_ascii=False, indent=2)
    return data_path


def save_traveller_master(output_dir=None, mode="train", year=None, **preprocess_kwargs):
    """Run the traveller preprocessing and save the cleaned table."""
    df = preprocess_traveller_master(mode=mode, year=year, **preprocess_kwargs)
    return save_dataframe(df, "traveller_master.csv", output_dir)


def save_travel_table(output_dir=None, dataset_key="여행", mode="train", year=None):
    """Save a trimmed travel table that only keeps identifiers and travel season."""
    df = load_dataset(dataset_key, mode=mode, year=year).copy()

    start_date_col = "TRAVEL_START_YMD"

    if start_date_col in df.columns:
        df[start_date_col] = pd.to_datetime(df[start_date_col], errors="coerce")
        
        month = df[start_date_col].dt.month
        season_map = {
            1: '겨울', 2: '겨울',
            3: '봄', 4: '봄', 5: '봄',
            6: '여름', 7: '여름', 8: '여름',
            9: '가을', 10: '가을', 11: '가을',
            12: '겨울'
        }
        df['TRAVEL_SEASON'] = month.map(season_map)

    columns_to_keep = ["TRAVEL_ID", "TRAVELER_ID", "TRAVEL_SEASON"]
    existing_columns = [column for column in columns_to_keep if column in df.columns]
    df = df[existing_columns].copy()

    return save_dataframe(df, "travel.csv", output_dir)


def save_visit_area_info(output_dir=None, save_base_table=False, mode="train", year=None, **preprocess_kwargs):
    """Run the visit area preprocessing and save the aggregated result."""
    if save_base_table:
        base_df, summary_df = preprocess_visit_area_info(return_base_table=True, mode=mode, year=year, **preprocess_kwargs)
        base_path = save_dataframe(base_df, "visit_area_base.csv", output_dir)
    else:
        summary_df = preprocess_visit_area_info(mode=mode, year=year, **preprocess_kwargs)
        base_path = None
    summary_path = save_dataframe(summary_df, "visit_area_summary.csv", output_dir)
    if save_base_table:
        return base_path, summary_path
    return summary_path


def save_all_preprocessed_data(output_dir=None, save_visit_base=False, mode="train", year=None):
    """Run every preprocessing step and save each result to disk."""
    paths = {}
    paths["activity_consumption"] = save_activity_consumption(output_dir=output_dir, mode=mode, year=year)
    paths["activity_history"] = save_activity_history(output_dir=output_dir, mode=mode, year=year)
    paths["lodging_consumption"] = save_lodging_consumption(output_dir=output_dir, mode=mode, year=year)
    paths["traveller_master"] = save_traveller_master(output_dir=output_dir, mode=mode, year=year)
    paths["travel"] = save_travel_table(output_dir=output_dir, mode=mode, year=year)
    if save_visit_base:
        base_path, summary_path = save_visit_area_info(output_dir=output_dir, save_base_table=True, mode=mode, year=year)
        paths["visit_area_base"] = base_path
        paths["visit_area_summary"] = summary_path
    else:
        paths["visit_area_summary"] = save_visit_area_info(output_dir=output_dir, mode=mode, year=year)
    return paths
