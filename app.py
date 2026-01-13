import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 盤後分析", layout="wide")
st.title("📈 台股 5MA/13MA 決策分析系統")

# --- 側邊欄：輸入參數 ---
st.sidebar.header("📌 個人持倉設定")
stock_id = st.sidebar.text_input("股票代號", value="2330")
my_cost = st.sidebar.number_input("持有平均價格", value=600.0, step=0.1)
my_shares = st.sidebar.number_input("持有股數 (最小單位: 股)", value=1000, step=1)

# --- 1. 抓取數據功能 (加入防錯) ---
@st.cache_data(ttl=3600)
def get_stock_data(sid):
    dl = DataLoader()
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 抓取日線
    try:
        df = dl.taiwan_stock_daily(stock_id=sid, start_date=start_date)
    except:
        df = pd.DataFrame()

    # 抓取除權息
    try:
        div = dl.taiwan_stock_dividend(stock_id=sid, start_date=start_date)
    except:
        div = pd.DataFrame()
        
    # 抓取新聞
    try:
        news = dl.taiwan_stock_news(stock_id=sid, start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'))
    except:
        news = pd.DataFrame()
        
    return df, div, news

# --- 2. 執行抓取與邏輯運算 ---
df, div, news = get_stock_data(stock_id)

if df is None or df.empty:
    st.error("❌ 抓取失敗：請檢查股票代號是否正確，或 FinMind 伺服器目前繁忙。")
else:
    # 格式整理
    df['date'] = pd.to_datetime(df['date'])
    df['5MA'] = df['close'].rolling(window=5).mean()
    df['13MA'] = df['close'].rolling(window=13).mean()
    
    last_row = df.iloc[-1]
    curr_p = last_row['close']
    m5 = last_row['5MA']
    m13 = last_row['13MA']

    # --- 3. 頂部數據看板 ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("當前股價", f"{curr_p}", f"{((curr_p/df.iloc[-2]['close'])-1)*100:.2f}%")
    c2.metric("持有總市值", f"${(curr_p * my_shares):,.0f}")
    c3.metric("預估損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")

    # --- 4. 繪製圖表 ---
    fig = go.Figure()
    # K線圖
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], 
                                 low=df['
