import streamlit as st
import googlemaps
import pandas as pd
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
import json
import importlib
import os
from datetime import datetime
import uuid
import hashlib

# ============================================
# 改良版アクセスカウンター関数 - UptimeRobot対応版
# ============================================
def update_access_count():
    counter_file = "total_access_counter.json"
    today = datetime.now().strftime("%Y-%m-%d")
    
    # カウンターファイルの読み込み
    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            # ファイルが壊れている場合は初期化
            data = {
                "total_access_count": 0, 
                "last_updated": "", 
                "first_access": datetime.now().isoformat(),
                "daily_counts": {},
                "session_ids": {},
                "bot_accesses": {}  # Botアクセス記録用
            }
    else:
        # 初回実行時
        data = {
            "total_access_count": 0, 
            "last_updated": "", 
            "first_access": datetime.now().isoformat(),
            "daily_counts": {},
            "session_ids": {},
            "bot_accesses": {}
        }
    
    # ユーザーエージェントをチェック（Bot判定用）
    user_agent = ""
    try:
        if hasattr(st, 'request') and hasattr(st.request, 'headers'):
            user_agent = st.request.headers.get("User-Agent", "").lower()
    except:
        pass
    
    # Bot判定
    is_bot = any(bot in user_agent for bot in ['uptimerobot', 'bot', 'crawl', 'spider', 'monitor', 'check'])
    
    # UptimeRobotなどのBotアクセスもカウントする設定
    count_bots = True
    
    if is_bot and count_bots:
        # Bot用の一意なIDを生成（IP + 日付）
        try:
            if hasattr(st, 'request') and hasattr(st.request, 'remote_addr'):
                client_ip = st.request.remote_addr
            else:
                client_ip = "unknown"
        except:
            client_ip = "unknown"
        
        # Botの一意IDを生成
        bot_id = hashlib.md5(f"bot_{today}_{client_ip}".encode()).hexdigest()[:12]
        bot_key = f"bot_{today}"
        
        # 今日のBotアクセスをチェック
        if bot_key not in data["bot_accesses"]:
            data["bot_accesses"][bot_key] = []
        
        # このBotが今日まだカウントされていない場合
        if bot_id not in data["bot_accesses"][bot_key]:
            data["total_access_count"] += 1
            data["last_updated"] = datetime.now().isoformat()
            data["bot_accesses"][bot_key].append(bot_id)
            
            # 日別カウント
            if today in data["daily_counts"]:
                data["daily_counts"][today] += 1
            else:
                data["daily_counts"][today] = 1
            
            # Botアクセスとして記録
            print(f"🤖 Botアクセスをカウント: {bot_id}")
            
            # 保存
            try:
                with open(counter_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"カウンター保存エラー: {e}")
            
            return data["total_access_count"]
    
    # 通常のユーザーアクセスの処理
    # StreamlitセッションIDを取得（または生成）
    if "access_counter_session_id" not in st.session_state:
        st.session_state.access_counter_session_id = str(uuid.uuid4())
    
    session_id = st.session_state.access_counter_session_id
    
    # 今日の日付で既存のセッションIDを確認
    today_session_ids = data.get("session_ids", {}).get(today, [])
    
    # このセッションが今日まだカウントされていない場合
    if session_id not in today_session_ids:
        # 総アクセス数を増加
        data["total_access_count"] += 1
        data["last_updated"] = datetime.now().isoformat()
        
        # 日別カウント
        if today in data["daily_counts"]:
            data["daily_counts"][today] += 1
        else:
            data["daily_counts"][today] = 1
        
        # セッションIDを記録
        if "session_ids" not in data:
            data["session_ids"] = {}
        if today not in data["session_ids"]:
            data["session_ids"][today] = []
        data["session_ids"][today].append(session_id)
        
        # 古いセッションIDをクリーンアップ（30日以上前のデータを削除）
        old_dates = []
        for date_str in list(data["session_ids"].keys()):
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if (datetime.now() - date_obj).days > 30:
                    old_dates.append(date_str)
            except:
                continue
        
        for old_date in old_dates:
            if old_date in data["session_ids"]:
                del data["session_ids"][old_date]
            if old_date in data["daily_counts"]:
                del data["daily_counts"][old_date]
        
        # 古いBotアクセスもクリーンアップ
        old_bot_dates = []
        for date_str in list(data["bot_accesses"].keys()):
            # bot_2024-01-15 のような形式から日付を抽出
            if date_str.startswith("bot_"):
                date_part = date_str[4:]  # "bot_"を除去
                try:
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                    if (datetime.now() - date_obj).days > 30:
                        old_bot_dates.append(date_str)
                except:
                    continue
        
        for old_date in old_bot_dates:
            if old_date in data["bot_accesses"]:
                del data["bot_accesses"][old_date]
        
        # 保存
        try:
            with open(counter_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"カウンター保存エラー: {e}")
    
    return data["total_access_count"]

