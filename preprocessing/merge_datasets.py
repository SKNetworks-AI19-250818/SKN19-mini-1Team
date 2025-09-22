import os

import pandas as pd

import json
from collections import Counter


def get_project_root():
    # 현재 파일이 있는 폴더에서 한 단계 위로 올라가 프로젝트 루트를 찾는다.
    here = os.path.dirname(__file__)
    # 절대 경로로 변환해 어느 위치에서 실행해도 같은 폴더를 가리키게 한다.
    return os.path.abspath(os.path.join(here, ".."))


def get_preprocessed_dir():
    # 프로젝트 루트 아래 data/training/preprocessing 경로를 조합한다.
    root = get_project_root()
    return os.path.join(root, "data", "training", "preprocessing")


def read_preprocessed_csv(filename):
    # 전처리 결과가 저장된 폴더 위치를 구한다.
    folder = get_preprocessed_dir()
    path = os.path.join(folder, filename)
    # 파일이 없다면 바로 알려주어 후속 과정에서 헛수고하지 않도록 한다.
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing preprocessed file: {path}")
    # pandas가 CSV를 읽어 데이터프레임으로 만들어 준다.
    return pd.read_csv(path)


def aggregate_activity_consumption(df):
    columns = ["TRAVEL_ID", "activity_payment_sum", "activity_payment_count", "activity_store_count"]
    if df.empty:
        # 입력 데이터가 비어 있으면 같은 형태의 빈 표를 반환해 후속 로직을 단순화한다.
        return pd.DataFrame(columns=columns)

    df = df.copy()
    # 계산을 위해 결제 금액을 숫자로 바꾸고 잘못된 값은 0으로 채운다.
    df["PAYMENT_AMT_WON"] = pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)

    # 여행별 결제 금액 합계, 결제 건수, 방문한 상점 수를 각각 계산한다.
    total = df.groupby("TRAVEL_ID")["PAYMENT_AMT_WON"].sum().rename("activity_payment_sum")
    count = df.groupby("TRAVEL_ID").size().rename("activity_payment_count")
    stores = df.groupby("TRAVEL_ID")["STORE_NM"].nunique().rename("activity_store_count")

    # 계산한 시리즈들을 하나의 표로 합친다.
    merged = pd.concat([total, count, stores], axis=1).reset_index()
    for column in columns[1:]:
        # 결측치는 0으로 채워 통계 계산 과정에서 문제가 생기지 않도록 한다.
        if column in merged.columns:
            merged[column] = merged[column].fillna(0)
    if "activity_payment_sum" in merged.columns:
        # 금액 합계는 반올림 후 정수로 변환해 사람이 읽기 쉽게 만든다.
        merged["activity_payment_sum"] = (
            merged["activity_payment_sum"].round().astype(int)
        )
    return merged


def aggregate_activity_history(df):
    if df.empty:
        # 빈 입력이 들어오면 동일한 컬럼 구조의 빈 결과를 돌려준다.
        return pd.DataFrame(columns=["TRAVEL_ID", "activity_history_rows", "activity_type_unique"])

    # 여행별로 활동 기록의 행 수와 고유한 활동 유형 개수를 센다.
    counts = df.groupby("TRAVEL_ID").size().rename("activity_history_rows")
    unique_types = df.groupby("TRAVEL_ID")["ACTIVITY_TYPE_CD"].nunique().rename("activity_type_unique")

    merged = pd.concat([counts, unique_types], axis=1).reset_index()
    return merged


