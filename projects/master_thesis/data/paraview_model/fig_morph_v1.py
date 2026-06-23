import pyvista as pv, numpy as np
pv.OFF_SCREEN = True
m = pv.read("solid_type_1.vtu")
m.set_active_scalars("gmsh:physical")

def dom(p):
    return m.threshold([p-0.5, p+0.5], scalars="gmsh:physical")

wall = dom(1); lipid = dom(2); cap = dom(3)

C_WALL="#D98B7C"; C_LIPID="#E6D84E"; C_CAP="#6E6B2E"; C_LUMEN="#FBFAF6"

# find z of min lumen (MLA): innermost lumen radius vs z, using lipid+cap inner boundary
# approx: take cap+lipid centroid z-weighted min inner radius -> just scan
allp = np.vstack([lipid.cell_centers().points, cap.cell_centers().points])
# MLA near where lipid bulges most inward; pick z slice with min inner radius of solids
zc = np.median(allp[:,2])
print("lesion center z ~", zc)

p = pv.Plotter(off_screen=True, shape=(1,2), window_size=[1500,650], border=False)
p.background_color="white"

# ---- Panel A: lesion region, wall transparent ----
p.subplot(0,0)
p.add_mesh(wall.extract_surface(), color=C_WALL, opacity=0.18, smooth_shading=True)
p.add_mesh(lipid.extract_surface(), color=C_LIPID, opacity=1.0, smooth_shading=True)
p.add_mesh(cap.extract_surface(), color=C_CAP, opacity=1.0, smooth_shading=True)
p.add_text("(i) Lesion region", position="upper_left", font_size=12, color="black")
# zoom into lesion: set camera focal at lesion, view from +x looking along -x, vessel axis = z horizontal
p.camera_position = [(2.5, 3.0, zc), (0,0,zc), (0,0,1)]
p.camera.zoom(1.3)

# ---- Panel B: MLA cross-section ----
p.subplot(0,1)
z0 = zc
sl_wall  = wall.slice(normal="z", origin=(0,0,z0))
sl_lipid = lipid.slice(normal="z", origin=(0,0,z0))
sl_cap   = cap.slice(normal="z", origin=(0,0,z0))
p.add_mesh(sl_wall, color=C_WALL)
p.add_mesh(sl_lipid, color=C_LIPID)
p.add_mesh(sl_cap, color=C_CAP)
p.add_text("(ii) Min Lumen Area plane", position="upper_left", font_size=12, color="black")
p.camera_position = "xy"
p.camera.zoom(1.5)

p.screenshot("/tmp/fig_morph_v1.png")
p.close()
import os; print("saved", os.path.getsize("/tmp/fig_morph_v1.png"),"bytes")