# ============================================
# セッション状態の永続化を試みる（再起動対策）
# ============================================
def try_restore_session():
    """セッション状態をファイルから復元しようと試みる"""
    session_file = "session_backup.json"
    if os.path.exists(session_file):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # セッションIDを復元
            if "access_counter_session_id" in session_data:
                st.session_state.access_counter_session_id = session_data["access_counter_session_id"]
                print(f"セッションIDを復元: {session_data['access_counter_session_id'][:8]}...")
            
            # カウント済みフラグを復元
            if "counted" in session_data:
                st.session_state.counted = session_data["counted"]
        except Exception as e:
            print(f"セッション復元エラー: {e}")

def save_session():
    """セッション状態をファイルに保存"""
    try:
        session_data = {
            "access_counter_session_id": st.session_state.get("access_counter_session_id", ""),
            "counted": st.session_state.get("counted", False),
            "saved_at": datetime.now().isoformat()
        }
        
        with open("session_backup.json", 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"セッション保存エラー: {e}")

# ============================================
# UptimeRobot用の特別なpingエンドポイント
# ============================================
# クエリパラメータでUptimeRobotからのアクセスを確認
import urllib.parse

# 現在のURLを取得してUptimeRobotか判定
current_url = ""
try:
    # Streamlitのリクエスト情報から判定
    if hasattr(st, 'query_params'):
        query_params = st.query_params
        if 'ping' in query_params:
            # UptimeRobotからのpingリクエスト
            st.set_page_config(layout="centered")
            st.markdown("""
            <style>
                .main .block-container {
                    padding-top: 0;
                    padding-bottom: 0;
                }
                body {
                    background-color: #f0f2f6;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # 最小限の応答
            st.markdown(f"""
            <div style='text-align: center; padding: 50px;'>
                <h1 style='color: green;'>✅ OK</h1>
                <p>Streamlit App is alive</p>
                <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # JSONでも応答（UptimeRobotのキーワードチェック用）
            st.json({
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "app": "risshun-mapkensaku",
                "message": "立春朝搾り販売店検索アプリ"
            })
            
            # ここでカウンターを更新
            counter_file = "total_access_counter.json"
            if os.path.exists(counter_file):
                try:
                    with open(counter_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    data["total_access_count"] += 1
                    data["last_updated"] = datetime.now().isoformat()
                    
                    with open(counter_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except:
                    pass
            
            st.stop()
except:
    pass

# ============================================
# メインアプリの開始
# ============================================

# セッション状態の復元を試みる
try_restore_session()

# カウンター更新（ページ上部で最初に実行）
access_count = update_access_count()

# カウンター更新後にセッションを保存
save_session()

# カスタムCSS読込
try:
    from cycustom_css import custom_css
    from cycustom_radio_css import custom_css as radio_custom_css
except:
    pass

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
        <h4 style="margin: 0; font-size: 10px; color: #007acc; line-height: 1.2;">"異常"なまでに新鮮な日本酒！人と人とを繋ぐ立春朝搾り</h4>
        <p style="margin: 1px 0; font-size: 10px;">
            「立春朝搾り」がどんなお酒か、わかりやすくご紹介。
        </p>
    </div>
</div>
"""
st.markdown(video_html_responsive, unsafe_allow_html=True)

st.write("")
st.image("kensakup_to-mapwo.png", use_container_width=True)
st.write("フリーワードを入力すると10km圏内の販売店が表示されます。")

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

# UptimeRobotのアクセスを確実に記録するための隠し要素
st.markdown("""
<div style="display: none;">
<!-- UptimeRobot監視用の隠し要素 -->
<div id="uptimerobot-check">✅ Active - 立春朝搾り販売店検索</div>
<time id="current-time">{}</time>
</div>

<script>
// 定期的にタイムスタンプを更新
setInterval(function() {
    document.getElementById('current-time').textContent = new Date().toISOString();
}, 30000); // 30秒ごとに更新

// バックグラウンドで軽いリクエスト（オプション）
setInterval(function() {
    // 軽量なpingを送信
    if (navigator.sendBeacon) {
        navigator.sendBeacon(window.location.href + '?ping=keepalive');
    }
}, 25 * 60 * 1000); // 25分ごと
</script>
""".format(datetime.now().isoformat()), unsafe_allow_html=True)

# より見やすいアクセスカウンター（画面左下に配置）
st.markdown(f"""
    <div style='
        position: fixed;
        bottom: 10px;
        left: 10px;
        color: #666666;
        font-size: 12px;
        opacity: 0.6;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.7);
        padding: 2px 6px;
        border-radius: 3px;
        transition: opacity 0.3s;
    '
    onmouseover="this.style.opacity='1'; this.style.backgroundColor='rgba(255, 255, 255, 0.9)';"
    onmouseout="this.style.opacity='0.7'; this.style.backgroundColor='rgba(255, 255, 255, 0.7)';"
    >
        📊 総訪問: {access_count}
    </div>
""", unsafe_allow_html=True)
