import streamlit as st
import pandas as pd
import numpy as np
import joblib
import time
import os

# ------------------------------
# Lite Model 
# ------------------------------
MODEL_PATH = "models/catboost_best_model_lite.joblib"

# 모델 입력 피처
LITE_FEATURES = [
    "TRIP_DAYS",
    "GENDER",
    "AGE_GRP",
    "ACTIVITY_TYPE_CD",
]

# 활동유형 매핑
ACT_LABEL_TO_CODE = {
    "취식": "1",
    "쇼핑": "2",
    "쇼핑/구매": "2",
    "체험": "3",
    "체험 활동": "3",
    "입장": "3",
    "관람": "3",
    "산책": "4",
    "단순 구경": "4",
    "걷기": "4",
    "휴식": "5",
    "기타": "6",
    "이동": "7",  # 환승/경유 의미
    "환승": "7",
    "경유": "7",
    "없음": "99",
}

@st.cache_resource
def get_model():
    
    if not os.path.exists(MODEL_PATH):
        st.info(" 모델 파일이 없어 가데이터 예측 결과 사용")
        return None
    
    try:
        return joblib.load(MODEL_PATH)
    except Exception as e:
        st.warning(f"모델 로드 실패: {e}")
        return None

def normalize_gender(v) -> int:
    """성별을 1(남)/2(여)로 변환"""
    if v is None:
        return 1
    v = str(v).strip().lower()
    mapping = {"m": 1, "남": 1, "남자": 1, "male": 1,
               "f": 2, "여": 2, "여자": 2, "female": 2}
    return mapping.get(v, 1)

def normalize_age_grp(v) -> int:
    """나이대: '30대' → 30, '30' → 30"""
    if v is None:
        return 30
    v = str(v)
    digits = "".join(ch for ch in v if ch.isdigit())
    return int(digits) if digits else 30

def normalize_activity_type(v) -> str:
    """활동유형 라벨 → 코드 변환"""
    if v is None:
        return "99"
    v = str(v).strip()
    if v in ACT_LABEL_TO_CODE:
        return ACT_LABEL_TO_CODE[v]
    vv = v.replace(" ", "").replace("/", "")
    for k, code in ACT_LABEL_TO_CODE.items():
        if vv == k.replace(" ", "").replace("/", ""):
            return code
    if v.isdigit():
        return v
    if (len(v) >= 2) and (v[0] in ("A", "a")) and v[1:].isdigit():
        return str(int(v[1:]))
    return "99"

def build_input_df(trip_days, gender, age_grp, activity_type_cd):
    """사용자 입력값 → 모델 입력 DataFrame 생성"""
    row = {
        "TRIP_DAYS": float(trip_days),
        "GENDER": normalize_gender(gender),
        "AGE_GRP": normalize_age_grp(age_grp),
        "ACTIVITY_TYPE_CD": normalize_activity_type(activity_type_cd),
    }
    return pd.DataFrame([row], columns=LITE_FEATURES)

def predict_failure(model, X, threshold=0.5):
    """예측 확률 및 라벨 반환"""
    proba = float(model.predict_proba(X)[:, 1][0])
    return proba, int(proba >= threshold)