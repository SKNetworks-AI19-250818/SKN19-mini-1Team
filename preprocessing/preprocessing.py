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
    # PLAN: keep PAYMENT_NUM and PAYMENT_MTHD_SE from TL_csv/tn_activity_consume_his so we can later emit activity_amt_mean_per_payment, activity_amt_max_single, and activity_card_ratio per TRAVEL_ID.
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
    # PLAN: expose RSVT_YN, EXPND_SE, and ADMISSION_SE as binary indicators for downstream activity_reservation_rate, activity_paid_ratio, and activity_free_entry_ratio rollups sourced from TL_csv/tn_activity_his.
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
    # PLAN: parse CHK_IN_DT_MIN and CHK_OUT_DT_MIN into lodging_nights and pair with PAYMENT_NUM to derive lodging_amt_per_night and lodging_payment_max using TL_csv/tn_lodge_consume_his.
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



def get_sido_code_map():
    """
    JSON 파일을 읽어 SIDO_NM을 SSG_CD1로 매핑하는 딕셔너리를 생성합니다.
    다양한 형태의 축약된 지명도 처리합니다.
    """
    json_path = os.path.join(_project_root, "data", "tag_code", "training", "json", "tc_sgg_시군구코드.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sido_map = {}
    # JSON 파일에서 중복을 제거한 {SIDO_NM: SGG_CD1} 맵을 먼저 생성
    unique_sido = {item['SIDO_NM']: item['SGG_CD1'] for item in data if item.get('SIDO_NM')}

    for sido_nm, sgg_cd1 in unique_sido.items():
        # 원본 이름 추가 (예: "서울특별시")
        sido_map[sido_nm] = sgg_cd1
        
        # 일반적인 축약어 추가 (예: "서울", "경기")
        if '특별시' in sido_nm:
            sido_map[sido_nm.replace('특별시', '')] = sgg_cd1
        if '광역시' in sido_nm:
            sido_map[sido_nm.replace('광역시', '')] = sgg_cd1
        if '특별자치시' in sido_nm:
             sido_map[sido_nm.replace('특별자치시', '')] = sgg_cd1
        if sido_nm.endswith('도'):
            sido_map[sido_nm[:-1]] = sgg_cd1

    # 요청하신 특정 축약어와 전체 이름 매핑
    sido_map['충남'] = unique_sido.get('충청남도')
    sido_map['충북'] = unique_sido.get('충청북도')
    sido_map['경남'] = unique_sido.get('경상남도')
    sido_map['경북'] = unique_sido.get('경상북도')
    sido_map['전남'] = unique_sido.get('전라남도')
    sido_map['전북'] = unique_sido.get('전라북도')

    return sido_map

def preprocess_traveller_master(dataset_key="여행객_Master"):
    """
    여행객 Master 테이블을 전처리하고, 거주지 및 목적지 컬럼을 SGG_CD1 코드로 변환합니다.
    """
    df = load_dataset(dataset_key).copy()
    sido_code_map = get_sido_code_map()
    
    # 긴 이름부터 찾도록 키를 정렬 ('경상남도'가 '경남'보다 먼저 매칭되도록)
    sorted_sido_keys = sorted(sido_code_map.keys(), key=len, reverse=True)

    def get_code_from_text(text):
        """문자열에서 지역명 키를 찾아 코드를 반환하는 함수"""
        if not isinstance(text, str):
            return None
        for key in sorted_sido_keys:
            if key in text:
                return sido_code_map[key]
        return None

    # TRAVEL_STATUS_RESIDENCE 컬럼 변환
    if "TRAVEL_STATUS_RESIDENCE" in df.columns:
        df["TRAVEL_STATUS_RESIDENCE_CODE"] = (
            df["TRAVEL_STATUS_RESIDENCE"].apply(get_code_from_text)
            .fillna(0)
            .astype(int)
        )

    # TRAVEL_STATUS_DESTINATION 컬럼 변환
    if "TRAVEL_STATUS_DESTINATION" in df.columns:
        df["TRAVEL_STATUS_DESTINATION_CODE"] = (
            df["TRAVEL_STATUS_DESTINATION"].apply(get_code_from_text)
            .fillna(0)
            .astype(int)
        )

    # Columns to drop as requested by user and for cleaning
    drop_columns = ["TRAVEL_STATUS_YMD"] + [f"TRAVEL_STYLE_{i}" for i in range(1, 9)]
    drop_columns.extend(["JOB_ETC", "EDU_FNSH_SE"])

    # Drop all collected columns at once
    df = df.drop(columns=drop_columns, errors="ignore")

    # 가구소득이 비어 있다면 중앙값으로 채워 극단값 영향을 줄입니다.
    if "HOUSE_INCOME" in df.columns:
        df["HOUSE_INCOME"] = df["HOUSE_INCOME"].fillna(df["HOUSE_INCOME"].median())
        
    # 보조 여행 동기가 없으면 0으로 채워 의미를 명확히 합니다.
    for column in ["TRAVEL_MOTIVE_2", "TRAVEL_MOTIVE_3"]:
        if column in df.columns:
            df[column] = df[column].fillna(0)
            
    # TRAVEL_STYL_1 부터 TRAVEL_STYL_7 까지의 컬럼명을 리스트로 생성
    style_columns_to_drop = [f"TRAVEL_STYL_{i}" for i in range(1, 8)]
    
    # 해당 컬럼들을 데이터프레임에서 삭제 (없는 컬럼이 있더라도 오류 발생 방지)
    df.drop(columns=style_columns_to_drop, inplace=True, errors='ignore')

    # 정리된 표의 인덱스를 재정렬하고 결과를 반환합니다.
    return df.reset_index(drop=True)


def preprocess_visit_area_info(
    dataset_key="방문지정보",
    exclude_codes=(21, 22, 23),
    drop_columns=None,
    return_base_table=False,
):
    """
    방문지 정보 테이블에서 여행 단위의 요약 통계를 생성합니다.
    - 제외 코드에 해당하는 방문지를 제외하고, 각 방문지의 실패 여부를 계산합니다.
    - 실패한 방문지 비율이 50% 이상인 여행을 '실패한 여행'으로 정의합니다.
    """
    # 1. 원본 데이터 로드 및 기본 전처리
    df = load_dataset(dataset_key).copy()
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

    # 각 만족도 항목이 3점 이하인지 여부를 boolean(True/False) 값으로 계산합니다.
    # (True는 1, False는 0으로 취급됩니다.)
    low_dgstfn = (df['DGSTFN'] <= 3)
    low_revisit = (df['REVISIT_INTENTION'] <= 3)
    low_rcmdtn = (df['RCMDTN_INTENTION'] <= 3)

    # 위 세 boolean 값을 더하면, 3점 이하인 항목의 개수가 됩니다.
    # 그 합이 2 이상이면 '실패한 방문지' 조건에 해당합니다.
    fail_visit_condition = (low_dgstfn + low_revisit + low_rcmdtn) >= 2
    
    df['IS_FAILED_VISIT'] = np.where(fail_visit_condition, 1, 0)

    # VISIT_AREA_TYPE_CD가 exclude_codes에 해당하는 경우는 계산에서 제외합니다.
    if "VISIT_AREA_TYPE_CD" in df.columns:
        df.loc[df['VISIT_AREA_TYPE_CD'].isin(set(exclude_codes)), 'IS_FAILED_VISIT'] = np.nan

    # 2. 여행 단위(TRAVEL_ID)로 통계 집계
    parts = []
    filtered = df[~df["VISIT_AREA_TYPE_CD"].isin(set(exclude_codes))].copy()
    if not filtered.empty:
        parts.append(filtered.groupby("TRAVEL_ID")["DGSTFN"].mean().rename("DGSTFN_AVG"))
        parts.append(filtered.groupby("TRAVEL_ID")["REVISIT_INTENTION"].mean().rename("REVISIT_AVG"))
        parts.append(filtered.groupby("TRAVEL_ID")["RCMDTN_INTENTION"].mean().rename("RCMDTN_AVG"))

    failed_ratio = df.groupby('TRAVEL_ID')['IS_FAILED_VISIT'].mean().rename('FAILED_VISIT_RATIO')
    parts.append(failed_ratio)

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

    aggregated = pd.concat(parts, axis=1).reset_index()
    aggregated['FAILED_VISIT_RATIO'] = aggregated['FAILED_VISIT_RATIO'].fillna(0)

    # (ii 조건) 최종 여행 실패/성공 여부 컬럼 생성
    aggregated['IS_FAILED_TRIP'] = np.where(aggregated['FAILED_VISIT_RATIO'] >= 0.5, 1, 0)

    # 최종 결과에는 중간 계산 과정 컬럼을 제외합니다.
    aggregated = aggregated.drop(columns=['FAILED_VISIT_RATIO'])

    if return_base_table:
        return df.drop(columns=['IS_FAILED_VISIT']).reset_index(drop=True), aggregated

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
        json_dir = os.path.join(folder, "json")
        os.makedirs(json_dir, exist_ok=True)
        encoder_path = os.path.join(json_dir, "travel_status_accompany_encoding.json")
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
        
    # MVMN_NM 컬럼이 존재하면, 결측치(NaN)를 "정보없음" 텍스트로 채웁니다.
    if "MVMN_NM" in df.columns:
        df["MVMN_NM"] = df["MVMN_NM"].fillna("정보없음")
    
    # TRAVEL_NM 컬럼 삭제
    if "TRAVEL_NM" in df.columns:
        df = df.drop(columns=["TRAVEL_NM"], errors="ignore")

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
