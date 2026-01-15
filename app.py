import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =========================
# 1. Page Config
# =========================
st.set_page_config(
    page_title="持股結構 × 量能診斷工具",
    page_icon="📊",
    layout="centered"
)

# =========================
# 2. Data Fetch
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
# 3. Sidebar
# =========================
st.sidebar.header("持倉資訊（選填）")

stock_id = st.sidebar.text_input(
    "股票代號（例：2330 / 00980A）",
    value="5498"
)

cost_price = st.sidebar.number_input(
    "買入均價",
    min_value=0.0,
    step=0.1
)

shares = st.sidebar.number_input(
    "持有股數",
    min_value=0,
    step=1000
)

# =========================
# 4. Load Data
# =========================
df, final_id = fetch_stock_data(stock_id)

if df.empty:
    st.error(f"無法取得 {stock_id} 的市場資料")
    st.stop()

# =========================
# 5. Indicators
# =========================
df["MA5"] = df["Close"].rolling(5).mean()
df["MA13"] = df["Close"].rolling(13).mean()
df["MA37"] = df["Close"].rolling(37).mean()

df["VOL_MA20"] = df["Volume"].rolling(20).mean()

curr_p = df["Close"].iloc[-1]
m5 = df["MA5"].iloc[-1]
m13 = df["MA13"].iloc[-1]
m37 = df["MA37"].iloc[-1]

vol_today = df["Volume"].iloc[-1]
vol_ma20 = df["VOL_MA20"].iloc[-1]
vol_ratio = vol_today / vol_ma20 if vol_ma20 > 0 else None

slope_37 = df["MA37"].diff().iloc[-1]

# =========================
# 6. Header
# =========================
st.title(f"{stock_id} 結構 × 量能診斷")
st.caption(f"資料來源：{final_id} ｜ 最後交易日：{df.index[-1].date()}")

# =========================
# 7. Metrics
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("目前股價", f"{curr_p:.2f}")

if cost_price > 0 and shares > 0:
    pnl = (curr_p - cost_price) * shares
    pnl_pct = (curr_p / cost_price - 1) * 100
    c2.metric(
        "帳面價差損益",
        f"{pnl:,.0f}",
        f"{pnl_pct:.2f}%",
        help="未計入股息、除權息與交易成本"
    )
else:
    if vol_today == 0:
        c2.metric("最近成交量", "今日無成交")
    else:
        c2.metric("今日成交量", f"{vol_today:,.0f} 股")

c3.metric(
    "37MA（自訂中期均線）",
    f"{m37:.2f}" if not pd.isna(m37) else "資料不足"
)

# =========================
# 8. Chart
# =========================
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df.index,
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    name="K線"
))

fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="5MA"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA13"], name="13MA"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA37"], name="37MA", line=dict(width=2)))

fig.update_layout(
    height=520,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10)
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# 9. Structural + Volume Interpretation
# =========================
st.subheader("結構判讀（結合成交量可信度）")

with st.expander("展開分析說明", expanded=True):

    if any(pd.isna([m5, m13, m37, vol_ma20])):
        st.info("資料尚未完整，暫不進行結構與量能判讀。")

    elif curr_p > m37 and slope_37 > 0 and m5 > m13 > m37:
        st.success("中期結構偏多")

        if vol_ratio and vol_ratio >= 1.3:
            st.caption("成交量高於近 20 日均量，價格結構具備市場共識支撐。")
        elif vol_ratio and vol_ratio < 0.8:
            st.caption("成交量低於均量，追價意願不足，需留意動能衰退。")
        else:
            st.caption("成交量處於正常區間，結構訊號可信度中性。")

    elif curr_p < m37 and slope_37 < 0:
        st.warning("中期結構轉弱風險升高")

        if vol_ratio and vol_ratio >= 1.3:
            st.caption("跌破均線伴隨放量，需留意結構持續轉弱可能。")
        else:
            st.caption("跌破均線但未放量，仍需觀察是否形成有效跌破。")

    elif curr_p > m37 and curr_p < m5:
        st.info("高檔整理區")

        if vol_ratio and vol_ratio < 0.8:
            st.caption("整理期間量能偏低，可能進入時間換空間階段。")
        else:
            st.caption("整理期間量能尚可，需觀察是否重新轉強。")

    else:
        st.info("結構不明確")
        st.caption("均線糾結或量價不同步，市場尚未形成共識。")

    st.caption(
        "注意：ETF、槓桿型商品與個股行為差異極大，本工具僅提供技術結構與量能參考。"
    )
