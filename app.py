# 1. 必要なライブラリを再インポート（このセルだけで完結させます）
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
# サーバー上の日本語フォントを自動で読み込む設定（後述のrequirementsと連動）
plt.rcParams['font.family'] = 'sans-serif'
import ipywidgets as widgets
from IPython.display import display, clear_output

# 等級遷移用
NCD_RATES = {i: 0.5 for i in range(1, 21)} # 簡易版

def run_integrated_analysis(savings, car_val, premium, deductible, prob, y_rate, inf_rate):
    years = 10
    time = np.arange(0, years + 1)
    
    # --- 解析1: 決定論的レポート (曲線モデル) ---
    cost_ins = premium * time
    savings_real = []
    curr_sav = 0
    for t in range(years + 1):
        # 購買力 = 名目資産 / (1 + インフレ率)^t
        real_p = curr_sav / ((1 + inf_rate)**t)
        savings_real.append(real_p)
        curr_sav = (curr_sav + premium) * (1 + y_rate)
    
    # --- 解析2: 確率論的分析 (モンテカルロ法) ---
    trials = 1000
    m_results = []
    for _ in range(trials):
        c_sav_ins = savings
        c_sav_no = savings
        c_val = car_val
        for t in range(1, years + 1):
            c_val *= 0.95 # 減価償却
            n_acc = np.random.poisson(prob)
            dmg = 0
            if n_acc > 0:
                for _ in range(n_acc):
                    dmg += c_val * np.random.beta(2, 5)
            
            # 保険あり：保険料（等級考慮せず一旦0.5倍固定）を払い、免責超えを補填
            c_sav_ins -= (premium * 0.5)
            if dmg > deductible: c_sav_ins += (dmg - deductible)
            c_sav_ins *= (1 + y_rate)
            
            # 保険なし：修理費すべて自腹
            c_sav_no -= dmg
            c_sav_no *= (1 + y_rate)
        m_results.append(c_sav_no - c_sav_ins)
    
    return time, cost_ins, np.array(savings_real), np.array(m_results)

# --- UI構築 ---
def update_app(savings, car_val, premium, deductible, prob, y_rate, inf_rate):
    time, cost_ins, sav_real, m_results = run_integrated_analysis(
        savings, car_val, premium, deductible, prob/100, y_rate/100, inf_rate/100
    )
    
    clear_output(wait=True)
    
    # 描画エリア
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 左：決定論レポート
    ax1.plot(time, cost_ins, label="累積保険料支出", color="red", linestyle="--")
    ax1.plot(time, sav_real, label="未加入時の実質資産価値", color="green", linewidth=2)
    ax1.set_title("10年間の実質収支推移", fontsize=14)
    ax1.set_xlabel("年数")
    ax1.set_ylabel("金額 (円)")
    ax1.legend()
    ax1.grid(True)
    
    # 右：確率分布
    n, bins, patches = ax2.hist(m_results, bins=50, edgecolor='black', alpha=0.7)
    for i in range(len(patches)):
        if bins[i] > 0: patches[i].set_facecolor('green')
        else: patches[i].set_facecolor('red')
    ax2.axvline(0, color='black', linewidth=2)
    ax2.set_title("1,000回の試行による『最終資産差』の分布", fontsize=14)
    ax2.set_xlabel("保険なしが有利な金額（プラスなら貯蓄の勝ち）")
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 意思決定指示書
    win_rate = np.sum(m_results > 0) / 10
    print("\n" + "█"*30 + " 最終意思決定指示書 " + "█"*30)
    print(f"【統計データ】 保険未加入（貯蓄）が有利になる確率: {win_rate}%")
    if win_rate > 70:
        print("🟢 判定：貯蓄シフト推奨。統計的に7割以上の確率で自腹の方が得をします。")
    else:
        print("🔴 判定：保険維持推奨。大損するリスクが無視できないレベルです。")
    print("█"*78)

# スライダー設定
s_sav = widgets.IntSlider(value=1500000, min=0, max=5000000, step=100000, description='貯蓄:')
s_c_val = widgets.IntSlider(value=3000000, min=500000, max=10000000, step=100000, description='車両価格:')
s_prem = widgets.IntSlider(value=100000, min=0, max=300000, step=5000, description='保険料:')
s_ded = widgets.IntSlider(value=50000, min=0, max=200000, step=10000, description='免責額:')
s_prob = widgets.FloatSlider(value=5.0, min=0, max=20.0, step=0.5, description='事故率(%):')
s_yr = widgets.FloatSlider(value=3.0, min=0, max=10.0, step=0.5, description='利回り(%):')
s_inf = widgets.FloatSlider(value=2.0, min=0, max=10.0, step=0.5, description='インフレ(%):')

ui = widgets.VBox([
    widgets.HBox([s_sav, s_c_val]),
    widgets.HBox([s_prem, s_ded]),
    widgets.HBox([s_prob, s_yr, s_inf])
])

out = widgets.interactive_output(update_app, {
    'savings': s_sav, 'car_val': s_c_val, 'premium': s_prem, 
    'deductible': s_ded, 'prob': s_prob, 'y_rate': s_yr, 'inf_rate': s_inf
})

display(ui, out)
