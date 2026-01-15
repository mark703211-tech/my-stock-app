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
# 2. 數據引擎
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
    st.error(f"❌ 無法取得 {stock_id} 市場資料。請檢查代號正確性或 requirements.txt 設定。")
    st.stop()

# 指標計算
df["MA5"] = df["Close"].rolling(5).mean()
df["MA13"] = df["Close"].rolling(13).mean()
df["MA37"] = df["Close"].rolling(37).mean()
df["Vol_MA5"] = df["Volume"].rolling(5).mean()

# 取得最新數值
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
st.caption(f"交易日：{df.index[-1].date()}")

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
# 6. K 線圖 (柔和配色)
# =========================
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], 
    low=df["Low"], close=df["Close"], name="K線"
))

# 修正配色：莫蘭迪深紅與深綠，降低視覺疲勞
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
# 7. 垂直診斷報告 (修正顏色與語法)
# =========================
st.markdown("---")
st.subheader("📋 趨勢結構診斷報告")

# 顏色判定：採用深色系
if any(pd.isna([m5, m13, m37])):
    bg_color, title, text = "#4a4e69", "數據觀測中", "資料天數不足，暫不進行中期判讀。"
elif curr_p > m37 and slope_37 > 0 and m5 > m13 > m37:
    bg_color, title, text = "#2d4a3e", "多頭排列：強勢格局", "價格穩站生命線，趨勢穩定發散向上。"
elif curr_p < m37:
    bg_color, title, text = "#5d2e2e", "空頭轉弱：偏空格局", "股價低於 37MA，中期壓力尚待消化。"
else:
    bg_color, title, text = "#5f4b32", "橫盤整理：方向不明", "均線交疊拉鋸，動能暫歇，靜待新訊號。"

# 垂直卡片
st.markdown(f"""
    <div style="background-color:{bg_color}; padding:20px; border-radius:12px; border-left: 10px solid rgba(255,255,255,0.15); margin-bottom:20px;">
        <h3 style="color:white; margin:0; font-size:20px; font-weight:bold;">{title}</h3>
        <p style="color:rgba(255,255,255,0.85); margin:10px 0 0 0; font-size:15px; line-height:1.5;">{text}</p>
    </div>
""", unsafe_allow_html=True)

# 數據指標
col_a, col_b = st.columns(2)
with col_a:
    bias_37 = ((curr_p / m37) - 1) * 100 if m37 > 0 else 0
    st.write(f"‧ **37MA 乖離率**：`{bias_37:+.2f}%`")
with col_b:
    st.write(f"‧ **量能倍率**：`{vol_ratio:.2f} 倍`")

# 操作指引
st.markdown("#### 🚩 實戰策略指引")
if any(pd.isna([m5, m13, m37])):
    st.info("新上市標的，建議優先觀察 5MA 與成交量變動。")
elif curr_p > m37:
    if vol_ratio >= 1.3:
        st.success("【確認加溫】量價齊揚，市場參與度高，建議續抱並上移停損。")
    elif vol_ratio < 0.8:
        st.warning("【量能不足】價格雖美但買盤觀望，需防範假突破。")
    else:
        st.success("【節奏穩健】趨勢推進中。只要生命線保持向上，維持原配置。")
else:
    if vol_ratio >= 1.3:
        st.error("【警訊確認】帶量跌破。法人撤離訊號明顯，建議加強風險管理。")
    else
