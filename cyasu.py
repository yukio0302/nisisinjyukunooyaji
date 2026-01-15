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
import os
from datetime import datetime

# 改良版アクセスカウンター関数 - 総アクセス数を永続化
# 改良版アクセスカウンター関数 - Streamlit対応版（日付リセット問題修正）
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
                "session_ids": {}
            }
    else:
        # 初回実行時
        data = {
            "total_access_count": 0, 
            "last_updated": "", 
            "first_access": datetime.now().isoformat(),
            "daily_counts": {},
            "session_ids": {}
        }
    
    # StreamlitセッションIDを取得（または生成）
    if "access_counter_session_id" not in st.session_state:
        import uuid
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
        
        # 保存
        try:
            with open(counter_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"カウンター保存エラー: {e}")
    
    return data["total_access_count"]

# カウンター更新（ページ上部で最初に実行）
access_count = update_access_count()

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

# Streamlitアプリの最後に追加（改良版）
st.markdown("""
<script>
// スリープ防止用の自動再接続スクリプト（改良版）
(function() {
    'use strict';
    
    console.log('🔄 Streamlitスリープ防止スクリプト開始');
    
    const CONFIG = {
        // 20分間非アクティブでping送信（30分タイムアウト前）
        INACTIVE_TIMEOUT: 20 * 60 * 1000, // 20分
        CHECK_INTERVAL: 2 * 60 * 1000,    // 2分ごとにチェック
        PING_INTERVAL: 25 * 60 * 1000,    // 25分間隔で定期的にping
        DEBUG: true
    };
    
    let lastActivity = Date.now();
    let lastPing = Date.now();
    let isActiveTab = true;
    
    // デバッグログ
    function debugLog(message) {
        if (CONFIG.DEBUG) {
            console.log(`[スリープ防止] ${message}`);
        }
    }
    
    // ユーザーアクティビティを検知
    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'scroll', 'click'];
    activityEvents.forEach(event => {
        document.addEventListener(event, () => {
            lastActivity = Date.now();
            debugLog(`ユーザーアクティビティ検出: ${event}`);
        }, { passive: true });
    });
    
    // タブの表示状態を監視
    document.addEventListener('visibilitychange', () => {
        isActiveTab = !document.hidden;
        debugLog(`タブ状態: ${isActiveTab ? '表示中' : '非表示'}`);
    });
    
    // 軽量なpingを送信
    function sendKeepAlivePing() {
        const now = Date.now();
        const pingUrl = `${window.location.origin}${window.location.pathname}?keepalive=${now}`;
        
        debugLog(`ping送信: ${pingUrl}`);
        
        // シンプルなfetchリクエスト
        fetch(pingUrl, {
            method: 'GET',
            mode: 'no-cors',
            cache: 'no-cache',
            headers: {
                'X-Keep-Alive': 'true',
                'X-Timestamp': now.toString()
            }
        })
        .then(() => {
            lastPing = Date.now();
            debugLog(`✅ ping成功: ${new Date().toLocaleTimeString()}`);
        })
        .catch(err => {
            debugLog(`⚠️ ping失敗: ${err.message}`);
        });
    }
    
    // 定期的にチェック
    setInterval(() => {
        const now = Date.now();
        const inactiveTime = now - lastActivity;
        const timeSinceLastPing = now - lastPing;
        
        debugLog(`非アクティブ時間: ${Math.round(inactiveTime/1000)}秒 | 前回pingから: ${Math.round(timeSinceLastPing/1000)}秒`);
        
        // 条件1: 20分以上非アクティブの場合
        if (inactiveTime >= CONFIG.INACTIVE_TIMEOUT) {
            debugLog('⏰ 20分以上非アクティブ → ping送信');
            sendKeepAlivePing();
        }
        
        // 条件2: 25分間隔での定期ping（タブが表示中のみ）
        else if (timeSinceLastPing >= CONFIG.PING_INTERVAL && isActiveTab) {
            debugLog('🕒 定期ping送信（25分間隔）');
            sendKeepAlivePing();
        }
        
    }, CONFIG.CHECK_INTERVAL);
    
    // 初期ping（ページ読み込み後30秒）
    setTimeout(() => {
        debugLog('初期ping送信（ページ読み込み後）');
        sendKeepAlivePing();
    }, 30000);
    
    // ページ離脱時にもping
    window.addEventListener('beforeunload', () => {
        if (navigator.sendBeacon) {
            const beaconUrl = `${window.location.origin}${window.location.pathname}?unload=${Date.now()}`;
            navigator.sendBeacon(beaconUrl);
            debugLog('📤 ページ離脱時にping送信');
        }
    });
    
    debugLog('スクリプト初期化完了');
    
    // グローバルに公開（必要に応じて）
    window.keepAlive = {
        sendPing: sendKeepAlivePing,
        getStatus: () => ({
            lastActivity: new Date(lastActivity).toLocaleTimeString(),
            lastPing: new Date(lastPing).toLocaleTimeString(),
            isActiveTab: isActiveTab
        })
    };
    
})();
</script>

<!-- 隠し要素でping状態を表示（オプション） -->
<div id="keepalive-status" style="display: none; position: fixed; bottom: 10px; right: 10px; 
      background: rgba(0,0,0,0.7); color: white; padding: 5px 10px; border-radius: 5px; 
      font-size: 12px; z-index: 9999;">
  スリープ防止: 有効
</div>

<script>
// ステータス表示の切り替え（オプション）
setTimeout(() => {
    const statusEl = document.getElementById('keepalive-status');
    if (statusEl) {
        statusEl.style.display = 'block';
        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 3000);
    }
}, 5000);
</script>
""", unsafe_allow_html=True)
