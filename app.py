import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- 1. フォント・環境設定 ---
def set_japanese_font():
    # packages.txtで導入したフォントを強制指定
    font_path = '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = prop.get_name()
    else:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'DejaVu Sans']

set_japanese_font()

# --- 解析ロジック (累積期待損失の計算を追加) ---
def run_full_analysis(savings, car_val, premium, deductible, prob, y_rate, inf_rate):
    years = 10
    time = np.arange(0, years + 1)
    
    # 【解析A】決定論的推移
    cost_ins_nominal = premium * time
    
    # 累積期待損失の計算 (期待値 = 車両価値 * 事故率 * 平均損害率)
    # 損害率は Beta(2,5) の平均 = 2/(2+5) ≒ 28.5% を使用
    avg_damage_rate = 2 / 7 
    expected_loss_series = [0]
    current_val = car_val
    cumulative_loss = 0
    for t in range(1, years + 1):
        current_val *= 0.95 # 減価償却
        # その年の期待損失 = 時価 * 事故率 * 平均損害率
        yearly_expected_loss = current_val * prob * avg_damage_rate
        cumulative_loss += yearly_expected_loss
        expected_loss_series.append(cumulative_loss)
    
    # 運用資産（保険料を運用した場合の実質価値）
    savings_real = []
    curr_nominal_sav = 0
    for t in range(years + 1):
        real_value = curr_nominal_sav / ((1 + inf_rate)**t)
        savings_real.append(real_value)
        curr_nominal_sav = (curr_nominal_sav + premium) * (1 + y_rate)
        
    # 【解析B】確率論的分析 (モンテカルロ法)
    trials = 1000
    ncd_rates = {1:1.64, 6:0.81, 15:0.49, 20:0.37} # 等級による割引目安
    m_results = []
    for _ in range(trials):
        c_sav_ins = savings
        c_sav_no = savings
        c_ncd = 15
        c_val = car_val
        for t in range(1, years + 1):
            c_val *= 0.95 # 減価償却
            n_acc = np.random.poisson(prob)
            dmg = 0
            if n_acc > 0:
                # 損害額は時価の20%〜100%の間で分布
                for _ in range(n_acc): dmg += c_val * np.random.beta(2, 5)
            
            # 保険ありケース（等級ダウンによる将来コスト増も考慮）
            curr_prem = premium * (0.5 if c_ncd >= 15 else 0.8) 
            c_sav_ins -= curr_prem
            if dmg > deductible:
                c_sav_ins += (dmg - deductible)
                c_ncd = max(1, c_ncd - 3)
            else:
                c_sav_ins -= dmg
                c_ncd = min(20, c_ncd + 1)
            c_sav_ins *= (1 + y_rate)
            
            # 保険なしケース（全額自腹）
            c_sav_no -= dmg
            c_sav_no *= (1 + y_rate)
        m_results.append(c_sav_no - c_sav_ins)
        
    return time, cost_ins_nominal, np.array(savings_real), np.array(m_results),np.array(m_results)

# --- 3. UI構築 ---
st.set_page_config(page_title="車両保険・精密分析アプリ", layout="wide")
st.title("🛡️ 車両保険・多角的意思決定エンジン")
st.markdown("### 決定論的コスト分析 × 確率論的リスクシミュレーション")

# サイドバー設定
st.sidebar.header("📝 条件設定")
s_sav = st.sidebar.number_input("現在の貯蓄 (円)", 0, 10000000, 1500000, 100000)
s_c_val = st.sidebar.slider("車両価格 (円)", 500000, 10000000, 3000000, 100000)
s_prem = st.sidebar.slider("年間基準保険料 (円)", 10000, 300000, 100000, 5000)
s_ded = st.sidebar.slider("免責額 (円)", 0, 200000, 50000, 10000)
s_prob = st.sidebar.slider("事故率 (%)", 0.0, 20.0, 5.0, 0.5) / 100
s_yr = st.sidebar.slider("運用利回り (%)", 0.0, 10.0, 3.0, 0.5) / 100
s_inf = st.sidebar.slider("インフレ率 (%)", 0.0, 10.0, 2.0, 0.5) / 100

if st.sidebar.button("シミュレーションを実行"):
    time, cost_ins, exp_loss, sav_real, m_results = run_full_analysis(s_sav, s_c_val, s_prem, s_ded, s_prob, s_yr, s_inf)
    
    # 指標表示
    win_rate = np.sum(m_results > 0) / len(m_results) * 100
    expected_gain = np.mean(m_results)
    
    st.divider()
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("貯蓄シフトの勝率", f"{win_rate:.1f}%")
    col_b.metric("10年後の平均収支差", f"{int(expected_gain):+,}円")
    col_c.metric("リスク判定", "貯蓄推奨" if win_rate > 70 else "保険維持推奨")

    # グラフ表示
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 長期推移レポート（決定論）")
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        ax1.plot(time, cost_ins, label="累積保険料支出 (確定コスト)", color="red", linestyle="--")
        ax1.plot(time, exp_loss, label="累積期待損失 (事故コスト期待値)", color="blue", linestyle=":")
        ax1.plot(time, sav_real, label="貯蓄＋運用資産 (実質価値)", color="green", linewidth=2)
        ax1.set_xlabel("年数")
        ax1.set_ylabel("金額 (円)")
        ax1.legend()
        ax1.grid(alpha=0.3)
        st.pyplot(fig1)
        st.caption("赤線(保険料)が青線(期待損失)を上回っている期間は、統計的に『払いすぎ』の状態です。")

    with col2:
        st.subheader("📊 資産差額の分布（確率論）")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        n, bins, patches = ax2.hist(m_results, bins=50, edgecolor='black', alpha=0.7)
        for i in range(len(patches)):
            if bins[i] > 0: patches[i].set_facecolor('green')
            else: patches[i].set_facecolor('red')
        ax2.axvline(0, color='black', linewidth=2)
        ax2.set_title("1,000回の人生試行結果")
        ax2.set_xlabel("保険なしが有利な金額（右に行くほど貯蓄の勝ち）")
        ax2.set_ylabel("頻度")
        st.pyplot(fig2)
        st.caption("事故の発生タイミングや損害額のバラツキを考慮した10年後の結果分布です。")

else:
    st.info("←左のサイドバーで条件を設定し、『シミュレーションを実行』を押してください。")
