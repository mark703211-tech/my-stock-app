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
# 2. 數據引擎 (萬用偵測機制)
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
st.sidebar.header("💰 持倉設定")
stock_id = st.sidebar.text_input("輸入代碼 (例如: 5498, 00980A)", value="5498").strip()
cost_price = st.sidebar.number_input("買入均價", min_value=0.0, step=0.1)
shares = st.sidebar.number_input("持有股數", min_value=0, step=1000)

# =========================
# 4. 加載與計算
# =========================
df, final_id = fetch_stock_data(stock_id)

if df.empty:
    st.error(f"❌ 無法取得 {stock_id} 市場資料。請確認代號正確並已建立 requirements.txt。")
    st.stop()

# 指標計算
df["MA5"] = df["Close"].rolling(5).mean()
df["MA13"] = df["Close"].rolling(13).mean()
df["MA37"] = df["Close"].rolling(37).mean()
df["Vol_MA5"] = df["Volume"].rolling(5).mean()
vol_ratio = df["Volume"].iloc[-1] / df["Vol_MA5"].iloc[-1] if df["Vol_MA5"].iloc[-1] > 0 else 1.0

curr_p = df["Close"].iloc[-1]
m5, m13, m37 = df["MA5"].iloc[-1], df["MA13"].iloc[-1], df["MA37"].iloc[-1]
slope_37 = df["MA37"].diff().iloc[-1]

# =========================
# 5. 數據看板
# =========================
st.title(f"🚀 {stock_id} 結構診斷")
st.caption(f"資料來源：{final_id} ｜ 交易日：{df.index[-1].date()}")

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
# 6. K 線圖 (配色微調)
# =========================
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="K線"
))

# 採用稍淡的紅綠色，降低視覺衝擊
fig.update_traces(
    increasing_line_color='#e63946', increasing_fillcolor='#e63946',
    decreasing_line_color='#2a9d8f', decreasing_fillcolor='#2a9d8f'
)

fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="5MA", line=dict(color='#457b9d', width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["MA37"], name="37MA", line=dict(color='#a29bfe', width=2)))

fig.update_layout(
    height=450, template="plotly_dark", xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
