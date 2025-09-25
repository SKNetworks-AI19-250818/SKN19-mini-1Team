import pandas as pd
import numpy as np
import pickle
from typing import Dict, List, Any, Optional
import os
import json
from sklearn.preprocessing import StandardScaler


class ObjectLabelEncoder:
    """
    초보자용 설명: 문자열(object) 타입 컬럼을 숫자(라벨)로 바꿔주는 간단한 도구입니다.

    핵심 아이디어
    - 학습(Fit) 단계에서 각 컬럼의 고유한 문자열 값들을 모아, "문자열 → 정수" 사전을 만듭니다.
    - 변환(Transform) 단계에서 사전에 따라 값을 정수로 바꿉니다.
    - 결측값(NaN)은 특별 토큰("__NaN__")으로, 처음 보는 값은 "__UNK__"(Unknown)으로 처리합니다.

    왜 필요한가요?
    - 많은 머신러닝 모델은 숫자만 입력으로 받습니다. 문자열을 숫자로 바꾸면 모델이 학습할 수 있습니다.

    사용 예시
    >>> enc = ObjectLabelEncoder(exclude_cols=["ID"])  # ID 같은 컬럼은 제외 가능
    >>> enc.fit(df)                                     # 사전 만들기
    >>> df_num = enc.transform(df)                      # 숫자로 변환
    >>> enc.save("encoder.pkl")                         # 나중에 동일 규칙을 쓰고 싶다면 저장
    """
    def __init__(
        self,
        include_cols: Optional[List[str]] = None,   # 지정 시 여기에만 적용
        exclude_cols: Optional[List[str]] = None,   # 제외할 컬럼
        sort_categories: bool = True,               # 카테고리 정렬 여부(재현성 보장)
        add_unknown_token: bool = True,             # __UNK__ 추가
        add_nan_token: bool = True,                 # __NaN__ 추가
        reserve_id_order: bool = True               # 토큰 순서 고정(재현성)
    ):
        self.include_cols = set(include_cols) if include_cols else None
        self.exclude_cols = set(exclude_cols) if exclude_cols else set()
        self.sort_categories = sort_categories
        self.add_unknown_token = add_unknown_token
        self.add_nan_token = add_nan_token
        self.reserve_id_order = reserve_id_order

        self.col2map_: Dict[str, Dict[str, int]] = {}
        self.col2inv_: Dict[str, Dict[int, str]] = {}
        self.object_cols_: List[str] = []
        self.fitted_: bool = False

        # 특수 토큰
        self.NAN_TOK = "__NaN__"
        self.UNK_TOK = "__UNK__"

    def _select_object_cols(self, df: pd.DataFrame) -> List[str]:
        """DataFrame에서 문자열(object) 타입 컬럼만 골라냅니다.

        - include_cols가 주어지면 그 컬럼들만 대상
        - exclude_cols가 주어지면 그 컬럼들은 제외
        """
        obj_cols = df.select_dtypes(include=["object"]).columns.tolist()
        if self.include_cols is not None:
            obj_cols = [c for c in obj_cols if c in self.include_cols]
        if self.exclude_cols:
            obj_cols = [c for c in obj_cols if c not in self.exclude_cols]
        return obj_cols

    def _build_mapping(self, series: pd.Series) -> Dict[str, int]:
        """하나의 컬럼(Series)에 대해 "문자열 → 정수" 매핑 사전을 만듭니다.

        구현 포인트(쉬운 버전)
        1) 결측치는 우선 제외하고, 실제 값들만 문자열로 변환해 고유값을 모읍니다.
        2) 원한다면 알파벳/숫자 순으로 정렬해 재현성을 보장합니다.
        3) 특별 토큰을 추가합니다: 맨 앞에 "__NaN__", 맨 뒤에 "__UNK__".
        4) 앞에서부터 0,1,2,... 순으로 번호를 붙입니다.
        """
        # 1) 결측치 제외 + 문자열로 통일
        non_na = series.dropna().astype(str)
        uniq_values = pd.Index(non_na.unique())

        # 2) 정렬(옵션)
        if self.sort_categories:
            uniq_values = pd.Index(sorted(uniq_values))

        # 3) 특별 토큰 추가
        cats: List[str] = list(uniq_values)
        if self.add_nan_token and self.NAN_TOK not in cats:
            cats.insert(0, self.NAN_TOK)  # 맨 앞에 NaN 토큰
        if self.add_unknown_token and self.UNK_TOK not in cats:
            cats.append(self.UNK_TOK)     # 맨 뒤에 Unk 토큰

        # 4) 정수 id 부여 (0부터 시작)
        mapping = {cat: i for i, cat in enumerate(cats)}
        return mapping

    def fit(self, df: pd.DataFrame):
        """학습 단계: 각 문자열 컬럼에 대한 매핑 사전을 만듭니다."""
        self.object_cols_ = self._select_object_cols(df)
        self.col2map_.clear()
        self.col2inv_.clear()

        for col in self.object_cols_:
            mapping = self._build_mapping(df[col])
            self.col2map_[col] = mapping
            # 역매핑(정수 → 문자열)도 같이 준비해 둡니다.
            self.col2inv_[col] = {i: k for k, i in mapping.items()}

        self.fitted_ = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """변환 단계: 학습 때 만든 규칙으로 문자열을 정수(라벨)로 바꿉니다.

        주의: 반드시 fit()이 먼저 호출되어야 합니다.
        """
        assert self.fitted_, "Call fit() before transform()."
        out = df.copy()
        for col in self.object_cols_:
            mapping = self.col2map_[col]

            # 1) 우선 문자열로 변환 (숫자 등도 안전하게 처리)
            s = out[col].astype(str)

            # 2) 결측치는 특별 토큰으로 대체
            if self.add_nan_token:
                s = s.where(~out[col].isna(), self.NAN_TOK)

            # 3) 매핑 적용: 사전에 없는 값은 NaN이 됩니다.
            mapped = s.map(mapping)

            # 4) 모르는 값(Unknown) 처리: __UNK__ id로 채우기 (옵션)
            if self.add_unknown_token and self.UNK_TOK in mapping:
                unk_id = mapping[self.UNK_TOK]
                mapped = mapped.fillna(unk_id)

            # 5) 정수형으로 저장 (결측 고려: pandas의 nullable 정수 Int32 사용)
            out[col] = mapped.astype("Int32")

        return out

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """fit() + transform()을 한 번에 실행합니다."""
        return self.fit(df).transform(df)

    def inverse_transform(self, df: pd.DataFrame, cols: Optional[List[str]] = None) -> pd.DataFrame:
        """정수로 바뀐 값을 다시 원래 문자열로 되돌립니다."""
        assert self.fitted_, "Call fit() before inverse_transform()."
        cols = cols or self.object_cols_
        out = df.copy()
        for col in cols:
            inv = self.col2inv_[col]
            out[col] = out[col].map(inv).astype("object")
        return out

    def save(self, path: str):
        """현재 인코더 상태를 파일로 저장합니다 (pickle)."""
        payload = {
            "include_cols": list(self.include_cols) if self.include_cols else None,
            "exclude_cols": list(self.exclude_cols) if self.exclude_cols else [],
            "sort_categories": self.sort_categories,
            "add_unknown_token": self.add_unknown_token,
            "add_nan_token": self.add_nan_token,
            "reserve_id_order": self.reserve_id_order,
            "col2map_": self.col2map_,
            "object_cols_": self.object_cols_,
            "NAN_TOK": self.NAN_TOK,
            "UNK_TOK": self.UNK_TOK,
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load(cls, path: str) -> "ObjectLabelEncoder":
        """저장한 인코더를 불러옵니다."""
        with open(path, "rb") as f:
            payload = pickle.load(f)
        enc = cls(
            include_cols=payload["include_cols"],
            exclude_cols=payload["exclude_cols"],
            sort_categories=payload["sort_categories"],
            add_unknown_token=payload["add_unknown_token"],
            add_nan_token=payload["add_nan_token"],
            reserve_id_order=payload["reserve_id_order"],
        )
        enc.col2map_ = payload["col2map_"]
        enc.object_cols_ = payload["object_cols_"]
        enc.col2inv_ = {c: {i: k for k, i in enc.col2map_[c].items()} for c in enc.object_cols_}
        enc.NAN_TOK = payload["NAN_TOK"]
        enc.UNK_TOK = payload["UNK_TOK"]
        enc.fitted_ = True
        return enc


def run_ml_preprocessing(mode: str):
    """
    Runs the ML preprocessing pipeline based on encoding.md rules.
    Reads 'travel_insight.csv', applies transformations, and saves 'travel_ml.csv'.
    
    :param mode: 'train' or 'validation'
    """
    mode_to_dir = {
        "train": "training",
        "validation": "validation"
    }
    mode_dir_name = mode_to_dir[mode]
    
    input_path = f'data/{mode_dir_name}/final/travel_insight.csv'
    output_dir = f'data/{mode_dir_name}/final/'
    output_path = os.path.join(output_dir, 'travel_ml.csv')

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(input_path)

    # 1. Date Feature Engineering
    df['TRAVEL_START_YMD'] = pd.to_datetime(df['TRAVEL_START_YMD'], errors='coerce')
    df['TRAVEL_END_YMD'] = pd.to_datetime(df['TRAVEL_END_YMD'], errors='coerce')
    
    df['TRAVEL_START_YEAR'] = df['TRAVEL_START_YMD'].dt.year
    df['TRAVEL_START_MONTH'] = df['TRAVEL_START_YMD'].dt.month
    df['TRAVEL_END_YEAR'] = df['TRAVEL_END_YMD'].dt.year
    df['TRAVEL_END_MONTH'] = df['TRAVEL_END_YMD'].dt.month

    # 2. Label Encoding
    cols_to_encode = [
        'TRAVEL_STATUS_ACCOMPANY',
        'MVMN_NM',
        'GENDER',
    ]

    # The following loop performs label encoding on categorical columns.
    # A new column with the suffix '_CODE' is created for each.
    # The mapping is sorted alphabetically for reproducibility.
    #
    # Below are the expected mappings based on the data:
    #
    # TRAVEL_STATUS_ACCOMPANY:
    # {
    #     '__NaN__': 0,
    #     '2인 가족 여행': 1,
    #     '2인 여행(가족 외)': 2,
    #     '3대 동반 여행(친척 포함)': 3,
    #     '3인 이상 여행(가족 외)': 4,
    #     '나홀로 여행': 5,
    #     '부모 동반 여행': 6,
    #     '자녀 동반 여행': 7,
    #     '__UNK__': 8
    # }
    #
    # MVMN_NM:
    # {
    #     '__NaN__': 0,
    #     '대중교통 등': 1,
    #     '자가용': 2,
    #     '정보없음': 3,
    #     '__UNK__': 4
    # }
    #
    # GENDER:
    # {
    #     '__NaN__': 0,
    #     '남': 1,
    #     '여': 2,
    #     '__UNK__': 3
    # }
    for col in cols_to_encode:
        encoder = ObjectLabelEncoder(include_cols=[col])
        df[f'{col}_CODE'] = encoder.fit_transform(df[[col]])[col]

    # 3. SIDO Code Encoding from tc_sgg_시군구코드.json
    with open('data/tag_code/training/json/tc_sgg_시군구코드.json', 'r', encoding='utf-8') as f:
        sgg_data = json.load(f)

    # Create a mapping from SIDO_NM to SGG_CD1
    sido_to_code = {
        item['SIDO_NM']: item['SGG_CD1'] 
        for item in sgg_data 
        if item.get('SIDO_NM') and item.get('SGG_NM') is None
    }

    # Abbreviation mapping from encoding.md and data observation
    abbr_map = {
        '경남': '경상남도',
        '경북': '경상북도',
        '충남': '충청남도',
        '충북': '충청북도',
        '전남': '전라남도',
        '전북': '전라북도',
        '제주': '제주특별자치도',
        '제주도': '제주특별자치도',
        '서울': '서울특별시',
        '경기': '경기도',
        '인천': '인천광역시',
        '부산': '부산광역시',
        '대구': '대구광역시',
        '광주': '광주광역시',
        '대전': '대전광역시',
        '울산': '울산광역시',
        '세종': '세종특별자치시',
        '강원': '강원도',
        '도서 지역': '도서지역',
        '도서지역' : '도서지역'
    }

    for col in ['TRAVEL_STATUS_RESIDENCE', 'TRAVEL_STATUS_DESTINATION']:
        # Normalize names using abbreviation map
        df[col] = df[col].replace(abbr_map)

        # Create new column with SGG_CD1 code
        # This will overwrite the existing _CODE columns with the new mapping
        df[f'{col}_CODE'] = df[col].map(sido_to_code)

        # Special rule: if residence/destination is '도서지역', set its code to 0
        # (island area handling per requirement)
        mask_island = df[col].astype(str).str.strip() == '도서지역'
        df.loc[mask_island, f'{col}_CODE'] = 0

    # 4. Scaling Numerical Features
    cols_to_scale = [
        'activity_payment_sum', 'activity_payment_count', 'activity_store_count',
        'activity_history_rows', 'activity_type_unique', 'lodging_payment_sum',
        'lodging_payment_count', 'lodging_store_count', 'visit_dgstfn_avg',
        'visit_revisit_avg', 'visit_rcmdtn_avg', 'visit_trip_days',
        'visit_move_cnt', 'AGE_GRP', 'FAMILY_MEMB', 'INCOME', 'HOUSE_INCOME',
        'TRAVEL_TERM', 'TRAVEL_NUM', 'TRAVEL_COMPANIONS_NUM'
    ]

    scaler = StandardScaler()

    for col in cols_to_scale:
        # Fill NaN with the median before scaling
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val)
        
        # Reshape data for scaler and apply scaling
        scaled_data = scaler.fit_transform(df[[col]])
        
        # Create new scaled column
        df[f'{col}_SCALED'] = scaled_data

    # Save the preprocessed dataframe
    df.to_csv(output_path, index=False)
    
    return output_path


if __name__ == "__main__":
    # This allows running the script directly for ML preprocessing
    print("Running ML preprocessing for validation set...")
    saved_path = run_ml_preprocessing(mode='validation')
    print(f"Successfully preprocessed validation data saved to: {saved_path}")

    print("Running ML preprocessing for training set...")
    saved_path = run_ml_preprocessing(mode='train')
    print(f"Successfully preprocessed training data saved to: {saved_path}")
