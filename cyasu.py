import streamlit as st
import googlemaps
from streamlit.components.v1 import html
import pandas as pd
from geopy.distance import geodesic
from streamlit_folium import folium_static
import folium
from streamlit_folium import st_folium
import json
import importlib

# カスタムCSS読込
from cycustom_css import custom_css
from cycustom_radio_css import custom_css as radio_custom_css

# config.jsonファイルを読込
with open("config.json", "r") as f:
    config = json.load(f)

API_KEY = config["GOOGLE_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)

# キャッシュ付きデータ読込
@st.cache_data
def reload_加盟店_data():
    import 加盟店_data
    importlib.reload(加盟店_data)
    df = pd.DataFrame(加盟店_data.加盟店_data)
    df['lat'] = df['lat'].astype(float)
    df['lon'] = df['lon'].astype(float)
    return df

# キャッシュ付きジオコーディング
@st.cache_data(ttl=3600)
def geocode_address(query):
    results = gmaps.geocode(query)
    return results[0]["geometry"]["location"] if results else None

# カスタムCSS
hide_streamlit_elements = """
    <style>
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        .main .block-container { 
            padding-top: -100px !important;
            margin-top: -100px !important;
        }
        .block-container {
            margin-top: -100px !important;
        }
        input[type="text"] {
            background-color: #f5f5f5;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 10px;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #666;
        }   
        .stSelectbox [contenteditable="true"],
        .stSelectbox input {
            pointer-events: none;
        }
    </style>
"""
st.markdown(hide_streamlit_elements, unsafe_allow_html=True)

# 画像と説明文
st.image("kensakup_topmain3.png", use_container_width=True)

video_html_responsive = """
<div style="border: 1px solid #ccc; border-radius: 8px; padding: 5px; background-color: #f9f9f9; display: flex; align-items: center; gap: 10px; height: 120px; box-sizing: border-box;">
    <div style="flex: 2; height: 100%;">
        <iframe src="https://www.youtube.com/embed/svSkE9pK3_E?si=xLCx3dj5htJAojB1" 
                frameborder="0" 
                allowfullscreen 
                style="width: 100%; height: 100%; border-radius: 5px;">
        </iframe>
    </div>
    <div style="flex: 1; text-align: left; font-size: 10px; line-height: 1.2; overflow-wrap: break-word; word-break: break-word;">
        <h4 style="margin: 0; font-size: 10px; color: #007acc; line-height: 1.2;">“異常”なまでに新鮮な日本酒！人と人とを繋ぐ立春朝搾り</h4>
        <p style="margin: 1px 0; font-size: 10px;">
            「立春朝搾り」がどんなお酒か、わかりやすくご紹介。
        </p>
    </div>
</div>
"""
st.markdown(video_html_responsive, unsafe_allow_html=True)

st.write("")
st.image("kensakup_to-mapwo.png", use_container_width=True)
st.write("フリーワードを入力すると10Km圏内の販売店が表示されます。")

query = st.text_input("最寄り駅やバス停名などを入力してください（例: 新宿駅、東京都新宿区など）:")

if query:
    location = geocode_address(query)
    if not location:
        st.warning("該当する場所が見つかりませんでした。県名などを入れて再検索してください。")
        st.stop()

    search_lat, search_lon = location['lat'], location['lng']
    m = folium.Map(location=[search_lat, search_lon], zoom_start=14)

    加盟店_data_df = reload_加盟店_data()
    
    # ベクトル化された距離計算
    lats = 加盟店_data_df['lat'].values
    lons = 加盟店_data_df['lon'].values
    distances = [geodesic((search_lat, search_lon), (lat, lon)).km for lat, lon in zip(lats, lons)]
    加盟店_data_df['distance'] = distances

    nearby_stores = 加盟店_data_df[加盟店_data_df['distance'] <= 10]
    if len(nearby_stores) == 0:
        st.warning("10km圏内に販売店がありません。30km圏内で再検索します。")
        nearby_stores = 加盟店_data_df[加盟店_data_df['distance'] <= 30]

    folium.Marker(
        [search_lat, search_lon],
        popup="検索地",
        icon=folium.Icon(color="red")
    ).add_to(m)

    if not nearby_stores.empty and "銘柄" in nearby_stores.columns:
        all_brands = set(
            brand for brands in nearby_stores["銘柄"]
            if isinstance(brands, list) and brands
            for brand in brands
        )
        all_brands.add("すべての銘柄")

        selected_brand = st.selectbox("検索エリアの取り扱い銘柄一覧", sorted(all_brands))

        if selected_brand:
            if selected_brand == "すべての銘柄":
                filtered_stores = nearby_stores
            else:
                # 高速化されたフィルタリング
                mask = [selected_brand in brands for brands in nearby_stores["銘柄"]]
                filtered_stores = nearby_stores[mask]

            if not filtered_stores.empty:
                bounds = []
                for _, store in filtered_stores.iterrows():
                    brand_html = "".join(
                        f'<span style="background-color: red; color: white; padding: 2px 4px; margin: 2px; display: inline-block;">{brand}</span>'
                        for brand in store["銘柄"]
                    )
                    popup_content = f"""
                    <b>{store['name']}</b><br>
                    <a href="{store['url']}" target="_blank">加盟店詳細はこちら</a><br>
                    銘柄: {brand_html}<br>
                    距離: {store['distance']:.2f} km
                    """
                    folium.Marker(
                        [store["lat"], store["lon"]],
                        popup=folium.Popup(popup_content, max_width=300),
                        icon=folium.Icon(color="blue"),
                    ).add_to(m)
                    bounds.append((store["lat"], store["lon"]))

                if bounds:
                    bounds.append((search_lat, search_lon))
                    m.fit_bounds(bounds, padding=(30, 30))
                
                st_folium(m, width="100%", height=500)
                st.markdown("""
                <a href="https://www.meimonshu.jp/modules/xfsection/article.php?articleid=377" target="_blank" class="stLinkButton">
                    立春朝搾りとは？公式サイトはこちら
                </a>
                """, unsafe_allow_html=True)
            else:
                st.write(f"「{selected_brand}」を取り扱う店舗はありません。")
    else:
        st.warning("すみません。30km圏内にも該当する店舗が無いようです。")

st.markdown("""
    <style>
        main .block-container {
            padding-bottom: -360px !important;
            margin-bottom: 0px !important;
        }
    </style>
""", unsafe_allow_html=True)
