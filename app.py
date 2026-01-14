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
raw_id = st.sidebar.text_input("股票代號 (例如: 2330)", value="2330")
stock_id = f"{raw_id}.TW" if ".TW" not in raw_id.upper() else raw_id

my_cost = st.sidebar.number_input("您的買入平均價格", value=600.0)
my_shares = st.sidebar.number_input("持有總股數 (含零股)", value=1000)

# --- 1. 抓取數據 (yfinance) ---
@st.cache_data(ttl=3600)
def get_full_data(sid):
    ticker = yf.Ticker(sid)
    df = ticker.history(period="2y")
    actions = ticker.actions
    return df, actions

df_raw, actions = get_full_data(stock_id)

if df_raw.empty:
    st.error("❌ 無法取得數據，請確認代號是否正確。")
else:
    df = df_raw.copy()
    # 指標計算
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['13MA'] = df['Close'].rolling(window=13).mean()
    df['37MA'] = df['Close'].rolling(window=37).mean()
    
    curr_p = round(df['Close'].iloc[-1], 2)
    m5 = round(df['5MA'].iloc[-1], 2)
    m13 = round(df['13MA'].iloc[-1], 2)
    m37 = round(df['37MA'].iloc[-1], 2)
    
    prev_p = df['Close'].iloc[-2]
    change_pct = (curr_p - prev_p) / prev_p * 100

    # --- 2. 數據看板 ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("當前股價", f"{curr_p}", f"{change_pct:.2f}%")
    col2.metric("預估總損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")
    col3.metric("5MA", f"{m5}")
    col4.metric("13MA", f"{m13}")
    col5.metric("37MA", f"{m37}")

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

    # --- 4. 決策分析 ---
    st.subheader("🤖 綜合趨勢建議")
    with st.expander("📌 均線策略詳解", expanded=True):
        if curr_p > m5 > m13 > m37:
            st.success("🟢 【多頭排列】股價與所有均線呈正向排列，建議續抱並可考慮分批加碼。")
        elif curr_p < m37:
            st.error("🔴 【趨勢破線】股價已跌破 37MA 中期關鍵位，風險增加，建議減碼保護利潤。")
        elif m5 < m13:
            st.warning("🟡 【短期走弱】5MA 跌破 13MA 形成交叉，不建議此時追高。")
        else:
            st.info("⚪ 【震盪區間】均線目前無明確趨勢，建議耐心持有觀望。")

    # --- 5. 歷史關鍵數據 (最後 5 日) ---
    st.divider()
    st.subheader("📅 歷史量價數據 (最後 5 日)")
    
    # 建立表格數據，成交量維持原始股數 (Volume)
    recent_df = df[['Close', 'Volume', '5MA', '13MA', '37MA']].tail(5).copy()
    recent_df.columns = ['收盤價', '成交量(股)', '5MA', '13MA', '37MA']
    
    # 格式化輸出：所有欄位皆顯示小數點後兩位
    st.table(recent_df.style.format("{:.2f}"))

    st.caption("註：成交量為市場實際交易總股數。")
