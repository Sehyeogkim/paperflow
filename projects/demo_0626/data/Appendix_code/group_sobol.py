"""
Q3 Analysis: Group effect comparison — Morphology vs Material vs Hemodynamics.

ExperimentE2:
  - 11 inputs (6 Morph + 2 Mat + 3 Hemo) -> stress outputs (PSS, delta_PSS)
  - Subset GPR models: Morph only, Mat only, Hemo only, Full
  - True group Sobol indices (SALib 'groups' key) on the Full model
  - FFR is skipped (trivially morphology-driven, see Q1)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import matplotlib
matplotlib.use('Agg')

import numpy as np
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
from SALib.sample import saltelli
from SALib.analyze import sobol
import warnings
warnings.filterwarnings('ignore')

from shared import (load_data, INPUT_PARAMS, MORPH_PARAMS, MAT_PARAMS, HEMO_PARAMS,
                    OUTPUT_NAMES, SEED, TEST_SIZE)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

DISPLAY_NAME_OUTPUTS = {'FFR': 'FFR', 'PSS': 'PSS', 'delta_PSS': r'$\Delta$PSS'}

# ============================================================
# DATA LOADING
# ============================================================
df = load_data()

X_full = df[INPUT_PARAMS].values
STRESS_OUTPUTS = ['PSS', 'delta_PSS']

all_targets = {name: np.log(df[name].values) for name in STRESS_OUTPUTS}

# ============================================================
# Common train/test split
# ============================================================
X_train_raw, X_test_raw, idx_train, idx_test = train_test_split(
    X_full, np.arange(len(X_full)), test_size=TEST_SIZE, random_state=SEED)

scaler_full = StandardScaler()
X_train_full = scaler_full.fit_transform(X_train_raw)
X_test_full = scaler_full.transform(X_test_raw)
X_full_scaled = scaler_full.transform(X_full)

morph_cols = [INPUT_PARAMS.index(p) for p in MORPH_PARAMS]
mat_cols   = [INPUT_PARAMS.index(p) for p in MAT_PARAMS]
hemo_cols  = [INPUT_PARAMS.index(p) for p in HEMO_PARAMS]

subsets = {
    'Morphology only':   morph_cols,
    'Material only':     mat_cols,
    'Hemodynamics only': hemo_cols,
    'Full':              list(range(len(INPUT_PARAMS))),
}

# ============================================================
# STEP 1: SUBSET MODEL COMPARISON
# ============================================================
print("\n" + "=" * 60)
print("STEP 1: SUBSET MODEL COMPARISON")
print("=" * 60)

results = {name: {} for name in STRESS_OUTPUTS}

for name in STRESS_OUTPUTS:
    y_full = all_targets[name]
    y_tr = y_full[idx_train]
    y_te = y_full[idx_test]

    print(f"\n{'─' * 50}")
    print(f"Output: {name} (log-space)")
    print(f"{'─' * 50}")

    for subset_name, cols in subsets.items():
        Xtr = X_train_full[:, cols]
        Xte = X_test_full[:, cols]
        n_dim = Xtr.shape[1]

        kernel = (ConstantKernel(1.0)
                  * RBF(length_scale=np.ones(n_dim))
                  + WhiteKernel(noise_level=0.1))

        gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5,
                                       normalize_y=True, random_state=SEED)
        gpr.fit(Xtr, y_tr)
        y_pred = gpr.predict(Xte)
        r2 = r2_score(y_te, y_pred)
        rmse = np.sqrt(mean_squared_error(y_te, y_pred))
        r2_orig = r2_score(np.exp(y_te), np.exp(y_pred))

        print(f"\n  {subset_name} ({n_dim} inputs) — RBF (ARD)  R2={r2:.4f}  RMSE={rmse:.4f}")
        print(f"      (original-space R2={r2_orig:.4f})")

        results[name][subset_name] = {
            'r2': r2, 'rmse': rmse, 'r2_orig': r2_orig, 'gpr': gpr,
        }

# Summary
print("\n" + "=" * 60)
print("STEP 1 SUMMARY: R² Comparison (log-space)")
print("=" * 60)
print(f"  {'Subset':<22s}", end='')
for name in STRESS_OUTPUTS:
    print(f"  {name:>12s}", end='')
print()
print("  " + "-" * 50)
for subset_name in subsets:
    print(f"  {subset_name:<22s}", end='')
    for name in STRESS_OUTPUTS:
        print(f"  {results[name][subset_name]['r2']:>12.4f}", end='')
    print()

# ============================================================
# STEP 2: TRUE GROUP SOBOL INDICES (Full model)
# ============================================================
print("\n" + "=" * 60)
print("STEP 2: TRUE GROUP SOBOL INDICES (Full model)")
print("=" * 60)

morph_set = set(MORPH_PARAMS)
mat_set   = set(MAT_PARAMS)

def group_of(p):
    if p in morph_set: return 'Morphology'
    if p in mat_set:   return 'Material'
    return 'Hemodynamics'

group_assignments = [group_of(p) for p in INPUT_PARAMS]

problem_grouped = {
    'num_vars': len(INPUT_PARAMS),
    'names': INPUT_PARAMS,
    'bounds': [[X_full_scaled[:, i].min(), X_full_scaled[:, i].max()]
               for i in range(len(INPUT_PARAMS))],
    'groups': group_assignments,
}

N_sobol = 1024
X_sobol = saltelli.sample(problem_grouped, N_sobol, calc_second_order=False)
print(f"Saltelli samples per output: {X_sobol.shape[0]}")

group_sobol = {}
group_names_sobol = list(dict.fromkeys(group_assignments))

for name in STRESS_OUTPUTS:
    gpr_full = results[name]['Full']['gpr']
    Y_sobol = gpr_full.predict(X_sobol)
    Si = sobol.analyze(problem_grouped, Y_sobol, calc_second_order=False)

    group_sobol[name] = {}
    print(f"\n--- {name} (true group Sobol) ---")
    for j, grp in enumerate(group_names_sobol):
        s1 = Si['S1'][j]
        st = Si['ST'][j]
        group_sobol[name][grp] = {'S1': s1, 'ST': st}
        print(f"  {grp:15s}  S1={s1:.4f}  ST={st:.4f}")

# ============================================================
# STEP 3: PLOTS
# ============================================================
print("\n" + "=" * 60)
print("STEP 3: PLOTS")
print("=" * 60)

# ── Plot 1: subset comparison ──
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
subset_names = list(subsets.keys())
colors = ['#4C72B0', '#DD8452', '#8172B3', '#55A868']

for idx, name in enumerate(STRESS_OUTPUTS):
    ax = axes[idx]
    r2_vals = [results[name][s]['r2'] for s in subset_names]
    bars = ax.bar(subset_names, r2_vals, color=colors)
    for bar, val in zip(bars, r2_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f'{val:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.set_ylabel('R² (log-space)')
    ax.set_title(f'{DISPLAY_NAME_OUTPUTS[name]}')
    ymax = max(r2_vals + [0.05])
    ax.set_ylim(min(0, min(r2_vals)) - 0.02, ymax * 1.18)
    ax.tick_params(axis='x', rotation=15)

fig.suptitle('Q3: Subset Model Comparison (Morph vs Mat vs Hemo vs Full)', fontsize=12)
fig.tight_layout()
fig.savefig('Q3_subset_comparison.png', dpi=150)
plt.close(fig)
print("Saved: Q3_subset_comparison.png")

# ── Plot 2: group Sobol ──
fig, axes = plt.subplots(1, 2, figsize=(11, 5))
for idx, name in enumerate(STRESS_OUTPUTS):
    ax = axes[idx]
    s1_vals = [group_sobol[name][g]['S1'] for g in group_names_sobol]
    st_vals = [group_sobol[name][g]['ST'] for g in group_names_sobol]

    x_pos = np.arange(len(group_names_sobol))
    width = 0.35
    bars1 = ax.bar(x_pos - width / 2, s1_vals, width, label='S1 (group)', color='steelblue')
    bars2 = ax.bar(x_pos + width / 2, st_vals, width, label='ST (group)', color='coral')

    for bar in list(bars1) + list(bars2):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=8)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(group_names_sobol)
    ax.set_ylabel('Group Sobol Index')
    ax.set_title(f'{DISPLAY_NAME_OUTPUTS[name]}')
    ax.legend(fontsize=8)

fig.suptitle('Q3: True Group Sobol Indices (Morph vs Mat vs Hemo)', fontsize=12)
fig.tight_layout()
fig.savefig('Q3_group_sobol.png', dpi=150)
plt.close(fig)
print("Saved: Q3_group_sobol.png")

print("\n" + "=" * 60)
print("Q3 ANALYSIS COMPLETE")
print("=" * 60)
