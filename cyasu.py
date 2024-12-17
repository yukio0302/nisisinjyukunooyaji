import streamlit as st
import googlemaps
from streamlit.components.v1 import html
import pandas as pd
from geopy.distance import geodesic
from streamlit_folium import folium_static
import folium
from streamlit_folium import st_folium
# カスタムCSS読込
from cycustom_css import custom_css
from cycustom_radio_css import custom_css as radio_custom_css

# Google Maps APIキー
GMAPS_API_KEY = "AIzaSyAlOeNotpA-q0KYg8TSTnHoiJz_Am-WguY"
gmaps = googlemaps.Client(key=GMAPS_API_KEY)


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

            # 地図オブジェクト作成
            m = folium.Map(location=[search_lat, search_lon], zoom_start=14)

            # 加盟店データとの距離計算
            加盟店_data["distance"] = 加盟店_data.apply(
                lambda row: geodesic((search_lat, search_lon), (row["lat"], row["lon"])).km, axis=1
            )
            nearby_stores = 加盟店_data[加盟店_data["distance"] <= 10]

            # 赤いピン（検索地点）
            folium.Marker).add_to(m)

            # 検索エリアの取り扱い銘柄一覧を表示
            if not nearby_stores.empty and "銘柄" in nearby_stores.columns:
                all_brands = set(
                    brand for brands in nearby_stores["銘柄"]
                    if isinstance(brands, list) and brands
                    for brand in brands
                )
                all_brands.add("すべての銘柄")

                selected_brand = st.selectbox("検索エリアの取り扱い銘柄一覧", sorted(all_brands))

                # 銘柄によるフィルタリング
                if selected_brand:
                    if selected_brand == "すべての銘柄":
                        filtered_stores = nearby_stores
                    else:
                        filtered_stores = nearby_stores[
                            nearby_stores["銘柄"].apply(lambda brands: selected_brand in brands)
                        ]

                    # 加盟店情報を地図にマッピング
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

                        # 地図の表示範囲設定
                        if bounds:
                            bounds.append((search_lat, search_lon))
                            m.fit_bounds(bounds, padding=(30, 30))
                        else:
                            st.write(f"「{selected_brand}」を取り扱う店舗はありません。")

            # 地図を表示
            st_folium(m, width=700, height=500)

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

            # 地図オブジェクト作成
            m = folium.Map(location=[search_lat, search_lon], zoom_start=14)

            # 加盟店データとの距離計算
            加盟店_data["distance"] = 加盟店_data.apply(
                lambda row: geodesic((search_lat, search_lon), (row["lat"], row["lon"])).km, axis=1
            )
            nearby_stores = 加盟店_data[加盟店_data["distance"] <= 10]

            # 赤いピン（検索地点）
            folium.Marker(
                [search_lat, search_lon],
                popup="検索地",
                icon=folium.Icon(color="red")
            ).add_to(m)

            # 検索エリアの取り扱い銘柄一覧を表示
            if not nearby_stores.empty and "銘柄" in nearby_stores.columns:
                all_brands = set(
                    brand for brands in nearby_stores["銘柄"]
                    if isinstance(brands, list) and brands
                    for brand in brands
                )
                all_brands.add("すべての銘柄")

                selected_brand = st.selectbox("検索エリアの取り扱い銘柄一覧", sorted(all_brands))

                # 銘柄によるフィルタリング
                if selected_brand:
                    if selected_brand == "すべての銘柄":
                        filtered_stores = nearby_stores
                    else:
                        filtered_stores = nearby_stores[
                            nearby_stores["銘柄"].apply(lambda brands: selected_brand in brands)
                        ]

                    # 加盟店情報を地図にマッピング
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

                        # 地図の表示範囲設定
                        if bounds:
                            bounds.append((search_lat, search_lon))
                            m.fit_bounds(bounds, padding=(30, 30))

            # 地図を表示
            st_folium(m, width=700, height=500)

        else:
            st.warning("該当する駅が見つかりませんでした。")
