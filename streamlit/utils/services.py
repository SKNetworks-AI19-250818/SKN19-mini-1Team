import streamlit as st
import pandas as pd
import numpy as np
import joblib
import time
import os

# ------------------------------
# 모델 및 피처 스키마
# ------------------------------
MODEL_PATH = "models/final_model.pkl"
FEATURE_SCHEMA = {
    "companion": "category",
    "people": "int",
    "days": "int",
    "lodging": "category",
    "moves": "int",
    "budget": "float"
}
FEATURE_ORDER = list(FEATURE_SCHEMA.keys())

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
        
model = get_model()

def predict_failure_proba(user_inputs: dict) -> float:

    df = pd.DataFrame([user_inputs])

    for col, dtype in FEATURE_SCHEMA.items():
        df[col] = df[col].astype(dtype if dtype != "category" else "category")
    
    X = df[FEATURE_ORDER]

    if model:
        try:
            return model.predict_proba(X)[0, 1]
        except Exception as e:
            st.warning(f"모델 예측 실패: {e}")

    # 가데이터
    base_prob = 0.3
    base_prob += min(user_inputs["days"] * 0.02, 0.3)
    base_prob += min(user_inputs["moves"] * 0.03, 0.2)
    base_prob -= min((user_inputs["people"] - 1) * 0.02, 0.15)

    if user_inputs["budget"] < 10:
        base_prob += 0.1

    elif user_inputs["budget"] > 500:
        base_prob += 0.05

    if user_inputs["companion"] == "연인":
        base_prob += 0.05

    elif user_inputs["companion"] == "회사":
        base_prob += 0.03
        
    elif user_inputs["companion"] == "가족":
        base_prob -= 0.05
        
    import hashlib
    # 입력 딕셔너리를 정렬해 문자열로 만들고 32비트 시드 생성
    key = repr(sorted(user_inputs.items())).encode("utf-8")
    seed = int.from_bytes(hashlib.blake2b(key, digest_size=4).digest(), "big")  # 0 ~ 2**32-1

    # 전역 시드 대신 독립 RNG 사용
    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-0.05, 0.05)

    return float(np.clip(base_prob + jitter, 0.0, 1.0))