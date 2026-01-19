import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os, math

# --- 1. 环境与字体配置 ---
font_path = 'SourceHanSansSC-Regular.otf'
prop = fm.FontProperties(fname=font_path) if os.path.exists(font_path) else None
if prop:
    plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 严谨的代码格式化与市场识别 (保留你的原稿) ---
def format_ticker(s):
    if not s: return "AAPL"
    s = s.strip().upper()
    if s.endswith(".HK"):
        parts = s.split(".")
        return f"{code.zfill(5)}.HK"
    if "." in s and not s.endswith((".SS", ".SZ")):
        return s.replace(".", "-")
    if s.isdigit() and len(s) == 6:
        return f"{s}.SS" if s.startswith(('6', '9')) else f"{s}.SZ"
    return s

def get_market_config(ticker):
    t = ticker.upper()
    if t.endswith(".HK"): return "HKD $", "港股"
    if t.endswith((".SS", ".SZ")): return "CNY ¥", "A股"
    return "USD $", "美股"

# --- 3. 核心算法逻辑 (保留你的原稿) ---
def rsi_wilder(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calculate_logic(df, info):
    # 增加一层防御，防止数据量不足
    if len(df) < 20: return None 
    close = df['Close'].dropna().astype(float)
    last = float(close.iloc[-1])
    rsi = rsi_wilder(close)
    rsi_last = float(rsi.iloc[-1])
    rsi_prev = float(rsi.iloc[-2]) if len(rsi) > 2 else rsi_last
    pr_3y = close.tail(756).rank(pct=True).iloc[-1]

    cond_A = pr_3y < 0.30
    cond_B = rsi_last < 35
    cond_C = rsi_last > rsi_prev

    if cond_A and cond_B and cond_C: sig = "加仓", "🔵", "确认反转，极高性价比"
    elif cond_A and cond_B: sig = "建仓", "🟢", "进入价值区，等待拐头"
    elif cond_A or cond_B: sig = "试探", "🟡", "满足单一底部特征"
    else: sig = "观察", "⚪", "暂无明显底部信号"

    tr = pd.concat([(df['High']-df['Low']), (df['High']-close.shift(1)).abs(), (df['Low']-close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    width = max(1.8 * atr, last * 0.08)
    center = last * 0.92

    zones = {
        "conservative": (center + 0.3*width, center + 0.8*width),
        "neutral": (center - 0.2*width, center + 0.2*width),
        "aggressive": (center - 0.8*width, center - 0.3*width)
    }

    adds = {
        "first": zones["neutral"][0],
        "pullback": (zones["aggressive"][0] + zones["aggressive"][1])/2,
    }

    return {
        "last": last, "sig": sig, "zones": zones, "adds": adds,
        "metrics": {"rsi": rsi_last, "pr_3y": pr_3y, "atr": atr},
        "cond": (cond_A, cond_B, cond_C)
    }

# --- 4. UI 界面 ---
st.set_page_config(page_title="10 dollars Seeking Alpha", layout="wide")

with st.sidebar:
    st.header("🔍 代码搜索")
    raw_input = st.text_input("代码 (AAPL, 600519)", value="AAPL", key="main_ticker_input")
    ticker = format_ticker(raw_input)
    currency_symbol, mkt_name = get_market_config(ticker)
    st.divider()
    st.markdown(f"**识别结果**")
    st.code(ticker)
    st.markdown(f"市场: `{mkt_name}` | 货币: `{currency_symbol}`")
    st.divider()  # 添加一条分割线
    st.caption("⚠️ **免责声明**")
    st.caption("本工具仅作学习与研究之用，不对任何人的任何投资结果负责。")

st.title("10 Dollars 带你 Seeking Alpha V0.9")

if st.button("🚀 生成全维度分析报告", use_container_width=True, type="primary"):
    with st.spinner(f"正在尝试连接 Yahoo 数据库解析 {ticker}..."):
        
        # 核心加固点 1: 初始化
        df = pd.DataFrame()
        info_data = {}
        
        try:
            tk = yf.Ticker(ticker)
            # 核心加固点 2: 抓取 history
            df = tk.history(period="3y")
            
            # 核心加固点 3: 安全获取 info
            try:
                raw_info = tk.info
                info_data = raw_info if raw_info is not None else {}
            except:
                info_data = {}

            if not df.empty:
                # 处理多级索引
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 1. 计算核心指标
                res = calculate_logic(df, info_data)
                
                if res:
                    # 2. 获取股票名字 (注意这里的缩进，必须和上一行 res 对齐)
                    stock_name = info_data.get('shortName') or info_data.get('longName') or ticker
                    
                    # 3. 显示大标题
                    st.header(f"📈 {stock_name} ({ticker}) 分析报告")

                    # 4. 指标行
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("当前价格", f"{currency_symbol} {res['last']:.2f}")
                    c2.metric("建议动作", f"{res['sig'][1]} {res['sig'][0]}")
                    
                    pe_val = info_data.get('trailingPE')
                    ps_val = info_data.get('priceToSalesTrailing12Months')
                    c3.metric("市盈率 PE", f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "—")
                    c4.metric("市销率 PS", f"{ps_val:.2f}" if isinstance(ps_val, (int, float)) else "—")
                    
                    st.divider()

                    # 5. 报告详情 (左雷达图，右区间)
                    col_left, col_right = st.columns([1, 1.2])
                    with col_left:
                        st.subheader("🎯 维度诊断雷达")
                        labels = ['位置(A)', '情绪(B)', '动能(C)', '波动率']
                        scores = [25 if res['cond'][0] else 8, 25 if res['cond'][1] else 10,
                                  25 if res['cond'][2] else 12, min(25, (res['metrics']['atr']/res['last'])*150)]
                        
                        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
                        angles = [n/4 * 2*math.pi for n in range(4)]; angles += angles[:1]
                        values = scores + scores[:1]
                        ax.fill(angles, values, color='#1E88E5', alpha=0.3)
                        ax.plot(angles, values, color='#1E88E5', linewidth=2, marker='o')
                        ax.set_xticks(angles[:-1])
                        ax.set_xticklabels(labels, fontproperties=prop)
                        ax.set_ylim(0, 25)
                        st.pyplot(fig)

                    with col_right:
                        st.subheader("📥 分批买入建议区间")
                        st.info(f"**诊断依据**：{res['sig'][2]}")
                        z_cons, z_neut, z_aggr = res['zones']['conservative'], res['zones']['neutral'], res['zones']['aggressive']
                        st.write(f"🔵 **保守区**: `{currency_symbol} {z_cons[0]:.2f} - {z_cons[1]:.2f}`")
                        st.write(f"🟢 **标准区**: `{currency_symbol} {z_neut[0]:.2f} - {z_neut[1]:.2f}`")
                        st.write(f"🔴 **激进区**: `{currency_symbol} {z_aggr[0]:.2f} - {z_aggr[1]:.2f}`")
                        st.divider()
                        st.subheader("🧱 操作手册 (加仓位)")
                        a1, a2 = st.columns(2)
                        a1.metric("第一加仓位", f"{currency_symbol} {res['adds']['first']:.2f}")
                        a2.metric("深度加仓位", f"{currency_symbol} {res['adds']['pullback']:.2f}")
                        
                        with st.expander("查看底层信号数据"):
                            st.write(f"A. 3年分位: {res['metrics']['pr_3y']*100:.1f}%")
                            st.write(f"B. RSI: {res['metrics']['rsi']:.1f}")
                            st.write(f"C. 拐头: {'是' if res['cond'][2] else '否'}")
                else:
                    st.warning("数据长度不足以支持 3 年全维度分析。")
            else:
                st.error(f"无法获取 {ticker} 的历史价格数据，Yahoo 接口可能暂时受限。")

        except Exception as e:
            st.error(f"程序运行出错: {e}")
