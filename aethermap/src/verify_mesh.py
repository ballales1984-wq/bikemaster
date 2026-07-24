import json
from aethermap.render.terrain_enhancer import build_enhanced_heightfield
from aethermap.render.webgl_exporter import _terrain_mesh_from_hf

# Test con risoluzione 32 come nel viewer
hf = build_enhanced_heightfield(n=32, base_alt=0.0, height_scale=0.04, base_url='http://localhost:8000')
mesh = _terrain_mesh_from_hf(hf.reshape(6, 32, 32), 32)

print('Mesh validation:')
print(f'  positions: {len(mesh["positions"])} verts')
print(f'  normals: {len(mesh["normals"])} verts')
print(f'  indices: {len(mesh["indices"])} indices')
print(f'  grid_size: {mesh.get("grid_size", "N/A")}')
print(f'  faces: {mesh.get("faces", "N/A")}')

# Verifica normali
normals = mesh['normals']
print(f'  normal sample: {normals[0]}')
print(f'  normal length: {sum(x*x for x in normals[0])**0.5:.3f}')

# Verifica positions
positions = mesh['positions']
print(f'  position sample: {positions[0]}')
print(f'  position range: x=[{min(p[0] for p in positions):.4f}, {max(p[0] for p in positions):.4f}]')
print(f'                   y=[{min(p[1] for p in positions):.4f}, {max(p[1] for p in positions):.4f}]')
print(f'                   z=[{min(p[2] for p in positions):.4f}, {max(p[2] for p in positions):.4f}]')
