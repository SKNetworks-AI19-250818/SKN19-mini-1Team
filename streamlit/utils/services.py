import streamlit as st
import pandas as pd
import numpy as np
import pathlib
import joblib
import time
import os

# ------------------------------
# Catboost Lite Model 
# ------------------------------
# lite_v1
LITE_FEATURES = [
    "TRIP_DAYS",
    "GENDER",
    "AGE_GRP",
    "ACTIVITY_TYPE_CD",
]

# lite_v2 
LITE_FEATURES_V2 = [
    "TRIP_DAYS",
    "GENDER",
    "AGE_GRP",
    "ACTIVITY_TYPE_CD",
    "payment_persona",
    "TRAVEL_STATUS_ACCOMPANY",  # UI 미노출, '정보없음' 고정
    "TRAVEL_COMPANIONS_NUM",
    "SEASON",
]

# 모델 버전별 입력 피처 매핑
MODEL_FEATURES = {
    "model_v1": LITE_FEATURES,
    "model_v2": LITE_FEATURES_V2,
}

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
def get_model(path):
    try:
        model = joblib.load(path)
        return model
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

def normalize_payment_persona(v: str) -> str:
    """payment_persona 정규화"""
    if v is None:
        return "med"
    m = {
        "low": "low", "낮음": "low", "하": "low", "lo": "low",
        "medium": "med", "med": "med", "중간": "med", "중": "med",
        "high": "high", "높음": "high", "상": "high", "hi": "high",
        "높": "high", "낮": "low",
    }
    key = str(v).strip().lower()
    return m.get(key, "med")

def normalize_companions_num(v) -> int:
    """동반인원 정규화"""
    try:
        n = int(float(str(v).strip()))
        return max(0, n)
    except Exception:
        return 0
    
def normalize_season(v: str) -> str:
    """시즌 정규화"""
    if v is None:
        return "봄"
    key = str(v).strip().lower()
    m = {
        "spring": "봄", "summer": "여름", "fall": "가을", "autumn": "가을", "winter": "겨울",
        "1": "봄", "2": "여름", "3": "가을", "4": "겨울",
        "봄": "봄", "여름": "여름", "가을": "가을", "겨울": "겨울",
    }
    return m.get(key, "봄")

def build_input_df_dynamic(features: list, **kwargs):
    row = {}
    # 공통
    if "TRIP_DAYS" in features:
        row["TRIP_DAYS"] = float(kwargs.get("trip_days", 1))
    if "GENDER" in features:
        row["GENDER"] = normalize_gender(kwargs.get("gender"))
    if "AGE_GRP" in features:
        row["AGE_GRP"] = normalize_age_grp(kwargs.get("age_grp"))
    if "ACTIVITY_TYPE_CD" in features:
        row["ACTIVITY_TYPE_CD"] = normalize_activity_type(kwargs.get("activity_type_cd"))
    # v2 전용
    if "payment_persona" in features:
        row["payment_persona"] = normalize_payment_persona(kwargs.get("payment_persona"))
    if "TRAVEL_STATUS_ACCOMPANY" in features:
        row["TRAVEL_STATUS_ACCOMPANY"] = "정보없음"  # UI 미노출 고정 값
    if "TRAVEL_COMPANIONS_NUM" in features:
        row["TRAVEL_COMPANIONS_NUM"] = normalize_companions_num(kwargs.get("companions_num"))
    if "SEASON" in features:
        row["SEASON"] = normalize_season(kwargs.get("season"))

    return pd.DataFrame([row], columns=features)