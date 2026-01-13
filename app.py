import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 分析助手", layout="wide")
st.title("📈 台股 5MA/13MA 決策系統 (yfinance 版)")

# --- 側邊欄 ---
st.sidebar.header("📌 個人持倉設定")
# yfinance 台灣股票需加上 .TW (例如 2330.TW)
raw_id = st.sidebar.text_input("股票代號", value="2330")
stock_id = f"{raw_id}.TW" if ".TW" not in raw_id.upper() else raw_id

my_cost = st.sidebar.number_input("持有平均價格", value=600.0)
my_shares = st.sidebar.number_input("持有股數", value=1000)

# --- 1. 抓取數據 (使用 yfinance) ---
def get_data(sid):
    try:
        # 抓取最近一年的數據
        ticker = yf.Ticker(sid)
        df = ticker.history(period="1y")
        return df
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return pd.DataFrame()

df = get_data(stock_id)

# --- 2. 判斷數據並顯示 ---
if df is None or df.empty:
    st.error(f"❌ 無法取得 '{stock_id}' 的數據。")
    st.info("💡 請確認代號是否正確（例如台積電輸入 2330）。")
else:
    # 計算均線
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['13MA'] = df['Close'].rolling(window=13).mean()
    
    # 取得最新一筆數據
    curr_p = round(df['Close'].iloc[-1], 2)
    m5 = round(df['5MA'].iloc[-1], 2)
    m13 = round(df['13MA'].iloc[-1], 2)

    # --- 3. 數據看板 ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("當前股價", f"{curr_p}")
    c2.metric("預估損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")
    c3.metric("5MA / 13MA", f"{m5} / {m13}")

    # --- 4. 繪製互動圖表 ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='blue', width=2), name='5MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['13MA'], line=dict(color='orange', width=2), name='13MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="red", annotation_text="我的成本")
    
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. AI 決策建議 ---
    st.subheader("🤖 AI 盤後分析建議")
    if curr_p > m5 and m5 > m13:
        st.success(f"🌟 強勢多頭：股價站穩均線。支撐看 5MA ({m5})，建議續抱或分批加碼。")
    elif curr_p < m5 and curr_p > m13:
        st.warning(f"⚠️ 短期轉弱：股價跌破 5MA。建議觀察 13MA ({m13}) 支撐，暫緩加碼。")
    elif curr_p < m13:
        st.error(f"🚨 趨勢轉空：股價已破 13MA。建議執行停損或減碼，保護資金安全。")
    else:
        st.write("🔄 盤整階段：建議觀望，等待 5MA 重新翻揚。")
