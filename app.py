import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 盤後分析助手", layout="wide")
st.title("📈 台股 5MA/13MA 決策分析系統")

# --- 側邊欄：輸入參數 ---
st.sidebar.header("個人持倉設定")
stock_id = st.sidebar.text_input("股票代號", value="2330")
my_cost = st.sidebar.number_input("持有股價", value=600.0, step=0.1)
my_shares = st.sidebar.number_input("持有股數 (股)", value=1000, step=1)

# --- 1. 抓取數據 ---
@st.cache_data(ttl=3600) # 快取一小時，避免重複抓取
def get_data(sid):
    dl = DataLoader()
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    # 抓取日線
    df = dl.taiwan_stock_daily(stock_id=sid, start_date=start_date)
    # 抓取除權息資料
    div = dl.taiwan_stock_dividend(stock_id=sid, start_date=start_date)
    return df, div

try:
    df, div = get_data(stock_id)
    df['date'] = pd.to_datetime(df['date'])
    div['date'] = pd.to_datetime(div['ex_dividend_date'])

    # --- 2. 計算指標 ---
    df['5MA'] = df['close'].rolling(window=5).mean()
    df['13MA'] = df['close'].rolling(window=13).mean()

    # --- 3. 繪製圖表 (Plotly 互動圖) ---
    fig = go.Figure()
    # K線
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], 
                                 low=df['low'], close=df['close'], name='K線'))
    # 均線
    fig.add_trace(go.Scatter(x=df['date'], y=df['5MA'], line=dict(color='blue', width=1.5), name='5MA'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['13MA'], line=dict(color='orange', width=1.5), name='13MA'))
    
    # 成本線
    fig.add_hline(y=my_cost, line_dash="dash", line_color="red", annotation_text="我的成本")

    # 標記除權息 (小記號)
    div_in_range = div[div['date'] >= df['date'].min()]
    fig.add_trace(go.Scatter(x=div_in_range['date'], y=df.loc[df['date'].isin(div_in_range['date']), 'high'],
                             mode='markers+text', marker_symbol='star', marker_size=10,
                             text="除權息", textposition="top center", name='除權息事件'))

    st.plotly_chart(fig, use_container_width=True)

    # --- 4. AI 決策建議欄 ---
    st.subheader("🤖 AI 盤後決策建議")
    last_row = df.iloc[-1]
    curr_p = last_row['close']
    m5, m13 = last_row['5MA'], last_row['13MA']
    profit = (curr_p - my_cost) * my_shares

    col1, col2, col3 = st.columns(3)
    col1.metric("當前股價", f"{curr_p}", f"{((curr_p/df.iloc[-2]['close'])-1)*100:.2f}%")
    col2.metric("預估損益", f"${profit:,.0f}", f"{(curr_p-my_cost)/my_cost*100:.2f}%")
    
    # 判斷邏輯
    if curr_p > m5 and m5 > m13:
        status, color = "建議持有 / 可適量追加", "green"
    elif curr_p < m5 and curr_p > m13:
        status, color = "短期轉弱 / 減碼觀察", "orange"
    else:
        status, color = "破位建議賣出", "red"
    
    st.markdown(f"### 核心行動指引：:{color}[{status}]")
    st.info(f"明日觀盤重點：5MA({m5:.1f}) 為短期防守位，若開盤跳空跌破則應執行減碼。")

    # --- 5. 關心新聞 (FinMind 新聞串接) ---
    st.subheader("📰 相關市場要聞")
    news_df = dl.taiwan_stock_news(stock_id=stock_id, start_date=(datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'))
    if not news_df.empty:
        for i, row in news_df.head(5).iterrows():
            st.write(f"**[{row['date']}]** {row['title']}")
            st.caption(f"連結: {row['link']}")
    else:
        st.write("目前暫無相關新聞。")

except Exception as e:
    st.error(f"資料抓取失敗，請檢查股票代號是否正確。錯誤訊息: {e}")
