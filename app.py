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
st.subheader("AI 結構判讀（技術 × 白話）")

with st.expander("點我看 AI 怎麼想", expanded=True):

    col_left, col_right = st.columns(2)

    # ===== 技術面摘要（冷靜版）=====
    with col_left:
        st.markdown("### 📊 技術面摘要")

        if any(pd.isna([m5, m13, m37, vol_ratio])):
            st.info("均線或成交量資料不足，暫不進行結構判讀。")

        elif curr_p > m37 and m5 > m13 > m37:
            st.success("中期結構偏多")
            st.write(
                f"- 股價位於 37MA ({m37:.2f}) 之上\n"
                f"- 均線呈多頭排列\n"
                f"- 量能倍率：約 {vol_ratio:.2f} 倍"
            )

        elif curr_p < m37:
            st.warning("中期結構轉弱")
            st.write(
                f"- 股價跌破 37MA ({m37:.2f})\n"
                f"- 均線結構遭破壞\n"
                f"- 量能倍率：約 {vol_ratio:.2f} 倍"
            )

        else:
            st.info("結構整理中")
            st.write(
                "- 股價仍在中期均線附近震盪\n"
                "- 均線糾結，方向尚未明確"
            )

    # ===== 白話解釋（接地氣版）=====
    with col_right:
        st.markdown("### 🧠 白話怎麼看")

        if any(pd.isna([m5, m13, m37, vol_ratio])):
            st.write(
                "這檔股票掛牌時間還不長，很多技術指標其實還沒跑完整。"
                "現在硬要判斷多空，反而容易被短線波動影響。"
            )

        elif curr_p > m37 and vol_ratio >= 1.3:
            st.write(
                "簡單說就是：**現在在車道上，而且後面真的有車在推。**\n\n"
                "不只是價格站上來，連成交量都有放大，代表不是少數人在自嗨，"
                "而是市場真的有人認同這個價位。短線不用急著跑，但也不適合追高亂衝。"
            )

        elif curr_p > m37 and vol_ratio < 0.8:
            st.write(
                "位置其實不差，但問題是**人不夠多**。\n\n"
                "價格撐得住，可是成交量縮，代表大家觀望氣氛濃。"
                "這種時候通常不會馬上噴，但也不一定會崩，比較像在等一個理由。"
            )

        elif curr_p < m37 and vol_ratio >= 1.3:
            st.write(
                "這裡要稍微小心一點。\n\n"
                "跌破重要均線時，成交量還放大，代表是真的有人在撤退，"
                "不是單純被洗一下。這種情況下，保守一點通常不是壞事。"
            )

        else:
            st.write(
                "現在就是**不上不下、卡在中間**的狀態。\n\n"
                "買了不一定馬上錯，但也很難馬上對。"
                "如果你不是很有把握，這種盤勢通常是耐心比操作重要。"
            )

    # ===== 時事 / 市場情境補充 =====
    st.markdown("---")
    st.markdown("### 📰 市場氣氛補充（情境參考）")

    st.write(
        "最近市場普遍在關注 **政策動向、國際利率走向、以及熱門題材輪動速度**。"
        "這類時間點常見的狀況是：\n\n"
        "- 有題材的股票會突然放量衝一段\n"
        "- 沒被點到名的，就算基本面不差，也容易在原地磨\n\n"
        "因此，現在的價格表現，往往不只是在反映公司本身，"
        "而是在反映「有沒有被市場選中」。"
    )

    st.caption(
        "提醒：以上為技術結構與市場情境解讀，非投資建議。"
    )
