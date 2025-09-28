import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pathlib
import joblib
import time
import os
#------------------------------
# 커스텀 모듈
#------------------------------
from utils.loader import load_css, img_to_base64, render_clouds, render_image, audio_to_base64, insert_background_audio
from utils.services import *
BASE_DIR = pathlib.Path(__file__).resolve().parent
STYLE_DIR = BASE_DIR / "style"
ASSETS_DIR = BASE_DIR / "assets" / "img"
AUDIO_DIR = BASE_DIR / "assets" / "audio"

#------------------------------
# 기본 설정 & 예측 모델
#------------------------------
st.set_page_config(page_title="One Trip, Two Fates", page_icon="✈️", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "intro"
if "result" not in st.session_state:
    st.session_state.result = None

#------------------------------
# 인트로 페이지
#------------------------------
def intro_page():

    load_css(str(STYLE_DIR / "intro.css"))
    render_clouds(str(ASSETS_DIR / "cloudy.png"), count=5, top_range=(5, 80), size_range=(120, 240))

    # OTTF 배경음악 
    # audio_url = audio_to_base64(str(AUDIO_DIR/"OTTF_INTRO_V2.wav"))    
    # insert_background_audio(audio_url)

    st.audio(str(AUDIO_DIR/"OTTF_INTRO_V2.wav"), format="audio/mp3", start_time=0)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <h2 class='intro-title'>ONE TRIP, TWO FATES</h2>
        <p class='intro-subtext'>
            당신의 여행, 과연 <span class="happy-highlight">해피엔딩 🎉</span>일까요<br>
            아니면 <span class="fail-highlight">대참사 😱</span>일까요?
        </p>
        """,
        unsafe_allow_html=True
    )

    render_image(str(ASSETS_DIR / "rating-color.png"), css_class="intro-main-image", width=300)

    st.markdown("<br>", unsafe_allow_html=True)
    b64_arrow = img_to_base64(str(ASSETS_DIR / "direction-arrow.png"))
    st.markdown(
        f"""
        <div class="arrow-wrap">
            <img src="data:image/png;base64,{b64_arrow}" width="80" alt="down" class="arrow-rotated">
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("나의 여행 운명 확인하기", use_container_width=True):
        st.session_state.page = "form"

#------------------------------
# 입력 폼 페이지
#------------------------------
def form_page():

    load_css(str(STYLE_DIR / "form.css"))
    render_clouds(str(ASSETS_DIR / "cloudy.png"), count=5, top_range=(5, 80), size_range=(120, 240))

    st.markdown("""
                <h2 class='intro-title'>나의 여행 운명 테스트</h2>
                """, unsafe_allow_html=True)
    
    st.session_state.setdefault("show_form", False)
    if not st.session_state.show_form:
        st.markdown(
            """
            <div class="intro-card">
                <div class="intro-card-icon">⚠️</div>
                <div class="intro-card-text">
                    <p>
                        여행 계획을 입력하면 <b>망한 여행 확률</b>을 계산해 드립니다.<br><br>
                        결과는 살짝 약올릴 수도 있으니 <b>마음의 준비</b>를 하고 보세요 😏<br><br>
                        높은 확률이 나온다면... <b>지금이라도 플랜 B</b>를 준비하세요!
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
        start = st.button("시작", use_container_width=True)
        if start:
            st.session_state.show_form = True
            st.rerun()
        return 
    
    st.markdown("<br>", unsafe_allow_html=True)

    # -- 상태 기본값 -------------------------
    st.session_state.setdefault("gender", "남")
    st.session_state.setdefault("age_grp", "30대")
    st.session_state.setdefault("trip_option", "2박 3일")
    st.session_state.setdefault("trip_days_long", 5)
    st.session_state.setdefault("act_ui", "🍽️ 맛집 탐방")
    
    # -- 성별&연령대 -------------------------
    gender = st.radio(
        "당신의 성별은 무엇인가요?",
        ["남", "여"],
        horizontal=True,
        key="gender"
    )
    age_grp = st.radio(
        "당신의 연령대를 선택해주세요.",
        ["10대", "20대", "30대", "40대", "50대 이상"],
        horizontal=True,
        key="age_grp"
    )

    # -- 여행기간 -------------------------
    trip_option = st.radio(
        "여행기간은 얼마나 되나요?"
        , ["당일치기", "1박 2일", "2박 3일", "3박 4일", "장기 여행 (직접 입력)"]
        , horizontal=True
        , key="trip_option"
    )

    if trip_option == "장기 여행 (직접 입력)":
        trip_days_long = st.slider(
            "여행 일수를 선택하세요(5~30일)",
            min_value=5, max_value=30, step=1, key="trip_days_long"
        )
        trip_days = int(trip_days_long)
    else:
        trip_map = {"당일치기": 1, "1박 2일": 2, "2박 3일": 3, "3박 4일": 4}
        trip_days = trip_map[trip_option]

    # -- 활동유형 -------------------------
    ACT_UI_LABELS = {
        "🍽️ 맛집 탐방": "취식",
        "🛍️ 쇼핑 여행": "쇼핑",
        "🎨 체험 액티비티": "체험",
        "🚶 걷기/투어": "산책",
        "🛌 힐링 여행": "휴식",
        "🗂 기타 활동": "기타",
        "🚌 이동이 많은 여행": "이동",
        "❌ 계획 없음": "없음",
    }

    ui_keys = list(ACT_UI_LABELS.keys())
    act_ui = st.radio(
        "이번 여행에서 가장 많이 할 활동을 선택해주세요."
        , ui_keys
        , horizontal=True
        , key="act_ui"
    )
    act_type = ACT_UI_LABELS[act_ui]
    
    # -- 입력정보확인 -------------------------
    def nights_days_label(days: int) -> str:
        if days <= 1: return "당일치기 (1일)"
        return f"{days-1}박 {days}일"
    
    st.markdown(
        f"""
        <div class="form-preview-card">
            <b>입력 정보 확인</b><br>
            성별: {gender} | 연령대: {age_grp} | 여행기간: {nights_days_label(trip_days)} | 활동: {act_ui}
        </div>
        """, unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # -- 입력값 제출 -------------------------
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("처음으로", key="back_to_intro", use_container_width=True):
            st.session_state.page = "intro"
    with col2:
        check_predict = st.button("여행 운명 확인하기", use_container_width=True)
    with col3:
        if st.button("초기화", use_container_width=True):
            for k in ["gender","age_grp","trip_option","trip_days_long","act_ui"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

    # -- 모델 예측 -------------------------
    if check_predict:
        model = get_model()
        if model is None:
            st.error("Opps! 잠시 후 다시 시도해주세요.")
        
        X = build_input_df(
            trip_days=trip_days,
            gender=st.session_state.gender,
            age_grp=st.session_state.age_grp,
            activity_type_cd=act_type,
        )

        proba = float(model.predict_proba(X)[:, 1][0])
        # proba, _ = predict_failure(model, X)
        print(proba)

        st.session_state.result = proba
        st.session_state.page = "result"

#------------------------------
# 결과 페이지
#------------------------------
def result_page():

    load_css(str(STYLE_DIR / "base.css"))
    load_css(str(STYLE_DIR / "result.css"))
    render_clouds(str(ASSETS_DIR / "cloudy.png"), count=5, top_range=(5, 80), size_range=(120, 240))

    st.markdown("<h2 class='intro-title'>여행 운명 결과</h2>", unsafe_allow_html=True)
    st.markdown("<p class='intro-subtext'>당신의 여행 운명을 예측한 결과입니다.</p>", unsafe_allow_html=True)

    fail_prob = st.session_state.result
    fail_percent = int(fail_prob * 100)

    gauge_color = "#e63946" if fail_percent > 50 else "#06d6a0"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=fail_percent,
            title={"text": "망할 확률 (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": gauge_color},
                "steps": [
                    {"range": [0, 50], "color": "rgba(6,214,160,0.2)"},
                    {"range": [50, 100], "color": "rgba(230,57,70,0.2)"}
                ]
            },
            number={"suffix": "%"}
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

    if fail_percent > 70:
        st.markdown(
            f"""
            <div class="result-card fail">
                😱 이번 여행, 망할 확률 <b>{fail_percent}%</b>! 플랜 B 준비하세요!!<br>
            </div>
            """, unsafe_allow_html=True
        )
    elif fail_percent > 40:
        st.markdown(
            f"""
            <div class="result-card warning">
                🤔 위험한 조짐이 보이네요. <b>{fail_percent}%</b> 확률로 망할 수도...<br>
                여행 계획을 다시 점검하는 걸 추천드려요.
            </div>
            """, unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="result-card success">
                🎉 <b>{fail_percent}%</b> 확률로 안전한 여행!<br>
                걱정 없이 즐기셔도 됩니다.
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, _, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("처음으로", key="back_to_intro", use_container_width=True):
            st.session_state.page = "intro"
    with col3:
        if st.button("다시 시도", key="retry", use_container_width=True):
            st.session_state.page = "form"

#------------------------------
# 페이지 라우팅
#------------------------------
if st.session_state.page == "intro":
    intro_page()
elif st.session_state.page == "form":
    form_page()
elif st.session_state.page == "result":
    result_page()