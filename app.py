import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="台股分析器", layout="wide")
st.title("📈 台股 5MA/13MA 決策系統")

# --- 側邊欄 ---
st.sidebar.header("📌 個人持倉設定")
# 提醒使用者台股代號格式
stock_id = st.sidebar.text_input("股票代號 (如: 2330)", value="2330")
my_cost = st.sidebar.number_input("持有平均價格", value=600.0, step=0.1)
my_shares = st.sidebar.number_input("持有股數", value=1000, step=1)

# --- 1. 抓取數據 (加入除錯模式) ---
def get_all_data(sid):
    dl = DataLoader()
    # 抓取過去一整年的資料確保均線計算正確
    start_d = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    try:
        # 明確指定抓取台灣市場日線資料
        df = dl.taiwan_stock_daily(stock_id=sid, start_date=start_d)
        
        # 如果回傳的是 None 或空的，嘗試在代號後加上市場後綴 (有時 API 需處理)
        if df is None or df.empty:
            return pd.DataFrame()
            
        return df
    except Exception as e:
        st.sidebar.error(f"API 抓取異常: {e}")
        return pd.DataFrame()

# 執行抓取 (暫時移除 cache 以確保抓到最新狀態)
df_raw = get_all_data(stock_id)

# --- 2. 判斷與顯示 ---
if df_raw is None or df_raw.empty:
    st.error(f"❌ 找不到股票代號 '{stock_id}' 的資料。")
    st.info("💡 提示：請確認代號是否正確（例如台積電請輸入 2330）。若持續失敗，可能是 FinMind 伺服器暫時限制存取，請稍後再試。")
    
    # 增加一個測試按鈕，點擊後會顯示目前抓取到的原始格式，幫助 debug
    if st.button("查看系統偵錯資訊"):
        st.write("目前輸入代號:", stock_id)
        st.write("原始回傳結果類型:", type(df_raw))
else:
    # 數據整理
    df = df_raw.copy()
    # 確保欄位名稱正確 (FinMind 有時會是大寫或小寫)
    df.columns = [c.lower() for c in df.columns]
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date') # 確保日期排序正確
    
    # 計算均線
    df['5ma'] = df['close'].rolling(window=5).mean()
    df['13ma'] = df['close'].rolling(window=13).mean()
    
    curr_p = float(df.iloc[-1]['close'])
    m5 = float(df.iloc[-1]['5ma'])
    m13 = float(df.iloc[-1]['13ma'])

    # --- 3. 數據看板 ---
    profit_total = (curr_p - my_cost) * my_shares
    profit_pct = (curr_p - my_cost) / my_cost * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("當前股價", f"{curr_p}")
    c2.metric("預估損益", f"${profit_total:,.0f}", f"{profit_pct:.2f}%")
    c3.metric("5MA / 13MA", f"{m5:.1f} / {m13:.1f}")

    # --- 4. 圖表 ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], 
                                 low=df['low'], close=df['close'], name='K線'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['5ma'], line=dict(color='#00F', width=2), name='5MA'))
    fig.add_trace(go.Scatter(x=df['date'], y=df['13ma'], line=dict(color='#F90', width=2), name='13MA'))
    fig.add_hline(y=my_cost, line_dash="dash", line_color="red", annotation_text="成本線")
    
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. 決策建議 ---
    st.subheader("🤖 交易建議")
    if curr_p > m5 and m5 > m13:
        st.success(f"🌟 強勢多頭：股價在均線之上。支撐點 5MA ({m5:.1f})。")
    elif curr_p < m5 and curr_p > m13:
        st.warning(f"⚠️ 短期轉弱：跌破 5MA。請觀察 13MA ({m13:.1f}) 是否支撐。")
    elif curr_p < m13:
        st.error(f"🚨 趨勢轉空：已破 13MA，建議保護利潤或停損。")
    else:
        st.write("🔄 盤整中。")
