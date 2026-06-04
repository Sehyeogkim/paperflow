import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Wedge, Circle
A="fig5_assets/"

# 1) Hemodynamic pressure/flow (dual axis)
fig,ax=plt.subplots(figsize=(1.7,1.45),dpi=160)
t=np.linspace(0,1,200)
P=80+95*np.exp(-((t-0.28)/0.13)**2)+15*np.exp(-((t-0.5)/0.2)**2)
Q=420*np.exp(-((t-0.2)/0.09)**2)
ax.plot(t,P,color="#2b5fa6",lw=1.6); ax.set_ylim(40,200)
ax.set_ylabel("Pressure\n(mmHg)",color="#2b5fa6",fontsize=6.5); ax.tick_params(labelsize=6)
ax.set_xlabel("Time (s)",fontsize=6.5)
ax2=ax.twinx(); ax2.plot(t,Q,color="#c0392b",lw=1.4,ls="--"); ax2.set_ylim(0,650)
ax2.set_ylabel("Flow (mL/s)",color="#c0392b",fontsize=6.5); ax2.tick_params(labelsize=6)
ax.set_xticks([0,0.5,1.0])
plt.tight_layout(); plt.savefig(A+"hemo.png",bbox_inches="tight",facecolor="white"); plt.close()

# 2) Plaque morphology (stylized cross-section)
fig,ax=plt.subplots(figsize=(1.5,1.45),dpi=160); ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Circle((0,0),1.0,fc="#d98b7c",ec="#a85a4a",lw=1.2))      # vessel wall
ax.add_patch(Circle((0,0),0.78,fc="#f0f0ee",ec="none"))               # media/lumen area
ax.add_patch(Wedge((0,-0.05),0.72,200,340,fc="#e6c84e",ec="#b89a2e",lw=0.8))  # lipid
ax.add_patch(Circle((0,-0.3),0.28,fc="#fbfaf6",ec="#888",lw=0.8))     # lumen
ax.add_patch(Wedge((0,-0.3),0.34,20,160,width=0.07,fc="#6e6b2e"))     # fibrous cap
ax.set_xlim(-1.1,1.1); ax.set_ylim(-1.1,1.1)
plt.tight_layout(); plt.savefig(A+"morph.png",bbox_inches="tight",facecolor="white"); plt.close()

# 3) Material stress-strain
fig,ax=plt.subplots(figsize=(1.7,1.45),dpi=160)
e=np.linspace(0,30,100)
ax.plot(e,2.8*(1-np.exp(-e/7)),color="#2b5fa6",lw=1.6,label="Fibrous Cap")
ax.plot(e,1.2*(1-np.exp(-e/9)),color="#c0392b",lw=1.4,label="Lipid")
ax.plot(e,0.7*(1-np.exp(-e/11)),color="#3a8a4a",lw=1.4,label="Media")
ax.set_xlabel("Strain (%)",fontsize=6.5); ax.set_ylabel("Stress (MPa)",fontsize=6.5)
ax.set_ylim(0,3); ax.set_xlim(0,30); ax.tick_params(labelsize=6)
ax.legend(fontsize=5.2,frameon=False,loc="lower right")
plt.tight_layout(); plt.savefig(A+"stress.png",bbox_inches="tight",facecolor="white"); plt.close()

# 4) GPR surrogate scatter + band
fig,ax=plt.subplots(figsize=(1.9,1.35),dpi=160)
x=np.linspace(0,10,200); y=0.5+0.35*np.sin(x*0.9)
rng=np.linspace(0,10,22); ys=0.5+0.35*np.sin(rng*0.9)+np.random.default_rng(3).normal(0,0.06,22)
ax.fill_between(x,y-0.13,y+0.13,color="#b9a7d6",alpha=0.5)
ax.plot(x,y,color="#4b2e83",lw=1.6)
ax.scatter(rng,ys,s=7,color="#3a2466",zorder=5)
ax.set_xlabel("Input space",fontsize=6.5); ax.set_ylabel("VI",fontsize=6.5)
ax.set_xticks([]); ax.set_yticks([]); 
for s in ax.spines.values(): s.set_linewidth(0.8)
plt.tight_layout(); plt.savefig(A+"gpr.png",bbox_inches="tight",facecolor="white"); plt.close()

# 5) Sobol bar
fig,ax=plt.subplots(figsize=(1.9,1.45),dpi=160)
ax.bar(["Material","Hemodynamic","Morphological"],[0.93,0.59,0.22],
       color=["#5b2a86","#2b5fa6","#7a9a6d"],width=0.62,edgecolor="none")
ax.set_ylabel("Sobol $S_1$",fontsize=6.5); ax.set_ylim(0,1.0)
ax.set_yticks([0,0.5,1.0]); ax.tick_params(axis="y",labelsize=6); ax.tick_params(axis="x",labelsize=5.6)
for s in ["top","right"]: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(A+"sobol.png",bbox_inches="tight",facecolor="white"); plt.close()
print("assets done")
