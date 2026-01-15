import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =========================
# 1. 頁面配置
# =========================
st.set_page_config(
    page_title="🟢 持股結構診斷工具",
    page_icon="📈",
    layout="centered"
)

# =========================
# 2. 數據引擎 (強化容錯機制)
# =========================
@st.cache_data(ttl=3600)
def fetch_stock_data(sid: str):
    sid = sid.strip().upper()
    for suffix in [".TW", ".TWO"]:
        try:
            target = f"{sid}{suffix}"
            ticker = yf.Ticker(target)
            df = ticker.history(period="2y")
            if not df.empty:
                return df, target
        except Exception:
            continue
    return pd.DataFrame(), None

# =========================
# 3. 側邊欄設定
# =========================
st.sidebar.header("💰 持倉設定")
stock_id = st.sidebar.text_input("輸入代碼 (例如: 5498, 00980A)", value="5498").strip()
cost_price = st.sidebar.number_input("買入均價", min_value=0.0, step=0.1, format="%.2f")
shares = st.sidebar.number_input("持有股數", min_value=0, step=1000)

# =========================
# 4. 加載與計算
# =========================
df, final_id = fetch_stock_data(stock_id)

if df.empty:
    st.error(f"❌ 無法取得 {stock_id} 市場資料。請確認 GitHub 專案中已建立包含 'yfinance' 的 requirements.txt 檔案。")
    st.stop()

# 核心指標計算
df["MA5"] = df["Close"].rolling(5).mean()
df["MA13"] = df["Close"].rolling(13).mean()
df["MA37"] = df["Close"].rolling(37).mean()
df["Vol_MA5"] = df["Volume"].rolling(5).mean()

# 取得最新數據
curr_p = df["Close"].iloc[-1]
m5 = df["MA5"].iloc[-1]
m13 = df["MA13"].iloc[-1]
m37 = df["MA37"].iloc[-1]
vol_ratio = df["Volume"].iloc[-1] / df["Vol_MA5"].iloc[-1] if df["Vol_MA5"].iloc[-1] > 0 else 1.0
slope_37 = df["MA37"].diff().iloc[-1]

# =========================
# 5. 數據看板 (Metrics)
# =========================
st.title(f"🚀 {stock_id} 結構診斷")
st.caption(f"數據來源：{final_id} ｜ 交易日：{df.index[-1].date()}")

c1, c2, c3 = st.columns(3)
c1.metric("目前股價", f"{curr_p:.2f}")

if cost_price > 0 and shares > 0:
    pnl = (curr_p - cost_price) * shares
    pnl_pct = (curr_p / cost_price - 1) * 100
    c2.metric("帳面損益", f"${pnl:,.0f}", f"{pnl_pct:+.2f}%")
else:
    c2.metric("今日成交量", f"{df['Volume'].iloc[-1]:,.0f}")

c3.metric("37MA 生命線", f"{m37:.2f}" if not pd.isna(m37) else "資料不足")

# =========================
# 6. K 線圖 (配色優化)
# =========================
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], 
    low=df["Low"], close=df["Close"], name="K線"
))

# 採用更穩重且不刺眼的配色
fig.update_traces(
    increasing_line_color='#bc4749', increasing_fillcolor='#bc4749',
    decreasing_line_color='#6a994e', decreasing_fillcolor='#6a994e'
)

fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="5MA", line=dict(color='#a8dadc', width=1.2)))
fig.add_trace(go.Scatter(x=df.index, y=df["MA37"], name="37MA", line=dict(color='#9b5de5', width=2)))

fig.update_layout(
    height=450, 
    template="plotly_dark", 
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

# =========================
# 7. 垂直診斷報告 (莫蘭迪配色)
# =========================
st.markdown("---")
st.subheader("📋 趨勢結構診斷")

# 顏色判定與結論設定
if any(pd.isna([m5, m13, m37])):
    bg_color, title, text = "#4a4e69", "數據觀測中", "資料天數不足，暫不進行中期結構判讀。"
elif curr_p > m37 and slope_37 > 0 and m5 > m13 > m37:
    bg_color, title, text = "#2d4a3e", "多頭排列：強勢格局", "價格站穩生命線，斜率向上，多頭趨勢延伸。"
elif curr_p < m37:
    bg_color, title, text = "#5d2e2e", "空頭轉弱：偏空格局", "股價低於生命線，趨勢受壓，建議保守防禦。"
else:
    bg_color, title, text = "#5f4b32", "橫盤整理：方向不明", "均線交疊拉鋸，動能暫歇，靜待突破訊號。"

# 診斷卡片設計
st.markdown(
