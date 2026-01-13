import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 進階分析", layout="wide")
st.title("📈 台股 5MA/13MA 專業決策系統")

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
    # 抓取兩年數據以確保除權息與均線計算完整
    df = ticker.history(period="2y")
    # 取得除權息事件
    actions = ticker.actions
    return df, actions

df, actions = get_full_data(stock_id)

if df.empty:
    st.error("❌ 無法取得數據，請確認代號是否正確。")
else:
    # 指標計算
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['13MA'] = df['Close'].rolling(window=13).mean()
    
    curr_p = round(df['Close'].iloc[-1], 2)
    m5 = round(df['5MA'].iloc[-1], 2)
    m13 = round(df['13MA'].iloc[-1], 2)
    prev_p = df['Close'].iloc[-2]
    change_pct = (curr_p - prev_p) / prev_p * 100

    # --- 2. 數據看板 (視覺強化) ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("當前股價", f"{curr_p}", f"{change_pct:.2f}%")
    col2.metric("預估總損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")
    col3.metric("5MA 短期線", f"{m5}")
    col4.metric("13MA 趨勢線", f"{m13}")

    # --- 3. 繪製圖表 (含除權息與成本) ---
    fig = go.Figure()
    # K線
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name='K線'))
    # 均線
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#00BFFF', width=2), name='5MA (短)'))
    fig.add_trace(go.Scatter(x=df.index, y=df['13MA'], line=dict(color='#FF8C00', width=2), name='13MA (長)'))
    
    # 成本線
    fig.add_hline(y=my_cost, line_dash="dash", line_color="#FF4B4B", annotation_text="我的成本")

    # 標記除權息 (星星符號)
    divs = actions[actions['Dividends'] > 0]
    divs = divs[divs.index > df.index.min()]
    if not divs.empty:
        fig.add_trace(go.Scatter(x=divs.index, y=df.loc[df.index.isin(divs.index.date), 'High'],
                                 mode='markers', marker=dict(symbol='star', size=12, color='gold'),
                                 name='除權息日', hovertext="配息發放"))

    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 進階 AI 決策分析 (針對明日交易) ---
    st.subheader("🤖 明日交易策略分析")
    
    # 建立多重判斷邏輯
    is_golden_cross = m5 > m13
    is_above_m5 = curr_p > m5
    is_profitable = curr_p > my_cost
    
    # AI 建議與動作建議
    with st.expander("📌 點擊展開詳細策略建議", expanded=True):
        if is_golden_cross and is_above_m5:
            if is_profitable:
                st.success("🟢 【建議：分批加碼】目前處於強勢多頭，且您已獲利。若明日回測 5MA 不破，可追加 1/3 位階。")
            else:
                st.info("🔵 【建議：續抱觀察】雖然趨勢轉強，但尚未脫離成本區，建議等站穩後再加碼。")
        elif is_golden_cross and not is_above_m5:
            st.warning("🟡 【建議：減碼觀望】趨勢雖未破壞，但股價跌破 5MA。若明日未收復，建議先賣出近期加碼部分。")
        elif not is_golden_cross and curr_p < m13:
            st.error("🔴 【建議：全面撤出】5MA 下穿 13MA 形成死亡交叉，且破趨勢線。應果斷執行停損或停利。")
        else:
            st.write("⚪ 【建議：盤整期】目前方向不明，建議維持現有部位，不加碼也不隨意賣出。")

    # --- 5. 關心數據紀錄 ---
    st.divider()
    st.subheader("📅 歷史關鍵數據 (最後 5 日)")
    st.table(df[['Close', '5MA', '13MA']].tail(5).round(2))
