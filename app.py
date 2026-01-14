import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(
    page_title="我的持股診斷", # 桌面顯示名稱
    page_icon="💰",           # 使用金錢袋圖標
    layout="centered"         # 1.0 適合置中對齊，看起來比較精簡
)
# --- 1. 抓取數據 (兼顧穩定性與名稱抓取) ---
@st.cache_data(ttl=3600)
def get_stock_full_info(sid):
    sid = sid.strip().upper()
    for suffix in [".TW", ".TWO"]:
        target_id = f"{sid}{suffix}"
        try:
            ticker = yf.Ticker(target_id)
            df = ticker.history(period="2y")
            if not df.empty:
                # 嘗試拿名稱，如果被限流就抓不到，則回傳代號
                try:
                    s_name = ticker.info.get('longName') or ticker.info.get('shortName') or sid
                except:
                    s_name = sid
                return df, ticker.actions, target_id, s_name
        except:
            continue
    return pd.DataFrame(), pd.DataFrame(), None, None

# --- 側邊欄 ---
st.sidebar.header("📌 個人持倉設定")
stock_input = st.sidebar.text_input("股票代號 (如: 2330 或 6182)", value="6182").strip()
my_cost = st.sidebar.number_input("您的買入平均價格", value=40.0, step=0.1)
my_shares = st.sidebar.number_input("持有總股數", value=1000, step=1)

df_raw, actions, final_id, stock_name = get_stock_full_info(stock_input)

# --- 2. 判斷與顯示 ---
if df_raw.empty:
    st.title("📈 台股 5 / 13 / 37 MA 專業決策系統")
    st.error(f"❌ 暫時無法讀取 '{stock_input}' 的數據。")
    st.info("💡 可能是數據源暫時忙碌。請稍等 5 分鐘後點擊右下方 Manage App -> Reboot App。")
else:
    # 標題自動顯示名稱
    st.title(f"📈 {stock_name} ({stock_input}) 5/13/37 MA 專業決策系統")
    
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
    c3.metric("5MA (極短)", f"{m5}")
    c4.metric("13MA (短期)", f"{m13}")
    c5.metric("37MA (趨勢)", f"{m37}")

    # 圖表
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#00BFFF', width=1.5), name='5MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['13MA'], line=dict(color='#FF8C00', width=1.5), name='13MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['37MA'], line=dict(color='#BA55D3', width=2), name='37MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="#FF4B4B", annotation_text="買入成本")
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 恢復並強化：AI 實戰深度解析 ---
    st.subheader("🤖 AI 實戰深度解析")
    bias_37 = ((curr_p - m37) / m37) * 100

    with st.expander("🔍 點擊展開：當前籌碼結構與明日操作策略", expanded=True):
        # 狀況 A：多頭排列
        if curr_p > m5 > m13 > m37:
            st.success("🟢 **狀態：極強勢多頭排列（飆股模式）**")
            st.write(f"""
            - **結構解析**：{stock_name} 目前所有均線皆呈上升斜率。這代表市場短期與中期籌碼達成高度共識，上方無解套壓力。
            - **風險警示**：目前與 37MA 的中期乖離率為 **{bias_37:.2f}%**。若乖離超過 15-20%，需慎防獲利回吐。
            - **明日策略**：只要收盤不破 5MA ({m5}) 則抱緊處理。回測 13MA ({m13}) 若有撐可視為二次買點。
            """)
        
        # 狀況 B：短期修正
        elif m5 < m13 and curr_p > m37:
            st.warning("🟡 **狀態：上升趨勢中的短期整理**")
            st.write(f"""
            - **結構解析**：5MA 已下穿 13MA，顯示短線投機買盤正在撤出。但因股價仍在 37MA ({m37}) 之上，中期趨勢尚未崩盤。
            - **操作建議**：**「不追高、不加碼」**。若明日跌破今日低點，建議獲利了結部分部位。
            - **關鍵價位**：盯緊 37MA ({m37})，這是最後的防線。
            """)

        # 狀況 C：趨勢反轉
        elif curr_p < m37:
            st.error("🔴 **狀態：空頭轉弱結構**")
            st.write(f"""
            - **結構解析**：股價跌破中期生命線 ({m37})。代表過去兩個月買入的人多數處於套牢狀態。
            - **操作建議**：**執行停損**。不要在空頭趨勢中攤平。反彈至均線若站不穩，應視為逃命波。
            """)
        
        # 狀況 D：均線糾結
        else:
            st.info("⚪ **狀態：均線糾結 / 箱型震盪**")
            st.write(f"""
            - **結構解析**：長短均線交疊，市場目前沒有方向。
            - **操作建議**：觀望為主。等待股價以帶量紅棒站上 5MA，或長黑棒跌破 37MA 來確認最終動向。
            """)

    # --- 5. 歷史數據 ---
    st.divider()
    st.subheader(f"📅 {stock_name} 歷史數據 (最後 5 日)")
    recent_df = df[['Close', 'Volume', '5MA', '13MA', '37MA']].tail(5).copy()
    recent_df.columns = ['收盤價', '成交量(股)', '5MA', '13MA', '37MA']
    st.table(recent_df.style.format("{:.2f}"))


