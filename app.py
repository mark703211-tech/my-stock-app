import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 進階分析", layout="wide")

# --- 1. 抓取數據 (極速防封版) ---
@st.cache_data(ttl=3600)
def get_stock_data_optimized(sid):
    # 先過濾掉空格
    sid = sid.strip().upper()
    for suffix in [".TW", ".TWO"]:
        target_id = f"{sid}{suffix}"
        try:
            ticker = yf.Ticker(target_id)
            # 只抓取歷史價格，這是最穩定的部分
            df = ticker.history(period="2y")
            if not df.empty:
                # 這裡用最安全的方式拿名稱，不抓 info 避免 RateLimit
                # 若 Yahoo 沒給名稱，就直接用代號
                return df, ticker.actions, target_id, sid
        except:
            continue
    return pd.DataFrame(), pd.DataFrame(), None, None

# --- 側邊欄 ---
st.sidebar.header("📌 個人持倉設定")
stock_input = st.sidebar.text_input("股票代號 (如: 2330 或 6182)", value="6182").strip()
my_cost = st.sidebar.number_input("您的買入平均價格", value=40.0, step=0.1)
my_shares = st.sidebar.number_input("持有總股數", value=1000, step=1)

df_raw, actions, final_id, stock_name = get_stock_data_optimized(stock_input)

# --- 2. 判斷與顯示 ---
if df_raw.empty:
    st.title("📈 台股 5 / 13 / 37 MA 專業決策系統")
    st.error(f"❌ 暫時無法讀取 '{stock_input}' 的數據。")
    st.info("💡 建議：點擊右上方『...』選擇『Reboot App』，或等待 5 分鐘後再試。這通常是數據源暫時忙碌。")
else:
    # 標題 (如果抓不到中文名，這裡會顯示 6182)
    st.title(f"📈 {stock_name} ({final_id}) 5/13/37 MA 專業決策系統")
    
    df = df_raw.copy()
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['13MA'] = df['Close'].rolling(window=13).mean()
    df['37MA'] = df['Close'].rolling(window=37).mean()
    
    curr_p = round(df['Close'].iloc[-1], 2)
    m5 = round(df['5MA'].iloc[-1], 2)
    m13 = round(df['13MA'].iloc[-1], 2)
    m37 = round(df['37MA'].iloc[-1], 2)
    change_pct = (curr_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100

    # 數據看板
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("當前股價", f"{curr_p}", f"{change_pct:.2f}%")
    c2.metric("預估總損益", f"${(curr_p - my_cost) * my_shares:,.0f}", f"{((curr_p - my_cost) / my_cost * 100):.2f}%")
    c3.metric("5MA", f"{m5}")
    c4.metric("13MA", f"{m13}")
    c5.metric("37MA", f"{m37}")

    # 圖表
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#00BFFF', width=1.5), name='5MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['13MA'], line=dict(color='#FF8C00', width=1.5), name='13MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['37MA'], line=dict(color='#BA55D3', width=2), name='37MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="#FF4B4B", annotation_text="成本")
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 強化版 AI 實戰策略詳解 ---
    st.subheader("🤖 AI 實戰深度解析")
    with st.expander("🔍 當前籌碼結構與明日操作策略", expanded=True):
        if curr_p > m5 > m13 > m37:
            st.success("🟢 **狀態：多頭排列（強勢）**")
            st.write(f"目前股價站穩於所有均線之上。只要收盤不破 5MA ({m5})，建議抱緊處理。")
        elif curr_p < m37:
            st.error("🔴 **狀態：空頭結構（轉弱）**")
            st.write(f"股價跌破中期線 ({m37})，過去兩個月買入的人多數套牢。建議執行風險管理。")
        elif m5 < m13:
            st.warning("🟡 **狀態：短期修正**")
            st.write(f"5MA 已穿過 13MA，短期買盤衰竭。關注 37MA ({m37}) 是否有支撐。")
        else:
            st.info("⚪ **狀態：均線糾結**")
            st.write("目前長短均線交疊，市場無共識，建議靜待放量突破。")

    # 歷史數據
    st.divider()
    st.subheader("📅 歷史量價數據 (最後 5 日)")
    recent_df = df[['Close', 'Volume', '5MA', '13MA', '37MA']].tail(5).copy()
    recent_df.columns = ['收盤價', '成交量(股)', '5MA', '13MA', '37MA']
    st.table(recent_df.style.format("{:.2f}"))
