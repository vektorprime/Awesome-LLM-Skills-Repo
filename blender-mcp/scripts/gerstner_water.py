import bpy
import math
from mathutils import Vector

COLL_NAME = "MCP_Water_Example"
PREFIX = "MCP_Water_"
NAME = PREFIX + "GerstnerSurface"

for obj in list(bpy.data.objects):
    if obj.name.startswith(PREFIX):
        bpy.data.objects.remove(obj, do_unlink=True)

coll = bpy.data.collections.get(COLL_NAME)
if coll is None:
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)

# Each tuple: direction angle radians, wavelength meters, amplitude meters, steepness, phase offset.
waves = [
    (math.radians(18.0), 5.8, 0.30, 0.46, 0.0),
    (math.radians(71.0), 3.1, 0.16, 0.36, 1.2),
    (math.radians(132.0), 1.75, 0.085, 0.28, 2.7),
    (math.radians(-33.0), 0.92, 0.038, 0.18, 0.4),
]

g = 9.81
size = 20.0
resolution = 145
half = size * 0.5
TIME = 0.0


def gerstner_point(x, y, time):
    p = Vector((x, y, 0.0))
    for angle, wavelength, amp, steepness, phase0 in waves:
        d = Vector((math.cos(angle), math.sin(angle)))
        k = 2.0 * math.pi / wavelength
        omega = math.sqrt(g * k)
        phase = k * (d.x * x + d.y * y) - omega * time + phase0

        # Horizontal displacement gives the characteristic sharpened crest.
        q = steepness
        p.x += q * amp * d.x * math.cos(phase)
        p.y += q * amp * d.y * math.cos(phase)
        p.z += amp * math.sin(phase)
    return p

verts = []
faces = []
for iy in range(resolution):
    y = -half + size * iy / (resolution - 1)
    for ix in range(resolution):
        x = -half + size * ix / (resolution - 1)
        verts.append(tuple(gerstner_point(x, y, TIME)))

for iy in range(resolution - 1):
    for ix in range(resolution - 1):
        a = iy * resolution + ix
        b = a + 1
        c = a + resolution + 1
        d = a + resolution
        faces.append((a, b, c, d))

mesh = bpy.data.meshes.new(NAME + "_Mesh")
mesh.from_pydata(verts, [], faces)
mesh.validate(verbose=False)
mesh.update()

obj = bpy.data.objects.new(NAME, mesh)
coll.objects.link(obj)
for poly in mesh.polygons:
    poly.use_smooth = True

solid = obj.modifiers.new("MCP_Water_Thickness", 'SOLIDIFY')
solid.thickness = 0.035
solid.offset = -1.0

mat = bpy.data.materials.get("MCP_Water_Material") or bpy.data.materials.new("MCP_Water_Material")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes.get("Principled BSDF")
out = nodes.get("Material Output")

if bsdf:
    if "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = (0.012, 0.055, 0.072, 1.0)
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.08
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.333
    for socket_name in ("Transmission Weight", "Transmission"):
        if socket_name in bsdf.inputs:
            bsdf.inputs[socket_name].default_value = 0.92
            break

# Add mild volumetric absorption so thicker water reads darker.
if out:
    absorption = nodes.get("MCP_Water_Absorption")
    if absorption is None:
        absorption = nodes.new("ShaderNodeVolumeAbsorption")
        absorption.name = "MCP_Water_Absorption"
    if "Color" in absorption.inputs:
        absorption.inputs["Color"].default_value = (0.03, 0.20, 0.24, 1.0)
    if "Density" in absorption.inputs:
        absorption.inputs["Density"].default_value = 0.16
    if "Volume" in out.inputs and not out.inputs["Volume"].is_linked:
        links.new(absorption.outputs["Volume"], out.inputs["Volume"])

mesh.materials.append(mat)

print({
    "ok": True,
    "object": obj.name,
    "resolution": resolution,
    "verts": len(mesh.vertices),
    "faces": len(mesh.polygons),
    "wave_count": len(waves),
    "dimensions": [round(v, 3) for v in obj.dimensions],
})
