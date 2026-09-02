import bpy
import math
from mathutils import Vector

NAME = "MCP_PrecisionGear"
COLL_NAME = "MCP_Gear_Example"

# Remove only the old example object.
old = bpy.data.objects.get(NAME)
if old:
    bpy.data.objects.remove(old, do_unlink=True)

coll = bpy.data.collections.get(COLL_NAME)
if coll is None:
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)

teeth = 28
root_radius = 1.25
outer_radius = 1.52
inner_radius = 0.46
thickness = 0.30
z0 = -thickness * 0.5
z1 = thickness * 0.5
samples_per_tooth = 4
count = teeth * samples_per_tooth

verts = []
faces = []

# Tooth profile repeats root -> outer -> outer -> root for each tooth.
def radius_for_index(i):
    phase = i % samples_per_tooth
    if phase in (1, 2):
        return outer_radius
    return root_radius

# Vertex layout per angular sample:
# 0: bottom inner
# 1: bottom outer/toothed
# 2: top inner
# 3: top outer/toothed
for i in range(count):
    a = 2.0 * math.pi * i / count
    ca, sa = math.cos(a), math.sin(a)
    ro = radius_for_index(i)
    verts.extend([
        (inner_radius * ca, inner_radius * sa, z0),
        (ro * ca, ro * sa, z0),
        (inner_radius * ca, inner_radius * sa, z1),
        (ro * ca, ro * sa, z1),
    ])

for i in range(count):
    j = (i + 1) % count
    bi0, bo0, ti0, to0 = 4*i, 4*i+1, 4*i+2, 4*i+3
    bi1, bo1, ti1, to1 = 4*j, 4*j+1, 4*j+2, 4*j+3

    # Top annulus section.
    faces.append((ti0, to0, to1, ti1))
    # Bottom annulus section, reversed winding.
    faces.append((bi1, bo1, bo0, bi0))
    # Outer toothed wall.
    faces.append((bo0, bo1, to1, to0))
    # Inner bore wall.
    faces.append((bi1, bi0, ti0, ti1))

mesh = bpy.data.meshes.new(NAME + "_Mesh")
mesh.from_pydata(verts, [], faces)
mesh.validate(verbose=False)
mesh.update()

obj = bpy.data.objects.new(NAME, mesh)
coll.objects.link(obj)

# Flat faces preserve crisp tooth planes. Bevel provides controlled highlights.
for poly in mesh.polygons:
    poly.use_smooth = False

bevel = obj.modifiers.new("MCP_Gear_Bevel", 'BEVEL')
bevel.width = 0.035
bevel.segments = 3
if hasattr(bevel, "limit_method"):
    bevel.limit_method = 'ANGLE'
if hasattr(bevel, "harden_normals"):
    bevel.harden_normals = True

# Dark machined steel material.
mat = bpy.data.materials.get("MCP_Gear_Steel")
if mat is None:
    mat = bpy.data.materials.new("MCP_Gear_Steel")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    if "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = (0.075, 0.085, 0.10, 1)
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 1.0
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.24
mesh.materials.append(mat)

print({
    "ok": True,
    "object": obj.name,
    "teeth": teeth,
    "base_verts": len(mesh.vertices),
    "base_faces": len(mesh.polygons),
    "dimensions": [round(v, 4) for v in obj.dimensions],
    "modifiers": [(m.name, m.type) for m in obj.modifiers],
})
