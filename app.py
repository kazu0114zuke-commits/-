import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# --- 徹底的な日本語フォント対策 ---
def set_japanese_font():
    # packages.txtでインストールされるIPAフォントのパスを直接指定
    font_path = '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = prop.get_name()
    else:
        # 代替案: システムの標準フォントから日本語を探す
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'IPAexGothic', 'DejaVu Sans']

set_japanese_font()


# --- 計算ロジック ---
def simulate_advanced_model(savings, car_val, base_premium, deductible, prob, y_rate, inf_rate, trials=1000, years=10):
    diff_results = []
    # 等級割増引率（簡易版）
    ncd_rates = {1:1.64, 2:1.28, 3:1.15, 4:1.08, 5:0.87, 6:0.81, 7:0.7, 8:0.63, 9:0.6, 10:0.58, 
                 11:0.56, 12:0.54, 13:0.52, 14:0.5, 15:0.49, 16:0.48, 17:0.44, 18:0.4, 19:0.39, 20:0.37}
    
    for _ in range(trials):
        c_sav_ins = savings
        c_sav_no = savings
        c_ncd = 15
        c_val = car_val
        for t in range(1, years + 1):
            c_val *= 0.95
            n_acc = np.random.poisson(prob)
            dmg = 0
            if n_acc > 0:
                for _ in range(n_acc):
                    dmg += c_val * np.random.beta(2, 5)
            
            # 保険あり
            curr_prem = base_premium * ncd_rates.get(c_ncd, 1.0)
            c_sav_ins -= curr_prem
            if dmg > deductible:
                c_sav_ins += (dmg - deductible)
                c_ncd = max(1, c_ncd - (3 * n_acc))
            else:
                c_sav_ins -= dmg
                c_ncd = min(20, c_ncd + 1)
            c_sav_ins *= (1 + y_rate)
            
            # 保険なし
            c_sav_no -= dmg
            c_sav_no *= (1 + y_rate)
        diff_results.append(c_sav_no - c_sav_ins)
    return np.array(diff_results)

# --- UI部分 ---
st.set_page_config(page_title="車両保険・定量判断エンジン", layout="wide")
st.title("🛡️ 車両保険・多角的意思決定エンジン")
st.caption("確率論的動的リスク分析モデル")

# サイドバーにスライダーを配置
st.sidebar.header("📋 シミュレーション設定")
s_sav = st.sidebar.number_input("現在の貯蓄 (円)", value=1500000, step=100000)
s_c_val = st.sidebar.slider("車両価格 (円)", 500000, 10000000, 3000000, 100000)
s_prem = st.sidebar.slider("年間基準保険料 (円)", 10000, 300000, 100000, 5000)
s_ded = st.sidebar.slider("免責金額 (円)", 0, 200000, 50000, 10000)
s_prob = st.sidebar.slider("年間事故率 (%)", 0.0, 20.0, 5.0, 0.5) / 100
s_yr = st.sidebar.slider("資産運用利回り (%)", 0.0, 10.0, 3.0, 0.5) / 100
s_inf = st.sidebar.slider("想定インフレ率 (%)", 0.0, 10.0, 2.0, 0.5) / 100

# メイン画面
if st.sidebar.button("解析を実行"):
    with st.spinner('1,000回の人生をシミュレーション中...'):
        results = simulate_advanced_model(s_sav, s_c_val, s_prem, s_ded, s_prob, s_yr, s_inf)
        
        # 指標計算
        win_rate = np.sum(results > 0) / len(results) * 100
        expected_gain = np.mean(results)
        var_95 = np.percentile(results, 5)

        # 指示書表示
        st.subheader("█ 最終意思決定指示書")
        c1, c2, c3 = st.columns(3)
        c1.metric("貯蓄シフトの勝率", f"{win_rate:.1f}%")
        c2.metric("期待収支改善額", f"{int(expected_gain):+,}円")
        c3.metric("最大損失リスク(5%)", f"{int(abs(var_95)):,}円")

        if win_rate > 70:
            st.success("【判定】貯蓄シフト推奨。統計的に高い確率で自腹の方が得をします。")
        else:
            st.warning("【判定】保険維持推奨。万が一の損失が大きく、保険によるリスク移転に価値があります。")

        # グラフ
        st.divider()
        st.subheader("📊 資産差額の確率分布（保険なし vs 加入）")
        fig, ax = plt.subplots(figsize=(10, 4))
        n, bins, patches = ax.hist(results, bins=50, edgecolor='black', alpha=0.7)
        for i in range(len(patches)):
            if bins[i] > 0: patches[i].set_facecolor('green')
            else: patches[i].set_facecolor('red')
        ax.axvline(0, color='black', linewidth=2)
        ax.set_xlabel("「保険なし」が有利な金額（プラスなら貯蓄の勝ち）")
        ax.set_ylabel("頻度")
        st.pyplot(fig)
else:
    st.info("サイドバーの「解析を実行」ボタンを押すと、1,000回のモンテカルロ・シミュレーションが始まります。")
