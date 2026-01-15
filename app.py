import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =========================
# 1. 頁面配置 (Page Config)
# =========================
st.set_page_config(
    page_title="🟢 持股結構診斷工具",
    page_icon="📈",
    layout="centered"
)

# =========================
# 2. 數據引擎 (Data Engine)
# =========================
@st.cache_data(ttl=3600)
def fetch_stock_data(sid: str):
    sid = sid.strip().upper()
    for suffix in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{sid}{suffix}")
            df = ticker.history(period="2y")
            if not df.empty:
                return df, f"{sid}{suffix}"
        except Exception:
            pass
    return pd.DataFrame(), None

# =========================
# 3. 側邊欄設定
# =========================
st.sidebar.header("💰 持倉設定（選填）")
stock_id = st.sidebar.text_input("輸入代碼 (例如: 5498, 00980A)", value="5498").strip()
cost_price = st.sidebar.number_input("買入均價", min_value=0.0, step=0.1)
shares = st.sidebar.number_input("持有股數", min_value=0, step=1000)

# =========================
# 4. 數據加載與指標計算
# =========================
df, final_id = fetch_stock_data(stock_id)

if df.empty:
    st.error(f"❌ 無法取得 {stock_id} 的市場資料。請檢查代號或確認 requirements.txt 已設定。")
    st.stop()

# 計算均線
df["MA5"] = df["Close"].rolling(5).mean()
df["MA13"] = df["Close"].rolling(13).mean()
df["MA37"] = df["Close"].rolling(37).mean()

# 計算量能倍率 (今日成交量 / 5日均量)
df["Vol_MA5"] = df["Volume"].rolling(5).mean()
vol_ratio = df["Volume"].iloc[-1] / df["Vol_MA5"].iloc[-1] if df["Vol_MA5"].iloc[-1] > 0 else 1.0

curr_p = df["Close"].iloc[-1]
m5, m13, m37 = df["MA5"].iloc[-1], df["MA13"].iloc[-1], df["MA37"].iloc[-1]
slope_37 = df["MA37"].diff().iloc[-1] # 生命線斜率

# =========================
# 5. 頂部看板 (Metrics)
# =========================
st.title(f"🚀 {stock_id} 診斷報告")
st.caption(f"資料來源：{final_id} ｜ 最後交易日：{df.index[-1].date()}")

c1, c2, c3 = st.columns(3)
c1.metric("目前股價", f"{curr_p:.2f}")

if cost_price > 0 and shares > 0:
    pnl = (curr_p - cost_price) * shares
    pnl_pct = (curr_p / cost_price - 1) * 100
    c2.metric("帳面損益", f"{pnl:,.0f}", f"{pnl_pct:.2f}%")
else:
    c2.metric("今日成交量", f"{df['Volume'].iloc[-1]:,.0f}")

c3.metric("37MA 生命線", f"{m37:.2f}" if not pd.isna(m37) else "資料不足")

# =========================
# 6. K 線圖 (視覺優化版)
# =========================
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="K線"
))

# 調整為台股紅漲綠跌
fig.update_traces(
    increasing_line_color='#FF4136', increasing_fillcolor='#FF4136',
    decreasing_line_color='#3D9970', decreasing_fillcolor='#3D9970'
)

fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="5MA", line=dict(color='#00BFFF', width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["MA37"], name="37MA", line=dict(color='#BA55D3', width=2)))

fig.update_layout(
    height=500, template="plotly_dark", xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

# =========================
# 7. 專業趨勢結構診斷 (垂直流卡片設計)
# =========================
st.markdown("---")
st.subheader("📋 趨勢結構診斷報告")

# 判定核心結論顏色與內容
if any(pd.isna([m5, m13, m37])):
    status_title, status_color, conclusion = "數據加載中", "#808080", "標的資料天數不足，暫不進行結構判讀。"
elif curr_p > m37 and slope_37 > 0 and m5 > m13 > m37:
    status_title, status_color, conclusion = "多頭排列：強勢格局", "#FF4136", "價格穩站生命線，斜率向上，動能充足。"
elif curr_p < m37:
    status_title, status_color, conclusion = "空頭轉弱：偏空格局", "#3D9970", "價格跌破 37MA，中期趨勢受壓，建議保守。"
else:
    status_title, status_color, conclusion = "橫盤整理：方向不明", "#FFA500", "均線交疊拉鋸，暫無明確趨勢，靜待突破。"

# --- 垂直報告呈現 ---
st.markdown(f"""
    <div style="background-color:{status_color}; padding:20px; border-radius:10px; text-align:center; margin-bottom:20px;">
        <h2 style="color:white; margin:0; font-size:24px;">{status_title}</h2>
        <p style="color:white; margin:10px 0 0 0; font-size:16px; opacity:0.9;">{conclusion}</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("#### 📊 技術數據追蹤")
st.write(f"‧ **乖離率**：股價領先 37MA 約 **{((curr_p/m37)-1)*100:.2f}%**")
st.write(f"‧ **量能偵測**：今日成交量為 5 日均量的 **{vol_ratio:.2f} 倍**")

st.markdown("#### 🚩 實戰策略指引")

if any(pd.isna([m5, m13, m37])):
    st.info("數據尚未完整跑出 37 天，建議先參考短線 5MA 操作。")
elif curr_p > m37:
    if vol_ratio >= 1.3:
        st.success("【確認加溫】量價齊揚，市場認同度高。持股者可上移停利點續抱；空手者切忌追高，等回測再看。")
    elif vol_ratio < 0.8:
        st.warning("【量能不足】價格雖美但買盤觀望。需防範高檔假突破，建議不宜在此加碼，耐心等量滾出來。")
    else:
        st.success("【趨勢穩健】目前處於常態推升。只要 37MA 斜率保持向上，操作維持既定節奏。")
else:
    if vol_ratio >= 1.3:
        st.error("【警訊出現】破線帶量是真跌。代表法人或主力正在撤離，建議嚴格執行風險管理，保護本金。")
    else:
        st.error("【緩跌風險】雖然沒爆量，但股價站不回生命線。這種「陰跌」最磨人，暫不攤平，等待底部放量訊號。")

st.divider()
st.caption("🔍 註：診斷結合價格位階與 5 日量能倍率。技術指標為落後指標，投資請務必獨立判斷風險。")
