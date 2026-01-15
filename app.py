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
# =========================
# 9. 專業結構診斷報告
# =========================
st.markdown("---")
st.subheader("📋 趨勢結構診斷")

# 補齊量能計算邏輯
df["Vol_MA5"] = df["Volume"].rolling(5).mean()
vol_ratio = df["Volume"].iloc[-1] / df["Vol_MA5"].iloc[-1] if df["Vol_MA5"].iloc[-1] > 0 else 1.0

# 判定核心結論 (標題與顏色)
if any(pd.isna([m5, m13, m37])):
    status_title = "數據加載中"
    status_color = "#808080" # 灰色
    conclusion = "新掛牌標的，指標尚在暖機階段。"
elif curr_p > m37 and m5 > m13 > m37:
    status_title = "多頭排列：強勢格局"
    status_color = "#FF4136" # 紅色 (多頭)
    conclusion = "價格站穩生命線，均線發散向上，動能充足。"
elif curr_p < m37:
    status_title = "空頭轉弱：偏空格局"
    status_color = "#3D9970" # 綠色 (台股空頭)
    conclusion = "價格跌破 37MA，中期趨勢受阻，需謹慎面對。"
else:
    status_title = "橫盤整理：方向不明"
    status_color = "#FFA500" # 橘色
    conclusion = "均線糾結，短中期力量拉鋸，靜待突破訊號。"

# --- 垂直報告呈現 ---
with st.container():
    # 1. 核心結論區 (大標題卡片)
    st.markdown(f"""
        <div style="background-color:{status_color}; padding:15px; border-radius:10px; text-align:center;">
            <h2 style="color:white; margin:0;">{status_title}</h2>
            <p style="color:white; margin:5px 0 0 0; opacity:0.9;">{conclusion}</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. 數據細節 (條列式)
    st.markdown("#### 📊 技術數據摘要")
    st.write(f"‧ **位置現況**：股價相較 37MA 乖離為 {((curr_p/m37)-1)*100:.2f}%")
    st.write(f"‧ **量能狀態**：今日成交量為 5 日均量的 **{vol_ratio:.2f} 倍**")
    
    # 3. 戰略指引 (長條對話框)
    st.markdown("#### 🚩 實戰操作指引")
    
    if any(pd.isna([m5, m13, m37])):
        st.info("目前數據天數不足 37 天，技術指標僅供參考，應以基本面或消息面為準。")
    elif curr_p > m37:
        if vol_ratio >= 1.3:
            st.success("【確認加溫】量價齊揚，市場認同度高。持股者可上移停利點續抱；空手者切忌追噴，等回測 5MA 守穩再看。")
        elif vol_ratio < 0.8:
            st.warning("【量能不足】價格雖美但買盤觀望。這類情況容易出現「假突破」，不建議在此處重倉參與，耐心等量滾出來。")
        else:
            st.success("【常態推升】趨勢穩健。只要 37MA 斜率保持向上，操作上維持既定節奏即可。")
    else:
        if vol_ratio >= 1.3:
            st.error("【警訊出現】破線帶量是真跌。代表法人或大戶正在撤離，這時不要談信仰，先保護本金才是上策。")
        else:
            st.error("【緩跌風險】雖然沒爆量，但股價站不回生命線。這種「陰跌」最磨人，建議轉為防守模式，暫不攤平。")

# --- 底部備註 ---
st.markdown("---")
st.caption("🔍 註：診斷邏輯結合價格位階與 5 日量能倍率。技術指標為落後指標，投資請務必獨立判斷風險。")
# =========================
# 9. AI 戰略對話室
# =========================
# =========================
# 9. AI 戰略對話室
# =========================
st.subheader("🤖 AI 戰略對話室")

# 先補齊計算邏輯 (計算量能倍率)
df["Vol_MA5"] = df["Volume"].rolling(5).mean()
vol_ratio = df["Volume"].iloc[-1] / df["Vol_MA5"].iloc[-1] if df["Vol_MA5"].iloc[-1] > 0 else 1.0

with st.expander("📊 查看診斷結論與操作戰略", expanded=True):
    col_tech, col_talk = st.columns([1, 1.2])

    # ----- 左側：核心診斷 (數據導向) -----
    with col_tech:
        st.markdown("#### 🔍 核心診斷")
        if any(pd.isna([m5, m13, m37])):
            st.info("⚠️ 數據基數不足，暫不判定。")
        elif curr_p > m37 and m5 > m13 > m37:
            st.success("✅ 結構：多頭排列")
            st.write(f"‧ 股價站穩 37MA ({m37:.2f})\n‧ 均線黃金發散\n‧ 量能表現：{vol_ratio:.2f}倍")
        elif curr_p < m37:
            st.error("❌ 結構：趨勢走空")
            st.write(f"‧ 股價跌破 37MA ({m37:.2f})\n‧ 賣壓尚未消化\n‧ 量能表現：{vol_ratio:.2f}倍")
        else:
            st.warning("⚖️ 結構：區間震盪")
            st.write("‧ 均線糾結中\n‧ 價格無明確方向\n‧ 等待關鍵突破")

    # ----- 右側：戰略指引 (接地氣實戰) -----
    with col_talk:
        st.markdown("#### 🧠 戰略指引")
        if any(pd.isna([m5, m13, m37])):
            st.write("這標的還太新，技術指標還在「暖機」。現在看到的線都不準，建議先看量價關係就好。")
        
        elif curr_p > m37:
            if vol_ratio >= 1.3:
                st.write("**「車速正在加快。」**\n\n不僅站上生命線，連量都滾出來了，代表這波是真的。短線不用急著出，讓利潤跑一下，但別在噴發時重倉追入。")
            elif vol_ratio < 0.8:
                st.write("**「位階不錯，但沒人跟。」**\n\n雖然還在支撐上，但成交量太小。這就像是車子停在坡道上但沒踩油門，短期內會以橫盤消磨耐心為主。")
            else:
                st.write("**「順著趨勢走。」**\n\n目前節奏很穩。只要不跌破 37MA，都不用自己嚇自己。適合分批佈局或續抱。")

        elif curr_p < m37:
            if vol_ratio >= 1.3:
                st.write("**「有人在撤退，別接飛刀。」**\n\n跌破生命線還帶量，這不是洗盤，是警訊。先把本金收回來，等站回 37MA 再說。")
            else:
                st.write("**「慢火溫水煮青蛙。」**\n\n雖然沒爆量慘跌，但緩步下探更折磨人。建議維持低水位觀望，不要輕易攤平。")

    # ----- 底部：時事與心法 -----
    st.divider()
    st.markdown("##### 💡 實戰提醒")
    st.write(
        f"目前 {stock_id} 的表現不僅是公司基本面，更受到**大盤氣氛**與**同族群連動**的影響。"
        "如果這兩天出現「量縮不跌」，那是轉強的前兆；反之，「爆量不漲」則要提防主力出貨。"
    )
    st.caption("※ 戰略指引僅供邏輯參考，投資請務必獨立判斷。")

