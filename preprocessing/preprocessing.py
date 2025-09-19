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
    # 파일에서 전처리 대상 데이터를 불러와 복사본으로 작업합니다.

    df = load_dataset(dataset_key).copy()
    # 자주 사용하지 않는 열 목록을 미리 정리합니다.

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
    # 기본 삭제 목록을 복사해서 수정 가능한 리스트로 만듭니다.

    columns_to_drop = list(default_drop)
    if drop_columns:
        # 사용자 정의 열이 있다면 중복 없이 목록에 추가합니다.

        for column in drop_columns:
            if column not in columns_to_drop:
                columns_to_drop.append(column)
    # 준비한 목록에 따라 실제로 열을 제거합니다.

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
    # 전처리 대상 데이터를 불러와 복사본으로 안전하게 다룹니다.

    df = load_dataset(dataset_key).copy()

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


def label_encode_series(series):
    """Encode a pandas Series and return the codes plus a value-to-code map."""
    # factorize를 사용해 고유값마다 정수 코드를 배정합니다.

    codes, uniques = pd.factorize(series, sort=True)
    # 원래 인덱스를 보존한 채 새 정수 코드 시리즈를 만듭니다.

    encoded = pd.Series(codes, index=series.index, name=f"{series.name}_ENC")
    mapping = {}
    for index, value in enumerate(uniques):
        # 한눈에 참고할 수 있도록 값과 코드 매핑을 딕셔너리에 저장합니다.

        mapping[value] = index
    return encoded, mapping


def preprocess_lodging_consumption(
    dataset_key="숙박소비내역",
    travel_dataset_key="여행",
    encode_columns=("RSVT_YN", "LODGING_TYPE_CD", "PAYMENT_MTHD_SE"),
):
    """Tidy the lodging consumption data and encode categorical fields."""
    # 숙박 이용 정보와 여행 기본 정보를 각각 불러옵니다.

    df = load_dataset(dataset_key).copy()
    travel = load_dataset(travel_dataset_key, usecols=["TRAVEL_ID", "TRAVEL_START_YMD"]).copy()

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

    # 범주형 열을 정수로 변환하고 매핑을 함께 저장합니다.

    encoders = {}
    for column in encode_columns:
        # 선택된 열마다 정수 인코딩을 적용하고 결과 열을 만듭니다.

        if column in df.columns:
            encoded, mapping = label_encode_series(df[column])
            df[encoded.name] = encoded
            encoders[column] = mapping

    # 전처리된 데이터와 각 열의 인코딩 정보를 함께 반환합니다.

    return df, encoders


def preprocess_traveller_master(dataset_key="여행객_Master"):
    """Clean the traveller master table."""
    # 여행객 기본 정보를 불러와 복사본으로 정리합니다.

    df = load_dataset(dataset_key).copy()
    drop_columns = []
    # 사용 빈도가 낮은 열을 모아 삭제 목록에 추가합니다.

    for column in ["JOB_ETC", "EDU_FNSH_SE"]:
        if column in df.columns:
            drop_columns.append(column)
    if drop_columns:
        # 모아둔 열을 한 번에 삭제해 표를 간결하게 만듭니다.

        df = df.drop(columns=drop_columns)

    # 가구소득이 비어 있다면 중앙값으로 채워 극단값 영향을 줄입니다.

    if "HOUSE_INCOME" in df.columns:
        df["HOUSE_INCOME"] = df["HOUSE_INCOME"].fillna(df["HOUSE_INCOME"].median())
    # 보조 여행 동기가 없으면 0으로 채워 의미를 명확히 합니다.

    for column in ["TRAVEL_MOTIVE_2", "TRAVEL_MOTIVE_3"]:
        if column in df.columns:
            df[column] = df[column].fillna(0)

    # 정리된 표의 인덱스를 재정렬하고 결과를 반환합니다.

    return df.reset_index(drop=True)


