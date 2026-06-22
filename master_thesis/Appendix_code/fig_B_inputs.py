#!/usr/bin/env python3
"""
Appendix B input figure: the two non-derivable empirical inputs.
  (a) coronary inflow waveform Q(t)   <- inflow.dat
  (b) normalized elastance e(x)=E/Emax <- elastance.dat   (x = t/t_sys)

Everything else in Appendix B (P_in, P_myo) is derived from these two curves
plus the equations/Table B1, so only these two are plotted here.

Output: figures/fig_B_inputs.svg (vector).
"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # master_thesis/
DATA = ROOT / "data" / "input_parameter"
OUT  = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)

q   = np.loadtxt(DATA / "inflow.dat")     # [t_norm, Q]
ela = np.loadtxt(DATA / "elastance.dat")  # [x=t/t_sys, E/Emax]

# Arial if present, else Liberation Sans (metric-identical Arial substitute on Linux)
_sans = ["Arial", "Liberation Sans", "Nimbus Sans"]
_math = "Arial" if any("arial" in f.lower() for f in
                        __import__("matplotlib").font_manager.get_font_names()) else "Liberation Sans"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": _sans, "font.size": 11,
    "mathtext.fontset": "custom",
    "mathtext.rm": _math, "mathtext.it": f"{_math}:italic", "mathtext.bf": f"{_math}:bold",
    "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.direction": "out", "ytick.direction": "out",
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.2, 3.3))

# (a) inflow Q(t)
ax1.plot(q[:, 0], q[:, 1], color="#1f4e79", lw=1.8)
ax1.axhline(0, color="0.6", lw=0.6, ls="--")
ax1.set_xlabel(r"Normalized cycle time  $t/T$")
ax1.set_ylabel(r"Coronary inflow  $Q(t)$  [cc s$^{-1}$]")
ax1.set_xlim(0, 1)

# (b) normalized elastance e(x)
ax2.plot(ela[:, 0], ela[:, 1], color="#7a1f1f", lw=1.8)
ax2.axvline(1.0, color="0.5", lw=0.8, ls=":")
ax2.set_xlabel(r"$x = t/t_\mathrm{sys}$")
ax2.set_ylabel(r"Normalized elastance  $e = E/E_\mathrm{max}$")
ax2.set_xlim(ela[:, 0].min(), ela[:, 0].max())
ax2.set_ylim(0, 1.05)

fig.tight_layout()
svg = OUT / "fig_B_inputs.svg"
fig.savefig(svg)
fig.savefig(svg.with_suffix(".png"), dpi=200)
plt.close(fig)
print(f"saved -> {svg}")
