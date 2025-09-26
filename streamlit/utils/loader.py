import random
import streamlit as st
from pathlib import Path
import base64

def load_css(file_name: str):
    """
    page에 적용되는 css 로드
    """
    css_path = Path("style") / file_name
    
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def img_to_base64(path: str) -> str:
    """
    base64로 이미지 변환
    """
    return base64.b64encode(Path(path).read_bytes()).decode()

def render_image(image_path: str, css_class: str = "", width=None, alt=None):
    """
    base64로 변환한 이미지 출력
    - image_path: 이미지 경로
    - css_class: 추가 CSS 클래스
    - width: px 단위 폭 (옵션)
    - alt: 대체 텍스트 (옵션)
    """
    b64_img = img_to_base64(image_path)
    width_attr = f'width="{width}"' if width else ""
    alt_attr = f'alt="{alt}"' if alt else ""
    class_attr = f'class="{css_class}"' if css_class else ""
    
    st.markdown(
        f'<img src="data:image/png;base64,{b64_img}" {width_attr} {alt_attr} {class_attr}>',
        unsafe_allow_html=True
    )

def render_clouds(image_path: str, count=5, top_range=(5, 80), size_range=(120, 240)):
    """
    랜덤 구름 생성
    - image_path: 구름 이미지 경로
    - count: 구름 개수
    - top_range: (min, max) top 위치 범위 (퍼센트)
    - size_range: (min, max) 구름 크기 범위 (px)
    """
    b64_cloud = img_to_base64(image_path)

    clouds = "".join([
        f'<img src="data:image/png;base64,{b64_cloud}" class="cloud" '
        f'style="left:{random.randint(5, 90)}%; '
        f'top:{random.randint(*top_range)}%; '
        f'width:{size}px; height:auto; animation-delay:{round(random.uniform(0, 5), 1)}s;">'
        for size in [random.randint(*size_range) for _ in range(count)]
    ])

    st.markdown(clouds, unsafe_allow_html=True)