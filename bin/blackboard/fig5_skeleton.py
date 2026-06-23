import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(13, 5.2), dpi=130)
ax.set_xlim(0, 13); ax.set_ylim(0, 5.2); ax.axis("off")

EDGE="#333333"; FILL="#ffffff"; SUB="#f4f1ea"; ACC="#777777"

def box(x,y,w,h,title,lines,fc=FILL,bold_title=True):
    ax.add_patch(FancyBboxPatch((x,y),w,h, boxstyle="round,pad=0.02,rounding_size=0.12",
                 lw=1.4, ec=EDGE, fc=fc))
    if title:
        ax.text(x+w/2, y+h-0.28, title, ha="center", va="top",
                fontsize=10.5, fontweight="bold" if bold_title else "normal", color="#1a1a1a")
    for i,ln in enumerate(lines):
        ax.text(x+w/2, y+h-0.62-0.34*i, ln, ha="center", va="top", fontsize=8.3, color="#2d2d2d")

def arrow(x0,y0,x1,y1):
    ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1), arrowstyle="-|>", mutation_scale=16,
                 lw=1.6, color=ACC, shrinkA=0, shrinkB=0))

# stage banners
for i,(sx,label) in enumerate([(0.2,"Stage 1  —  Dataset Generation"),
                               (4.55,"Stage 2  —  Vulnerability Index Selection"),
                               (9.0,"Stage 3  —  Surrogate & Sensitivity")]):
    ax.add_patch(FancyBboxPatch((sx,4.5),3.85,0.5, boxstyle="round,pad=0.02,rounding_size=0.1",
                 lw=0, fc="#e7e2d6"))
    ax.text(sx+1.92,4.75,label, ha="center", va="center", fontsize=9.5, fontweight="bold", color="#3a3a3a")

# ---- Stage 1 ----
box(0.2,2.55,3.85,1.7,"Input Parameters",
    ["Morphology","Hemodynamics","Material"], fc=SUB)
box(0.2,0.55,3.85,1.55,"Cost-effective FSI\n(prior work, cited)",
    ["1,000-sample dataset","PSS , ΔPSS","(sphere-averaging)"])
arrow(2.12,2.55,2.12,2.10)

# ---- Stage 2 ----
box(4.55,2.55,3.85,1.7,"6 VI candidates",
    ["VI = stress / strength","stress = {PSS, ΔPSS}","α = {0.0, 0.5, 1.0}"], fc=SUB)
box(4.55,0.55,3.85,1.55,"7-criterion clinical screen",
    ["sign-agreement test","→ VI1 = ΔPSS / E_FC^0.5","→ VI2 = ΔPSS / E_FC^1.0"])
arrow(6.47,2.55,6.47,2.10)

# ---- Stage 3 ----
box(9.0,2.55,3.85,1.7,"GPR Surrogate",
    ["input → VI mapping","LAP 784 / CP 727"], fc=SUB)
box(9.0,0.55,3.85,1.55,"Sobol Sensitivity",
    ["S1 , S_total","Material > Hemo > Morph"])
arrow(10.92,2.55,10.92,2.10)

# inter-stage arrows
arrow(4.05,1.3,4.55,1.3)
arrow(8.40,1.3,9.0,1.3)

ax.text(6.5,0.12,"[ skeleton / wireframe — structure only, no styling ]", ha="center",
        fontsize=8, style="italic", color="#999")
plt.tight_layout()
plt.savefig("/tmp/fig5_skeleton.png", bbox_inches="tight", facecolor="white")
print("saved")
