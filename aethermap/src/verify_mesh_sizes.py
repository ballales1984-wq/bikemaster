from aethermap.render.terrain_enhancer import build_enhanced_heightfield
from aethermap.render.webgl_exporter import _terrain_mesh_from_hf

res = 16
print(f'start res={res}')
hf = build_enhanced_heightfield(n=res, base_alt=0.0, height_scale=0.04, base_url='http://localhost:8001')
print('hf built')
mesh = _terrain_mesh_from_hf(hf.reshape(6, res, res), res)
print(f'res={res}: positions={len(mesh["positions"])} indices={len(mesh["indices"])}')
