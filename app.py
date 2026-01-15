import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =========================
# 1. Page Config
# =========================
st.set_page_config(
    page_title="🟢 持股結構診斷工具",
    page_icon="📊",
    layout="centered"
)

# =========================
# 2. Data Engine
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
# 3. Sidebar – Position Input
# =========================
st.sidebar.header("💰 持倉資訊（選填）")

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
    st.error(f"❌ 無法取得 {stock_id} 的市場資料，請檢查代號是否正確。")
    st.stop()

# =========================
# 5. Indicator Calculation
# =========================
df["MA5"] = df["Close"].rolling(5).mean()
df["MA13"] = df["Close"].rolling(13).mean()
df["MA37"] = df["Close"].rolling(37).mean()

curr_p = df["Close"].iloc[-1]
m5 = df["MA5"].iloc[-1]
m13 = df["MA13"].iloc[-1]
m37 = df["MA37"].iloc[-1]

# 均線方向（斜率判定）
slope_13 = df["MA13"].diff().iloc[-1]
slope_37 = df["MA37"].diff().iloc[-1]

# =========================
# 6. Header
# =========================
st.title(f"🚀 {stock_id} 結構診斷")
st.caption(f"資料來源：{final_id} ｜ 最後交易日：{df.index[-1].date()}")

# =========================
# 7. Metrics (整合微調：成交量輔助顯示)
# =========================
c1, c2, c3 = st.columns(3)

c1.metric("目前股價", f"{curr_p:.2f}")

# 微調點：若未輸入成本資訊，則顯示今日成交量
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
    today_vol = df["Volume"].iloc[-1]
    c2.metric("今日成交量", f"{today_vol:,.0f} 股")

c3.metric(
    "37MA（中期生命線）",
    f"{m37:.2f}" if not pd.isna(m37) else "資料不足"
)

# =========================
# 8. Chart (整合微調：台股配色習慣)
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

# 微調點：調整 K 線為紅漲綠跌
fig.update_traces(
    increasing_line_color='#FF4136', increasing_fillcolor='#FF4136',
    decreasing_line_color='#3D9970', decreasing_fillcolor='#3D9970'
)

fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="5MA", line=dict(color='#00BFFF', width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["MA13"], name="13MA", line=dict(color='#FF8C00', width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["MA37"], name="37MA", line=dict(color='#BA55D3', width=2)))

fig.update_layout(
    height=520,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# 9. Structural Interpretation
# =========================
st.subheader("🤖 AI 結構判讀（非操作建議）")

with st.expander("展開判讀邏輯與建議", expanded=True):

    if any(pd.isna([m5, m13, m37])):
        st.info("均線資料尚未完整，僅供價格觀察，不進行結構判讀。")

    elif curr_p > m37 and slope_37 > 0 and m5 > m13 > m37:
        st.success("**🟢 中期結構偏多**")
        st.write(
            f"價格穩定在 37MA ({m37:.2f}) 之上，且均線呈現多頭排列。 "
            "代表目前趨勢健康且斜率向上，操作上建議順勢而為，不輕易預設高點。"
        )

    elif curr_p < m37 and slope_37 < 0:
        st.error("**🔴 中期結構轉弱風險升高**")
        st.write(
            f"目前股價已跌破 37MA ({m37:.2f}) 且該均線開始下彎。 "
            "這通常代表中期趨勢進入空方盤整，建議嚴格控管部位，切勿盲目加碼。"
        )

    elif curr_p > m37 and curr_p < m5:
        st.warning("**🟡 高檔整理區**")
        st.write(
            "股價仍在中期結構支撐之上，但短期動能明顯降溫並跌破短均。 "
            "屬於典型的獲利回吐或整理型態，需靜待 5MA 重新站回方有新動能。"
        )

    else:
        st.info("**⚪ 結構不明確**")
        st.write(
            "目前的均線糾結或長短均方向不一，市場尚未給出明確的趨勢訊號。 "
            "建議在此階段保持耐心，等待更明顯的突破或回測訊號出現。"
        )

    st.divider()
    st.caption(
        "注意：本工具僅根據技術分析指標進行結構判讀。債券 ETF (如 00980A)、槓桿型商品之邏輯與個股不同，請綜合評估。"
    )
