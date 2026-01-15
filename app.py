import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =========================
# 1. 頁面配置
# =========================
st.set_page_config(
    page_title="🟢 持股診斷：AI 戰略戰情室",
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
st.sidebar.header("💰 實戰持倉設定")
stock_id = st.sidebar.text_input("輸入代碼 (例如: 5498, 00980A)", value="5498").strip()
cost_price = st.sidebar.number_input("買入均價", min_value=0.0, step=0.1, format="%.2f")
shares = st.sidebar.number_input("持有股數", min_value=0, step=1000)

# =========================
# 4. 加載與計算
# =========================
df, final_id = fetch_stock_data(stock_id)

if df.empty:
    st.error(f"❌ 找不到 {stock_id}。請確認代碼正確或檢查網路。")
    st.stop()

# 核心指標計算
df["MA5"] = df["Close"].rolling(5).mean()
df["MA37"] = df["Close"].rolling(37).mean()
df["Vol_MA5"] = df["Volume"].rolling(5).mean()

# 最新數據
curr_p = float(df["Close"].iloc[-1])
m37 = float(df["MA37"].iloc[-1])
vol_ratio = float(df["Volume"].iloc[-1] / df["Vol_MA5"].iloc[-1]) if df["Vol_MA5"].iloc[-1] > 0 else 1.0
slope_37 = float(df["MA37"].diff().iloc[-1])
bias_37 = ((curr_p / m37) - 1) * 100 if m37 > 0 else 0

# =========================
# 5. 數據看板
# =========================
st.title(f"🚀 {stock_id} 結構診斷報告")
st.caption(f"交易日：{df.index[-1].date()} ｜ 數據源：{final_id}")

c1, c2, c3 = st.columns(3)
c1.metric("目前價位", f"{curr_p:.2f}")

if cost_price > 0 and shares > 0:
    pnl = (curr_p - cost_price) * shares
    pnl_pct = (curr_p / cost_price - 1) * 100
    c2.metric("真實損益", f"${pnl:,.0f}", f"{pnl_pct:+.2f}%")
else:
    c2.metric("成交量", f"{df['Volume'].iloc[-1]:,.0f}")

c3.metric("37MA 生命線", f"{m37:.2f}" if not pd.isna(m37) else "計算中")

# =========================
# 6. K 線圖
# =========================
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], 
    low=df["Low"], close=df["Close"], name="K線"
))
fig.update_traces(increasing_line_color='#bc4749', increasing_fillcolor='#bc4749',
                  decreasing_line_color='#6a994e', decreasing_fillcolor='#6a994e')
fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], name="5MA", line=dict(color='#a8dadc', width=1.2)))
fig.add_trace(go.Scatter(x=df.index, y=df["MA37"], name="37MA", line=dict(color='#9b5de5', width=2)))
fig.update_layout(height=400, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# =========================
# 7. 垂直診斷報告 (含乖離率影響判讀)
# =========================
st.markdown("---")
st.subheader("📋 趨勢結構診斷")

# 判定結論背景與標題
if curr_p > m37 and slope_37 > 0:
    bg_color, title, text = "#2d4a3e", "多頭結構：順風局", "價格穩站在生命線上，目前處於健康的上升軌道。"
elif curr_p < m37:
    bg_color, title, text = "#5d2e2e", "趨勢轉弱：逆風局", "跌破生命線，代表空頭掌握主導權，不宜硬碰硬。"
else:
    bg_color, title, text = "#5f4b32", "區間震盪：磨人局", "方向不明，股價在生命線附近徘徊，靜待表態。"

st.markdown(f"""
    <div style="background-color:{bg_color}; padding:20px; border-radius:12px; border-left: 10px solid rgba(255,255,255,0.15); margin-bottom:20px;">
        <h3 style="color:white; margin:0; font-size:20px; font-weight:bold;">{title}</h3>
        <p style="color:rgba(255,255,255,0.85); margin:10px 0 0 0; font-size:15px; line-height:1.5;">{text}</p>
    </div>
""", unsafe_allow_html=True)

# 🚩 戰略指引 (將乖離率與量能結合)
st.markdown("#### 🚩 AI 戰略戰情室")

# 1. 針對乖離率的影響進行分析
bias_analysis = ""
if bias_37 > 10:
    bias_analysis = f"⚠️ **注意過熱風險**：目前的乖離率高達 `{bias_37:.2f}%`，代表股價離 37MA 太遠了，這就像皮球彈得太高，**隨時可能引發獲利了結的賣壓回測**。建議不要在此加碼。"
elif bias_37 < -10:
    bias_analysis = f"📉 **注意跌深反彈**：乖離率來到 `{bias_37:.2f}%`，股價嚴重低於 37MA，**技術性反彈的機會正在增加**。雖然還沒轉強，但這時殺低通常不是明智之舉。"
else:
    bias_analysis = f"✅ **乖離適中**：目前乖離率為 `{bias_37:.2f}%`，股價與平均成本距離合理，**走勢較為紮實，沒有過熱或超跌的極端現象。**"

st.info(bias_analysis)

# 2. 綜合量能與位階的實戰指引
if curr_p > m37:
    if vol_ratio >= 1.3:
        st.success("**「油門踩很深，動能充沛！」**\n\n量價齊揚，這波動能是真的。持股者可上移停利防線續抱；若乖離率沒過熱，則是強勢標的。")
    elif vol_ratio < 0.8:
        st.warning("**「位階不錯，但沒人理。」**\n\n雖然股價在上面，但成交量縮得太厲害。這就像車子空有外殼但沒汽油，小心出現「假突破」後的虛弱回測。")
    else:
        st.success("**「節奏穩健，順勢而為。」**\n\n目前處於常態推升，沒有異常爆量或萎縮。順著生命線斜率慢慢抱著就好。")
else:
    if vol_ratio >= 1.3:
        st.error("**「有人在撤退，別當最後一個。」**\n\n帶量跌破生命線是危險訊號。大戶撤離時，這條線會從支撐變壓力。先保護本金，不要盲目談信仰。")
    else:
        st.error("**「溫水煮青蛙，耐心被磨平。」**\n\n雖然賣壓不重，但站不回生命線代表買盤極度虛弱。建議保持觀望，等股價重新站回 37MA 才是重生契機。")

st.divider()
st.caption("🔍 註：診斷結合價格位階與量能。技術指標具滯後性，請務必獨立判斷。")
