import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 進階分析", layout="wide")
st.title("📈 台股 5 / 13 / 37 MA 專業決策系統")

# --- 側邊欄：持倉設定 ---
st.sidebar.header("📌 個人持倉設定")
# 獲取原始輸入
stock_input = st.sidebar.text_input("股票代號 (如: 2330 或 5498)", value="2330").strip()

my_cost = st.sidebar.number_input("您的買入平均價格", value=600.0)
my_shares = st.sidebar.number_input("持有總股數", value=1000)

# --- 1. 抓取數據 (上市/上櫃自動切換邏輯) ---
@st.cache_data(ttl=3600)
def get_stock_data(sid):
    # 先嘗試上市 (.TW)，再嘗試上櫃 (.TWO)
    for suffix in [".TW", ".TWO"]:
        target_id = f"{sid}{suffix}"
        ticker = yf.Ticker(target_id)
        df = ticker.history(period="2y")
        if not df.empty:
            return df, ticker.actions, target_id
    return pd.DataFrame(), pd.DataFrame(), None

df_raw, actions, final_id = get_stock_data(stock_input)

if df_raw.empty:
    st.error(f"❌ 找不到代號 '{stock_input}' 的資料。")
    st.info("💡 提示：若是剛更名或下市股票，數據源可能暫未支援。")
else:
    df = df_raw.copy()
    st.sidebar.success(f"✅ 已成功載入: {final_id}")
    
    # 指標計算
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['13MA'] = df['Close'].rolling(window=13).mean()
    df['37MA'] = df['Close'].rolling(window=37).mean()
    
    curr_p = round(df['Close'].iloc[-1], 2)
    m5 = round(df['5MA'].iloc[-1], 2)
    m13 = round(df['13MA'].iloc[-1], 2)
    m37 = round(df['37MA'].iloc[-1], 2)
    
    change_pct = (curr_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100

    # --- 2. 數據看板 ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("當前股價", f"{curr_p}", f"{change_pct:.2f}%")
    c2.metric("預估總損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")
    c3.metric("5MA", f"{m5}")
    c4.metric("13MA", f"{m13}")
    c5.metric("37MA", f"{m37}")

    # --- 3. 繪製圖表 ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#00BFFF', width=1.5), name='5MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['13MA'], line=dict(color='#FF8C00', width=1.5), name='13MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['37MA'], line=dict(color='#BA55D3', width=2), name='37MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="#FF4B4B", annotation_text="成本")

    # 標記除權息
    divs = actions[actions['Dividends'] > 0]
    if not divs.empty:
        divs_in_range = divs[divs.index >= df.index.min()]
        if not divs_in_range.empty:
            fig.add_trace(go.Scatter(x=divs_in_range.index, y=df.loc[df.index.isin(divs_in_range.index), 'High'] * 1.02,
                                     mode='markers', marker=dict(symbol='star', size=10, color='gold'),
                                     name='除權息日'))

    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. AI 策略詳解 ---
    st.subheader("🤖 AI 實戰策略詳解")
    with st.expander("🔍 均線結構與明日操作建議", expanded=True):
        if curr_p > m5 > m13 > m37:
            st.success("🟢 **【多頭排列】**：趨勢極強。若回測 5MA ({m5}) 不破可加碼。")
        elif curr_p < m37:
            st.error(f"🔴 **【趨勢轉空】**：股價破中期線 ({m37})，建議嚴格執行停損或減碼。")
        elif m5 < m13:
            st.warning(f"🟡 **【短期轉弱】**：5MA 已穿過 13MA，短期買盤衰竭，建議減碼 1/3。")
        else:
            st.info("⚪ **【震盪蓄勢】**：均線糾結，建議維持部位，觀察明日是否放量。")

    # --- 5. 歷史數據 ---
    st.divider()
    st.subheader("📅 歷史量價數據 (最後 5 日)")
    recent_df = df[['Close', 'Volume', '5MA', '13MA', '37MA']].tail(5).copy()
    recent_df.columns = ['收盤價', '成交量(股)', '5MA', '13MA', '37MA']
    st.table(recent_df.style.format("{:.2f}"))
