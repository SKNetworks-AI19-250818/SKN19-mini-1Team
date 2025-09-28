import random
import streamlit as st
from pathlib import Path
import base64
import streamlit.components.v1 as components
import pathlib

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

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets" / "img"
SEASON_IMAGES = {
    "봄": ASSETS_DIR/"sakura.png",
    "여름": ASSETS_DIR/"watermelon.png",
    "가을": ASSETS_DIR/"autumn.png",
    "겨울": ASSETS_DIR/"snowflake.png",
}

def render_season_clouds(season: str, count=5, top_range=(5, 80), size_range=(120, 240)):
    path = SEASON_IMAGES[season]
    render_clouds(path, count=count, top_range=top_range, size_range=size_range)

def audio_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:audio/wav;base64,{b64}"

# background 음악을 끊김 없이 삽입하는 HTML iframe 방식
def insert_background_audio(audio_data_uri):
    html = f"""
    <html>
      <body style="margin:0; padding:0; overflow:hidden;">
        <audio autoplay loop id="bg-music" style="display:none">
          <source src="{audio_data_uri}" type="audio/wav">
        </audio>
        <script>
          const audio = document.getElementById('bg-music');
          if (audio) {{
            audio.play().catch((e) => {{
              console.log("Autoplay failed:", e);
            }});
          }}
        </script>
      </body>
    </html>
    """
    components.html(html, height=0, width=0, scrolling=False)