def aggregate_lodging(df):
    columns = ["TRAVEL_ID", "lodging_payment_sum", "lodging_payment_count", "lodging_store_count"]
    if df.empty:
        # 숙박 결제 데이터가 없으면 같은 모양의 빈 결과를 돌려 후속 과정에서 예외를 막는다.
        return pd.DataFrame(columns=columns)

    df = df.copy()
    # 숫자가 아닌 값은 0으로 바꾸고 합계를 얻기 위한 준비를 한다.
    df["PAYMENT_AMT_WON"] = pd.to_numeric(df["PAYMENT_AMT_WON"], errors="coerce").fillna(0)

    total = df.groupby("TRAVEL_ID")["PAYMENT_AMT_WON"].sum().rename("lodging_payment_sum")
    count = df.groupby("TRAVEL_ID").size().rename("lodging_payment_count")
    stores = df.groupby("TRAVEL_ID")["STORE_NM"].nunique().rename("lodging_store_count")

    merged = pd.concat([total, count, stores], axis=1).reset_index()
    for column in columns[1:]:
        # 결측값은 0으로 채워 계산 과정에서 NaN이 퍼지지 않게 한다.
        if column in merged.columns:
            merged[column] = merged[column].fillna(0)
    if "lodging_payment_sum" in merged.columns:
        # 금액 합계를 반올림한 뒤 정수형으로 변환한다.
        merged["lodging_payment_sum"] = (
            merged["lodging_payment_sum"].round().astype(int)
        )
    return merged


def prepare_visit_summary(df):
    if df.empty:
        # 방문 요약 데이터가 없으면 필요한 컬럼 이름만 유지한 빈 표를 반환한다.
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

    # 분석에서 쓰기 쉬운 이름으로 컬럼을 바꿔 준다.
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
    # 전처리 이전 데이터 위치 정보를 담은 JSON 파일을 읽어 온다.
    here = os.path.dirname(__file__)
    json_path = os.path.join(here, "file_dir.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Cannot find mapping file: {json_path}")
    with open(json_path, encoding="utf-8") as handle:
        data = json.load(handle)

    # 상대 경로를 프로젝트 루트 기준의 절대 경로로 바꿔 저장한다.
    file_map = {}
    root = get_project_root()
    for key, rel_path in data.items():
        file_map[key] = os.path.join(root, rel_path)
    return file_map


def load_travel_table():
    # 이미 저장된 전처리 결과가 있으면 그 파일을 사용한다.
    preprocessed_path = os.path.join(get_preprocessed_dir(), "travel.csv")
    if os.path.exists(preprocessed_path):
        return pd.read_csv(preprocessed_path)

    # 없으면 원본 데이터를 찾아 TRAVEL_MISSION 컬럼을 제거한 뒤 돌려준다.
    file_map = load_file_map()
    if "?�행" not in file_map:
        raise KeyError("'?�행' key is missing from file_dir.json")
    travel_path = file_map["?�행"]
    return pd.read_csv(travel_path).drop(columns=["TRAVEL_MISSION"], errors="ignore")


def _extract_codes(value, delimiter=";"):
    # 값이 비어 있으면 빈 리스트를 반환해 이후 로직이 단순해지도록 한다.
    if pd.isna(value):
        return []
    codes = []
    # 구분자를 기준으로 나누고 앞뒤 공백을 제거한다.
    for part in str(value).split(delimiter):
        code = part.strip()
        if code:
            codes.append(code)
    return codes


def expand_multi_value_column(df, column, prefix, delimiter=";", top_n=10):
    if column not in df.columns:
        # 기대한 컬럼이 없으면 원본 데이터를 그대로 돌려준다.
        return df

    # 각 행에서 코드 목록을 뽑아낸다.
    code_lists = df[column].apply(lambda x: _extract_codes(x, delimiter))
    counter = Counter()
    for codes in code_lists:
        counter.update(codes)

    # 가장 많이 등장한 코드 top_n개만 따로 열로 만들어 준다.
    top_codes = [code for code, _ in counter.most_common(top_n)]

    for code in top_codes:
        col_name = f"{prefix}{code}"
        # 해당 코드가 존재하면 1, 없으면 0을 기록한다.
        df[col_name] = code_lists.apply(lambda codes: int(code in codes))

    # top_n에 포함되지 않은 코드가 하나라도 있으면 OTHER 플래그를 1로 세운다.
    df[f"{prefix}OTHER"] = code_lists.apply(
        lambda codes: int(any(code not in top_codes for code in codes)) if codes else 0
    )
    # 한 행에서 등장한 코드 개수를 기록해 추후 분석에 활용한다.
    df[f"{prefix}COUNT"] = code_lists.apply(len)

    return df


