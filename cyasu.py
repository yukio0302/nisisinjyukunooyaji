import streamlit as st
import googlemaps
from streamlit.components.v1 import html
import pandas as pd
from geopy.distance import geodesic
import folium
from folium.plugins import MarkerCluster

# Google Maps APIキー
GMAPS_API_KEY = "AIzaSyAlOeNotpA-q0KYg8TSTnHoiJz_Am-WguY"
gmaps = googlemaps.Client(key=GMAPS_API_KEY)

# カスタムCSS読込
from cycustom_css import custom_css
from cycustom_radio_css import custom_css as radio_custom_css

# 強制的にCSSで開発者アイコンとロゴを非表示にする
hide_streamlit_elements = """
    <style>
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
    </style>
"""
st.markdown(hide_streamlit_elements, unsafe_allow_html=True)

# 加盟店データを外部ファイルからインポート
from 加盟店_data import 加盟店_data

st.image("kensakup_top.png",  use_container_width=True)
st.write("郵便番号もしくは住所を入力して、10km圏内の加盟店を検索します。")

# 検索モード選択
search_mode = st.radio("検索方法を選択してください：", ("住所で検索", "最寄り駅で検索"))

# 入力フォーム
if search_mode == "住所で検索":
    postal_code_input = st.text_input("郵便番号を入力してください（例: 123-4567）:")
    address_input = st.text_input("住所（番地・号を除く）を入力してください:")
    query = postal_code_input or address_input

    if query:
        # Geocodingで緯度経度を取得
        results = gmaps.geocode(query)
        if results:
            search_lat = results[0]["geometry"]["location"]["lat"]
            search_lon = results[0]["geometry"]["location"]["lng"]

            # 地図作成
            map_ = folium.Map(location=[search_lat, search_lon], zoom_start=14)

            # 赤いピンを追加（検索地点）
            folium.Marker([search_lat, search_lon], popup="検索地", icon=folium.Icon(color='red')).add_to(map_)

            # 加盟店データとの距離計算
            加盟店_data["distance"] = 加盟店_data.apply(
                lambda row: geodesic((search_lat, search_lon), (row["lat"], row["lon"])).km, axis=1
            )
            nearby_stores = 加盟店_data[加盟店_data["distance"] <= 10]

            # 青いピンを追加（加盟店）
            for _, store in nearby_stores.iterrows():
                folium.Marker(
                    [store["lat"], store["lon"]],
                    popup=f"""
                        店名: {store['name']}<br>
                        <a href="{store['url']}" target="_blank">加盟店詳細はこちら</a><br>
                        銘柄: <span style="background-color:red;color:white;">{store['銘柄']}</span><br>
                        距離: {store['distance']:.2f} km
                    """,
                    icon=folium.Icon(color='blue')
                ).add_to(map_)

            # 地図を表示
            st.write(map_)

            # 銘柄セレクトボックスを表示
            brands = nearby_stores['brand'].unique()
            selected_brand = st.selectbox('銘柄を選択してください', brands)

            # 選択した銘柄の加盟店のみ表示
            filtered_stores = nearby_stores[nearby_stores['brand'] == selected_brand]
            st.write(f"選択された銘柄: {selected_brand}")
            for _, store in filtered_stores.iterrows():
                st.write(f"- {store['name']} ({store['distance']:.2f} km)")

        else:
            st.warning("住所または郵便番号に該当する場所が見つかりませんでした。")

elif search_mode == "最寄り駅で検索":
    station_name = st.text_input("最寄り駅名を入力してください:")
    if station_name:
        query = f"{station_name}駅"
        results = gmaps.geocode(query)
        if results:
            search_lat = results[0]["geometry"]["location"]["lat"]
            search_lon = results[0]["geometry"]["location"]["lng"]

            # 地図作成
            map_ = folium.Map(location=[search_lat, search_lon], zoom_start=14)

            # 赤いピンを追加（検索地点）
            folium.Marker([search_lat, search_lon], popup="検索地", icon=folium.Icon(color='red')).add_to(map_)

            # 地図を表示
            st.write(map_)
        else:
            st.warning("該当する駅が見つかりませんでした。")