def preprocess_visit_area_info(
    dataset_key="방문지정보",
    exclude_codes=(21, 22, 23),
    drop_columns=None,
    return_base_table=False,
):
    """Create per-travel aggregates from the visit area table."""
    # 방문지 정보를 불러와 복사본으로 전처리를 진행합니다.

    df = load_dataset(dataset_key).copy()

    # 분석에 필요 없는 상세 위치 정보 등을 기본으로 제거합니다.

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
    # 기본 목록을 복사해 실제로 제거할 열 리스트를 만듭니다.

    columns_to_drop = list(default_drop)
    if drop_columns:
        for column in drop_columns:
            if column not in columns_to_drop:
                columns_to_drop.append(column)
    # 준비된 목록에 따라 열을 삭제해 표를 단순화합니다.

    df = df.drop(columns=columns_to_drop, errors="ignore")

    # 방문 시작/종료일을 날짜 형식으로 변환해 계산이 가능하게 합니다.

    for column in ["VISIT_START_YMD", "VISIT_END_YMD"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    filtered = df
    if "VISIT_AREA_TYPE_CD" in df.columns:
        # 분석에서 제외할 방문 유형 코드는 미리 걸러냅니다.

        filtered = df[~df["VISIT_AREA_TYPE_CD"].isin(set(exclude_codes))].copy()

    # 여행 단위로 계산한 통계들을 모아둘 리스트입니다.

    parts = []

    if not filtered.empty:
        if "DGSTFN" in filtered.columns:
            # 여행별 만족도 평균을 계산합니다.

            parts.append(filtered.groupby("TRAVEL_ID")["DGSTFN"].mean().rename("DGSTFN_AVG"))
        if "REVISIT_INTENTION" in filtered.columns:
            # 재방문 의향 평균을 계산합니다.

            parts.append(filtered.groupby("TRAVEL_ID")["REVISIT_INTENTION"].mean().rename("REVISIT_AVG"))
        if "RCMDTN_INTENTION" in filtered.columns:
            # 추천 의향 평균을 계산합니다.

            parts.append(filtered.groupby("TRAVEL_ID")["RCMDTN_INTENTION"].mean().rename("RCMDTN_AVG"))

        if {"VISIT_START_YMD", "VISIT_END_YMD"}.issubset(df.columns):
            # 여행 기간(일수)을 계산해 추가합니다.

            trip_days = df.groupby("TRAVEL_ID").apply(
                lambda x: (x["VISIT_END_YMD"].max() - x["VISIT_START_YMD"].min()).days + 1
                if x["VISIT_START_YMD"].notna().any() and x["VISIT_END_YMD"].notna().any()
                else np.nan
            ).rename("TRIP_DAYS")
            parts.append(trip_days)

        if "VISIT_AREA_NM" in filtered.columns:
            # 방문한 장소 수를 계산해 이동 횟수 지표로 활용합니다.

            move_count = filtered.groupby("TRAVEL_ID")["VISIT_AREA_NM"].count().rename("MOVE_CNT")
            parts.append(move_count)

        if "REVISIT_YN" in filtered.columns:
            # 'Y' 비율로 재방문 경험 비중을 구합니다.

            def visit_rate(series):
                total = len(series)
                if total == 0:
                    return np.nan
                return (series.astype(str).str.upper() == "Y").sum() / total

            rate = filtered.groupby("TRAVEL_ID")["REVISIT_YN"].apply(visit_rate).rename("VISIT_RATE")
            parts.append(rate)

    # 계산된 통계를 하나의 표로 합칩니다.

    if parts:
        aggregated = pd.concat(parts, axis=1).reset_index()
    else:
        aggregated = pd.DataFrame(
            columns=["TRAVEL_ID", "DGSTFN_AVG", "REVISIT_AVG", "RCMDTN_AVG", "TRIP_DAYS", "MOVE_CNT", "VISIT_RATE"]
        )

    if return_base_table:
        # 전처리된 원본 표와 요약 표를 함께 반환할 수도 있습니다.

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
