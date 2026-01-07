import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- 1. フォント設定 (日本語化の徹底) ---
def set_japanese_font():
    # packages.txtでインストールしたフォントを直接指定
    font_path = '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = prop.get_name()
    else:
        # 代替案: 標準的な日本語フォントを指定
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'IPAexGothic', 'DejaVu Sans']

set_japanese_font()

# --- 2. 解析ロジック (要素数を11に統一) ---
def run_full_analysis(savings, car_val, premium, deductible, prob, y_rate, inf_rate):
    years = 10
    # time は 0年〜10年の計11個
    time = np.arange(0, years + 1)
    
    # 【解析A】決定論的推移
    # 1. 累積保険料 (11個)
    cost_ins_nominal = premium * time
    
    # 2. 累積期待損失 (11個)
    avg_damage_rate = 2 / 7 # Beta(2,5)の期待値
    expected_loss_series = [0.0]
    cumulative_loss = 0.0
    temp_val = car_val
    for t in range(1, years + 1):
        temp_val *= 0.95 
        yearly_expected_loss = temp_val * prob * avg_damage_rate
        cumulative_loss += yearly_expected_loss
        expected_loss_series.append(cumulative_loss)
    
    # 3. 運用資産の実質価値 (11個)
    savings_real = [0.0]
    curr_nominal_sav = 0.0
    for t in range(1, years + 1):
        curr_nominal_sav = (curr_nominal_sav + premium) * (1 + y_rate)
        real_value = curr_nominal_sav / ((1 + inf_rate)**t)
        savings_real.append(real_value)
        
    # 【解析B】モンテカルロ法
    trials = 1000
    m_results = []
    for _ in range(trials):
        c_sav_ins, c_sav_no, c_val = savings, savings, car_val
        for t in range(1, years + 1):
            c_val *= 0.95
            n_acc = np.random.poisson(prob)
            dmg = sum([c_val * np.random.beta(2, 5) for _ in range(n_acc)])
            # 保険あり (平均的な割引を適用)
            c_sav_ins -= (premium * 0.6) 
            if dmg > deductible: c_sav_ins += (dmg - deductible)
            c_sav_ins *= (1 + y_rate)
            # 保険なし
            c_sav_no -= dmg
            c_sav_no *= (1 + y_rate)
        m_results.append(c_sav_no - c_sav_ins)
        
    return time, cost_ins_nominal, np.array(expected_loss_series), np.array(savings_real), np.array(m_results)

# --- 3. UI・表示部分 ---
st.set_page_config(page_title="車両保険・精密分析エンジン", layout="wide")
st.title("🛡️ 車両保険・多角的意思決定エンジン")
st.markdown("### 決定論的コスト分析 × 確率論的リスクシミュレーション")

# サイドバー
st.sidebar.header("📝 条件設定")
s_sav = st.sidebar.number_input("現在の貯蓄 (円)", 0, 10000000, 1500000, 100000)
s_c_val = st.sidebar.slider("車両価格 (円)", 500000, 10000000, 3350000, 100000)
s_prem = st.sidebar.slider("年間車両保険料 (円)", 10000, 300000, 72000, 1000)
s_ded = st.sidebar.slider("免責額 (円)", 0, 200000, 50000, 10000)
s_prob = st.sidebar.slider("年間の事故遭遇率 (%)", 0.0, 20.0, 5.0, 0.5) / 100
s_yr = st.sidebar.slider("運用利回り (%)", 0.0, 10.0, 3.0, 0.5) / 100
s_inf = st.sidebar.slider("インフレ率 (%)", 0.0, 10.0, 2.0, 0.5) / 100

if st.sidebar.button("シミュレーションを実行"):
    # 5つの戻り値を展開
    time, cost_ins, exp_loss, sav_real, m_results = run_full_analysis(s_sav, s_c_val, s_prem, s_ded, s_prob, s_yr, s_inf)
    
    # 指標
    win_rate = np.sum(m_results > 0) / len(m_results) * 100
    expected_gain = np.mean(m_results)
    
    st.divider()
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("貯蓄シフトの勝率", f"{win_rate:.1f}%")
    col_b.metric("10年後の平均収支差", f"{int(expected_gain):+,}円")
    col_c.metric("判定", "貯蓄推奨" if win_rate > 70 else "保険維持推奨")

    # グラフ
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 長期推移レポート（決定論）")
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        ax1.plot(time, cost_ins, label="累積保険料 (赤)", color="red", linestyle="--")
        ax1.plot(time, exp_loss, label="累積期待損失 (青)", color="blue", linestyle=":")
        ax1.plot(time, sav_real, label="貯蓄＋運用資産 (緑)", color="green", linewidth=2)
        ax1.set_xlabel("年数")
        ax1.set_ylabel("金額 (円)")
        ax1.legend()
        ax1.grid(alpha=0.3)
        st.pyplot(fig1)
        st.caption("赤(払う額)と青(事故る額)の差が保険会社の手数料。緑が自前で運用した場合の資産。")

    with col2:
        st.subheader("📊 資産差額の分布（確率論）")
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        n, bins, patches = ax2.hist(m_results, bins=50, edgecolor='black', alpha=0.7)
        for i in range(len(patches)):
            if bins[i] > 0: patches[i].set_facecolor('green')
            else: patches[i].set_facecolor('red')
        ax2.axvline(0, color='black', linewidth=2)
        ax2.set_xlabel("保険なしが有利な金額（右に行くほど貯蓄の勝ち）")
        ax2.set_ylabel("頻度")
        st.pyplot(fig2)
        st.caption("1,000回のシミュレーション結果。右側の緑が多いほど貯蓄の方が経済的です。")

else:
    st.info("←左のサイドバーで条件を設定し、『シミュレーションを実行』を押してください。")
