import streamlit as st
import os
import json
import base64
import folium
import rasterio
import numpy as np
from PIL import Image
import io
from streamlit_folium import st_folium
from rasterio.warp import calculate_default_transform, reproject, Resampling
from branca.element import Template, MacroElement


def reproject_to_epsg4326(tif_path):
    with rasterio.open(tif_path) as src:
        src_crs = src.crs
        dst_crs = 'EPSG:4326'
        nodata = src.nodata

        transform, width, height = calculate_default_transform(
            src_crs, dst_crs, src.width, src.height, *src.bounds
        )

        dst = np.zeros((height, width), dtype=np.float32)

        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src_crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
            src_nodata=nodata,
            dst_nodata=np.nan
        )

        left = transform[2]
        top = transform[5]
        right = left + transform[0] * width
        bottom = top + transform[4] * height

        bounds_4326 = [[bottom, left], [top, right]]

        return dst, bounds_4326, nodata

def make_legend_html(legend_dict):
    items_html = ""
    for label, color in legend_dict.items():
        items_html += f"""
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <div style="width:18px; height:18px; background:{color}; border:1px solid #ccc;"></div>
            <span style="margin-left:8px;">{label}</span>
        </div>
        """

st.set_page_config(layout="wide")

APP_DIR = os.path.dirname(__file__)
GEO_PATH = os.path.join(APP_DIR, "jb_sgg.geojson")
BASE_DIR = os.path.join(APP_DIR, "static/full_tif")

with open(GEO_PATH, "r", encoding="utf-8") as f:
    JB_GEO = json.load(f)


st.title("전북 과수 재배지 변동 예측지도")

crops = {
    "apple": "img/apple.png",
    "grape": "img/grape.png",
    "peach": "img/peach.png",
    "pear": "img/pear.png",
    "tangerine": "img/tangerine.png",
}

def img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


crop_imgs = {k: img_to_b64(os.path.join(APP_DIR, v)) for k, v in crops.items()}


if "selected_crop" not in st.session_state:
    st.session_state["selected_crop"] = None


left_label = st.session_state["selected_crop"].capitalize() if st.session_state["selected_crop"] else ""
st.markdown(f"### 🍎 작목 선택 — {left_label}")

st.markdown("""
<style>
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
    year = st.select_slider("연도 선택 (2021 / 2041 / 2061 / 2081)", [2021, 2041, 2061, 2081], value=2021)

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



full_path = os.path.join(BASE_DIR, crop, scenario, f"{crop}_{scenario}_{year}_FULL.tif")

if not os.path.exists(full_path):
    st.error(f"⚠️ 파일을 불러오는 데 문제가 발생했습니다.\n관리자에게 문의해 주세요:\n => {full_path}")
    st.stop()


m = folium.Map(location=[36.0, 127.0], zoom_start=8)

folium.GeoJson(
    JB_GEO,
    name="전북 시군구 경계",
    style_function=lambda feature: {
        "color": "blue",
        "weight": 2,
        "fill": True,
        "fillColor": "#000000",
        "fillOpacity": 0.0,
    },
    highlight_function=lambda feature: {
        "weight": 3,
        "fill": True,
        "fillColor": "#000000",
        "fillOpacity": 0.0,
    },
    popup=folium.GeoJsonPopup(
        fields=["SIG_KOR_NM", "SIG_ENG_NM"],
        aliases=["", ""],
        labels=False,
        parse_html=True,
        localize=True,
        style="font-size:15px;",
        template="""
            <div style="font-size:15px;">
                {{SIG_KOR_NM}} ({{SIG_ENG_NM}})
            </div>
            """
    )
).add_to(m)


arr32, bounds_4326, nodata = reproject_to_epsg4326(full_path)


arr = arr32.copy()
arr = np.where(np.isnan(arr), 255, arr).astype(np.uint8)

palette = []
palette += [255, 248, 220]    # 0 Bad
palette += [238, 201, 0]      # 1 Possible
palette += [46, 139, 87]      # 2 Suitable



while len(palette) < 255 * 3:
    palette += [0, 0, 0]

palette += [0, 0, 0]

img = Image.fromarray(arr, mode="P")
img.putpalette(palette)
img.info["transparency"] = 255

buffer = io.BytesIO()
img.save(buffer, format="PNG")
encoded_png = base64.b64encode(buffer.getvalue()).decode()

legend_template = """
{% macro html(this, kwargs) %}

<div id='maplegend' 
     style='position: absolute; 
            z-index:9999; 
            background-color: white;
            border:2px solid #bbb;
            border-radius:6px;
            padding: 10px;
            bottom: 50px;
            right: 20px;
            font-size:14px;
            color:#333;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.3);'>

<b>재배 적합도</b><br><br>

<div style='display:flex; align-items:center; margin-bottom:4px;'>
    <div style='width:16px; height:16px; background:rgb(255,248,220); border:1px solid #999;'></div>
    <span style='margin-left:6px; color:#333;'>저위생산지</span>
</div>

<div style='display:flex; align-items:center; margin-bottom:4px;'>
    <div style='width:16px; height:16px; background:rgb(238,201,0); border:1px solid #999;'></div>
    <span style='margin-left:6px; color:#333;'>재배가능지</span>
</div>

<div style='display:flex; align-items:center;'>
    <div style='width:16px; height:16px; background:rgb(46,139,87); border:1px solid #999;'></div>
    <span style='margin-left:6px; color:#333;'>재배적합지</span>
</div>

</div>

{% endmacro %}
"""

macro = MacroElement()
macro._template = Template(legend_template)
m.get_root().add_child(macro)

folium.raster_layers.ImageOverlay(
    image=f"data:image/png;base64,{encoded_png}",
    bounds=bounds_4326,
    opacity=opacity,
    name=f"{crop}_{scenario}_{year}_재배적합도"
).add_to(m)

m.get_root().add_child(macro)

folium.LayerControl().add_to(m)


st_folium(m, width="100%", height=700)