def expand_travel_categorical_codes(travel_df):
    # 여행 목적과 미션 체크처럼 여러 값이 들어 있는 문자열을 개별 열로 확장한다.
    travel_df = expand_multi_value_column(travel_df, "TRAVEL_PURPOSE", "TRAVEL_PURPOSE_", ";")

    travel_df = expand_multi_value_column(
        travel_df,
        "TRAVEL_MISSION_CHECK",
        "TRAVEL_MISSION_CHECK_",
        ";",
        top_n=10,
    )

    # 확장 과정에서 값이 비어도 오류가 나지 않도록 기본값 0을 채워 둔다.
    travel_df["TRAVEL_PURPOSE_COUNT"] = travel_df.get("TRAVEL_PURPOSE_COUNT", 0)
    travel_df["TRAVEL_PURPOSE_OTHER"] = travel_df.get("TRAVEL_PURPOSE_OTHER", 0)

    return travel_df


def build_final_dataset():
    # 미리 전처리해 둔 CSV 파일들을 모두 불러온다.
    activity_consumption = read_preprocessed_csv("activity_consumption.csv")
    activity_history = read_preprocessed_csv("activity_history.csv")
    lodging = read_preprocessed_csv("lodging_consumption.csv")
    traveller_master = read_preprocessed_csv("traveller_master.csv")
    visit_summary = read_preprocessed_csv("visit_area_summary.csv")

    # 각 테이블에서 여행 단위로 필요한 요약 통계를 만든다.
    activity_consume_summary = aggregate_activity_consumption(activity_consumption)
    activity_history_summary = aggregate_activity_history(activity_history)
    lodging_summary = aggregate_lodging(lodging)
    visit_summary_ready = prepare_visit_summary(visit_summary)

    # 여행 기본 정보에 파생된 통계를 차례대로 붙인다.
    travel_table = load_travel_table()
    travel_table = expand_travel_categorical_codes(travel_table)

    travel_features = travel_table.copy()
    travel_features = travel_features.merge(activity_consume_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(activity_history_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(lodging_summary, on="TRAVEL_ID", how="left")
    travel_features = travel_features.merge(visit_summary_ready, on="TRAVEL_ID", how="left")

    # 숫자형 컬럼은 기본값을 0으로 채워 연산에서 NaN이 생기지 않도록 한다.
    # PLAN: swap this blanket zero fill for persona/purpose medians pulled from
    # data/training/TL_csv source tables via preprocessing/preprocessing.py helpers.
    # e.g., use activity/lodging aggregations to impute missing rows with ~9.7e4 activity sum,
    # 4 activity count, 8 history rows, and ~1.2e5 lodging sum per TRAVEL_PERSONA before falling back to 0.
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

    # 건수 관련 컬럼은 정수형으로 맞춰 분석 시 의미가 잘 전달되도록 한다.
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

    # 금액 합계는 반올림 후 정수형으로 통일한다.
    sum_columns = [
        "activity_payment_sum",
        "lodging_payment_sum",
    ]
    for column in sum_columns:
        if column in travel_features.columns:
            travel_features[column] = travel_features[column].round().astype(int)

    # 마지막으로 여행자 기본 정보와 조인해 최종 데이터를 완성한다.
    final_df = travel_features.merge(traveller_master, on="TRAVELER_ID", how="left")
    return final_df


def save_final_dataset():
    # 최종 데이터프레임을 만들고 전처리 폴더에 CSV로 저장한다.
    df = build_final_dataset()
    output_dir = get_preprocessed_dir()
    output_path = os.path.join(output_dir, "final_traveler.csv")
    df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    # 스크립트를 직접 실행하면 저장 경로를 확인할 수 있다.
    path = save_final_dataset()
    print(f"Saved merged dataset to {path}")
