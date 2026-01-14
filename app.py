import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股 AI 進階分析", layout="wide")

# --- 側邊欄：持倉設定 ---
st.sidebar.header("📌 個人持倉設定")
stock_input = st.sidebar.text_input("股票代號 (如: 2330 或 5498)", value="5498").strip()
my_cost = st.sidebar.number_input("您的買入平均價格", value=10.0) # 預設值可依需求調整
my_shares = st.sidebar.number_input("持有總股數", value=1000)

# --- 1. 抓取數據 (新增獲取股票名稱功能) ---
@st.cache_data(ttl=3600)
def get_stock_data_with_name(sid):
    for suffix in [".TW", ".TWO"]:
        target_id = f"{sid}{suffix}"
        ticker = yf.Ticker(target_id)
        df = ticker.history(period="2y")
        if not df.empty:
            # 嘗試抓取股票中文名稱，若無則顯示代號
            s_name = ticker.info.get('longName', sid)
            return df, ticker.actions, target_id, s_name
    return pd.DataFrame(), pd.DataFrame(), None, None

df_raw, actions, final_id, stock_name = get_stock_data_with_name(stock_input)

if df_raw.empty:
    st.title("📈 台股 5 / 13 / 37 MA 專業決策系統")
    st.error(f"❌ 找不到代號 '{stock_input}' 的資料。")
else:
    # 動態標題：顯示代號與名稱
    st.title(f"📈 {stock_name} ({stock_input}) 5/13/37 MA 專業決策系統")
    
    df = df_raw.copy()
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
    c3.metric("5MA (極短)", f"{m5}")
    c4.metric("13MA (短期)", f"{m13}")
    c5.metric("37MA (趨勢)", f"{m37}")

    # --- 3. 繪製圖表 ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#00BFFF', width=1.5), name='5MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['13MA'], line=dict(color='#FF8C00', width=1.5), name='13MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['37MA'], line=dict(color='#BA55D3', width=2), name='37MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="#FF4B4B", annotation_text="買入成本")
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 強化版 AI 實戰策略詳解 ---
    st.subheader("🤖 AI 實戰深度解析")
    
    # 計算乖離與斜率趨勢
    bias_37 = ((curr_p - m37) / m37) * 100
    m37_prev = df['37MA'].iloc[-2]
    is_m37_up = m37 > m37_prev

    with st.expander("🔍 點擊展開：當前籌碼結構與明日操作策略", expanded=True):
        # 狀況 A：多頭排列
        if curr_p > m5 > m13 > m37:
            st.success("🟢 **狀態：極強勢多頭排列**")
            st.write(f"""
            - **結構解析**：{stock_name} 目前所有均線皆呈上升斜率，且股價位於所有均線之上。這代表市場短期與中期籌碼達成高度共識，這是一檔典型的飆股結構。
            - **風險警示**：目前與 37MA 的中期乖離率為 **{bias_37:.2f}%**。若乖離過大（>20%），需慎防獲利回吐的急殺。
            - **明日策略**：不建議放空。若有持股者應「抱緊處理」，直到股價收盤有效跌破 5MA ({m5}) 再考慮分批獲利了結。
            """)
        
        # 狀況 B：短期修正
        elif m5 < m13 and curr_p > m37:
            st.warning("🟡 **狀態：上升趨勢中的短期整理**")
            st.write(f"""
            - **結構解析**：短期均線 5MA 已跌破 13MA，顯示短線投機買盤正在撤出。但因股價仍在 37MA ({m37}) 之上，中期大趨勢並未走壞。
            - **操作建議**：**暫停加碼**。如果您是短線投資者，這是一個「減碼訊號」；如果您是長線投資者，應關注 37MA 的支撐力道。
            - **關鍵價位**：明日需觀察 37MA ({m37})，只要此線不破，中期多頭結構就還在。
            """)

        # 狀況 C：跌破生命線
        elif curr_p < m37:
            st.error("🔴 **狀態：空頭轉弱結構**")
            st.write(f"""
            - **結構解析**：股價已跌破 37MA (中期生命線)，且 37MA 方向{'開始走平或下彎' if not is_m37_up else '尚未完全轉下'}。這代表過去兩個月買入的人多數處於套牢狀態。
            - **操作建議**：**嚴格執行風險管理**。建議考慮將部位縮減至最低，或設立停損。反彈至 13MA ({m13}) 若站不穩，皆應視為逃命波。
            """)
        
        # 狀況 D：均線糾結
        else:
            st.info("⚪ **狀態：均線糾結/箱型震盪**")
            st.write(f"""
            - **結構解析**：5、13、37MA 數值極為接近（均線糾結）。這代表股價正在選擇方向，即將出現大波動。
            - **操作建議**：**多看少動**。等待股價以帶量長紅棒站上 5MA，或長黑棒跌破 37MA 來確認最終方向。
            """)

    # --- 5. 歷史數據 ---
    st.divider()
    st.subheader(f"📅 {stock_name} 歷史量價數據 (最後 5 日)")
    recent_df = df[['Close', 'Volume', '5MA', '13MA', '37MA']].tail(5).copy()
    recent_df.columns = ['收盤價', '成交量(股)', '5MA', '13MA', '37MA']
    st.table(recent_df.style.format("{:.2f}"))
