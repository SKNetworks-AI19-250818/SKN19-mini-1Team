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
from utils.loader import load_css, img_to_base64, render_clouds, render_image
from utils.services import *
BASE_DIR = pathlib.Path(__file__).resolve().parent
STYLE_DIR = BASE_DIR / "style"
ASSETS_DIR = BASE_DIR / "assets" / "img"
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

    render_image(str(ASSETS_DIR / "rating-color.png"), css_class="intro-main-image")

    st.markdown("<br>", unsafe_allow_html=True)
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

    st.markdown("<h2 class='page-title'>✏️ 여행 정보 입력</h2>", unsafe_allow_html=True)
    st.markdown("<p class='page-subtext'>아래 정보를 입력하면 당신의 여행 운명을 알려드립니다.</p>", unsafe_allow_html=True)

    with st.form("travel_form"):
        companion = st.selectbox("동반자 유형", ["혼자", "친구", "연인", "가족", "회사"])
        people = st.slider("동반 인원", 1, 10, 2)
        days = st.slider("여행 일수", 1, 14, 3)
        lodging = st.selectbox("숙소 유형", ["호텔", "모텔", "펜션", "캠핑", "당일치기"])
        moves = st.slider("이동 횟수", 0, 10, 2)
        budget = st.slider(
            "예상 지출 (만원)",
            min_value=0,
            max_value=1000,
            value=50,
            step=1,
            help="여행 전체 예상 비용을 선택하세요." 
        )

        # 버튼 그룹
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col1:
            back_clicked = st.form_submit_button("⬅ 처음으로")
        with col2:
            predict_clicked = st.form_submit_button("🔮 여행 운명 확인하기")
        with col3:
            reset_clicked = st.form_submit_button("🔄 초기화")

        # 버튼 동작
        if back_clicked:
            st.session_state.page = "intro"
        elif reset_clicked:
            st.experimental_rerun()
        elif predict_clicked:
            with st.spinner("결과를 계산 중입니다... ⏳"):
                time.sleep(1)
                inputs = {
                    "companion": companion,
                    "people": people,
                    "days": days,
                    "lodging": lodging,
                    "moves": moves,
                    "budget": budget,
                }
                inputs["budget"] = float(budget)
                proba = predict_failure_proba(inputs)
                st.session_state.result = proba
                st.session_state.page = "result"

#------------------------------
# 결과 페이지
#------------------------------
def result_page():

    load_css(str(STYLE_DIR / "base.css"))
    load_css(str(STYLE_DIR / "result.css"))
    render_clouds(str(ASSETS_DIR / "cloudy.png"), count=5, top_range=(5, 80), size_range=(120, 240))

    st.markdown("<h2 class='page-title'>🔮 여행 운명 결과</h2>", unsafe_allow_html=True)
    st.markdown("<p class='page-subtext'>당신의 여행 운명을 예측한 결과입니다.</p>", unsafe_allow_html=True)

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

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅ 처음으로", key="back_to_intro", use_container_width=True):
            st.session_state.page = "intro"
    with col2:
        if st.button("🔄 다시 시도", key="retry", use_container_width=True):
            st.session_state.page = "form"
    with col3:
        if st.button("🔗 공유하기", key="share", use_container_width=True):
            st.info("공유 기능 준비 중입니다!\n\n결과를 저장하고 친구에게 공유할 수 있도록 업데이트 예정이에요.")

#------------------------------
# 페이지 라우팅
#------------------------------
if st.session_state.page == "intro":
    intro_page()
elif st.session_state.page == "form":
    form_page()
elif st.session_state.page == "result":
    result_page()