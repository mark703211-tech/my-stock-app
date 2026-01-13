import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股分析", layout="wide")
st.title("📈 台股 5MA/13MA 決策系統")

# --- 側邊欄 ---
st.sidebar.header("📌 個人持倉設定")
stock_id = st.sidebar.text_input("股票代號", value="2330")
my_cost = st.sidebar.number_input("持有平均價格", value=600.0, step=0.1)
my_shares = st.sidebar.number_input("持有股數", value=1000, step=1)

# --- 1. 抓取數據 ---
@st.cache_data(ttl=3600)
def get_all_data(sid):
    dl = DataLoader()
    start_d = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    try:
        # 抓取日線
        df = dl.taiwan_stock_daily(stock_id=sid, start_date=start_d)
        # 抓取除權息 (選填，若失敗則回傳空表)
        try:
            div = dl.taiwan_stock_dividend(stock_id=sid, start_date=start_d)
        except:
            div = pd.DataFrame()
        return df, div
    except:
        return pd.DataFrame(), pd.DataFrame()

df_raw, div_raw = get_all_data(stock_id)

if df_raw.empty:
    st.error("❌ 找不到資料，請確認股票代號（如 2330）。")
else:
    # 數據處理
    df = df_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['5MA'] = df['close'].rolling(window=5).mean()
    df['13MA'] = df['close'].rolling(window=13).mean()
    
    curr_p = df.iloc[-1]['close']
    m5 = df.iloc[-1]['5MA']
    m13 = df.iloc[-1]['13MA']

    # --- 2. 數據看板 ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("當前股價", f"{curr_p}")
    c2.metric("預估損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")
    c3.metric("5MA / 13MA", f"{m5:.1f} / {m13:.1f}")

    # --- 3. 圖表 ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='K線'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['5MA'], line=dict(color='blue', width=2), name='5MA'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['13MA'], line=dict(color='orange', width=2), name='13MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="red", annotation_text="成本線")
    
    fig.update_layout(height=450, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. AI 決策建議 ---
    st.subheader("🤖 交易建議")
    if curr_p > m5 and m5 > m13:
        st.success(f"🌟 強勢多頭：目前股價在均線之上，建議繼續持有。若回測 5MA ({m5:.1f}) 不破可加碼。")
    elif curr_p < m5 and curr_p > m13:
        st.warning(f"⚠️ 短期轉弱：股價跌破 5MA，建議停止加碼。觀察 13MA ({m13:.1f}) 是否有支撐。")
    elif curr_p < m13:
        st.error(f"🚨 趨勢轉空：股價已破 13MA，建議執行減碼或出清以避開下行風險。")
    else:
        st.write("🔄 橫盤整理中，建議續抱觀望。")

    st.caption("註：本工具僅供參考，投資請自行評估風險。數據來源：FinMind")
