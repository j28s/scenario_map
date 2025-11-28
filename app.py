import streamlit as st
import leafmap.foliumap as leafmap
import os
import json
import folium
import base64


st.set_page_config(layout="wide")

SGG = {
    45790: "고창군", 45130: "군산시", 45210: "김제시",
    45190: "남원시", 45730: "무주군", 45800: "부안군",
    45770: "순창군", 45710: "완주군", 45140: "익산시",
    45750: "임실군", 45740: "장수군", 45113: "전주시 덕진구",
    45111: "전주시 완산구", 45180: "정읍시", 45720: "진안군"
}
JEONJU_CODES = [45111, 45113]

APP_DIR = os.path.dirname(__file__)
GEO_PATH = os.path.join(APP_DIR, "jb_sgg.geojson")

with open(GEO_PATH, "r", encoding="utf-8") as f:
    JB_GEO = json.load(f)


st.title("전북 과수 재배지 변동 예측지도")

BASE_DIR = os.path.join(APP_DIR, "full_tif")

def img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


crops = {
    "apple": "img/apple.png",
    "grape": "img/grape.png",
    "peach": "img/peach.png",
    "pear": "img/pear.png",
    "tangerine": "img/tangerine.png",
}


crop_imgs = {k: img_to_b64(v) for k, v in crops.items()}

if "selected_crop" not in st.session_state:
    st.session_state["selected_crop"] = None

left_label = st.session_state["selected_crop"].capitalize() if st.session_state["selected_crop"] else ""
st.markdown(f"### 🍎 작목 선택 — {left_label}")

st.markdown("""
<style>
button[id^="cropbtn_"] {
    background: none !important;
    border: none !important;
    padding: 0 !important;
}
.crop-img {
    width: 110px;
    border-radius: 16px;
    transition: 0.2s;
}
.crop-label {
    font-size: 20px;
    text-align: center;
    margin-top: 10px;
    cursor: pointer;
    padding: 6px 12px;
    border-radius: 8px;
    transition: 0.2s;
    display: inline-block;
}
.crop-label:hover {
    background-color: rgba(255,255,255,0.15);
    transform: scale(1.05);
}
.label-selected {
    background-color: #ff6f6f !important;
    color: white !important;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


cols = st.columns(5)

for i, (crop, img_b64) in enumerate(crop_imgs.items()):
    with cols[i]:

        selected = (st.session_state.selected_crop == crop)

        st.markdown(
            f"""
            <div style="text-align:center;">
                <img src="data:image/png;base64,{img_b64}" class="crop-img">
            </div>
            """,
            unsafe_allow_html=True
        )

        label_class = "crop-label"
        if selected:
            label_class += " label-selected"

        if st.button(crop.capitalize(), key=f"labelbtn_{crop}"):
            st.session_state.selected_crop = crop
            st.rerun()

crop = st.session_state["selected_crop"]


scenario = st.selectbox("시나리오", ["SSP245", "SSP585"])
if scenario == "SSP585":
    year = 2021 if st.checkbox("2021 (단일 연도)", value=True) else None
else:
    year = st.select_slider("연도 선택 ( 2021 / 2041 / 2061 / 2081 )", [2021, 2041, 2061, 2081], value=2021)
opacity = st.slider("TIFF 투명도", 0.0, 1.0, 0.7)


btn_col, txt_col = st.columns([3, 11])
with btn_col:
    load_clicked = st.button("지도 불러오기")
with txt_col:
    st.markdown(
        "<p style='font-size:14px; color:#b0b0b0; margin-top:10px;'>"
        "작목·시나리오·연도를 선택한 뒤 <b>'지도 불러오기'</b>를 누르세요."
        "</p>",
        unsafe_allow_html=True,
    )

if load_clicked:
    if crop is None:
        st.error("⚠️ 먼저 작목을 선택해주세요!")
        st.stop()
    if year is None:
        st.error("⚠️ 연도를 선택해주세요!")
        st.stop()
    st.session_state["show_map"] = True

if not st.session_state.get("show_map", False):
    st.stop()


full_path = os.path.join(
    BASE_DIR,
    crop,
    scenario,
    f"{crop}_{scenario}_{year}_FULL.tif"
)

if not os.path.exists(full_path):
    st.error(f"TIFF 파일이 존재하지 않습니다.\n{full_path}")
    st.stop()

m = leafmap.Map(center=[36.0, 127.0], zoom=8)

colormap = ["#FFF8DC", "#EEC900", "#2E8B57"]
legend_dict = {
    "Bad (0)": "#FFF8DC",
    "Possible (1)": "#EEC900",
    "Suitable (2)": "#2E8B57"
}

m.add_legend(title="Suitability", legend_dict=legend_dict)


for feature in JB_GEO["features"]:
    kor = feature["properties"]["SIG_KOR_NM"]
    eng = feature["properties"]["SIG_ENG_NM"]
    feature["properties"] = {
        "": f"{kor} ({eng})"
    }

m.add_geojson(
    JB_GEO,
    layer_name="전북 시군구 경계",
    info_mode="on_click"
)

with st.spinner("TIFF 지도를 불러오는 중입니다... (조금만 기다려주세요!)"):
    m.add_raster(
        full_path,
        colormap=colormap,
        opacity=opacity,
        layer_name=f"{crop}_{scenario}_{year}"
    )

m.to_streamlit(width="100%", height=700)

# st.markdown(
#     """
#     <small>
#     아이콘 출처:
#     사과 - Freepik,
#     배 - kosonicon,
#     복숭아 - Vitaly Gorbachev,
#     포도 - Dreamcreateicons,
#     귤 - Triangle Squad (모두 Flaticon)
#     </small>
#     """,
#     unsafe_allow_html=True
# )