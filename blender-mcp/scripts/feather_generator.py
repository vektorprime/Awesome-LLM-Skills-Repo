import bpy
import math
import random
from mathutils import Vector

COLL_NAME = "MCP_Feather_Example"
PREFIX = "MCP_Feather_"
SEED = 17
random.seed(SEED)

# Rebuild only this example.
for obj in list(bpy.data.objects):
    if obj.name.startswith(PREFIX):
        bpy.data.objects.remove(obj, do_unlink=True)

coll = bpy.data.collections.get(COLL_NAME)
if coll is None:
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)


def link_only(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def principled_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        for socket_name in ("Subsurface Weight", "Subsurface"):
            if socket_name in bsdf.inputs:
                bsdf.inputs[socket_name].default_value = 0.035
                break
    return mat


vane_mat = principled_material(
    "MCP_Feather_VaneMat",
    (0.105, 0.055, 0.025, 1.0),
    roughness=0.62,
)
shaft_mat = principled_material(
    "MCP_Feather_ShaftMat",
    (0.72, 0.53, 0.29, 1.0),
    roughness=0.43,
)
barb_mat = principled_material(
    "MCP_Feather_BarbMat",
    (0.075, 0.035, 0.016, 1.0),
    roughness=0.68,
)

length = 3.2
max_width = 0.88
samples = 64


def centerline(t):
    # Feather grows in +Z with a mild swept curve and camber.
    return Vector((
        0.10 * math.sin(t * math.pi * 0.92) + 0.035 * t,
        0.12 * math.sin(t * math.pi) ** 1.7,
        length * t,
    ))


def width_profile(t):
    # Narrow calamus, broad middle, tapered tip.
    core = math.sin(math.pi * max(0.0, min(1.0, t))) ** 0.72
    base_gate = min(1.0, t / 0.10)
    tip_gate = min(1.0, (1.0 - t) / 0.07)
    return max_width * core * base_gate * tip_gate


# --- vane mesh ---
verts = []
faces = []
left_edge = []
right_edge = []
centers = []

for i in range(samples):
    t = i / (samples - 1)
    c = centerline(t)
    w = width_profile(t)

    # Intentional asymmetry is important for a convincing flight feather.
    edge_noise_l = 1.0 + 0.030 * math.sin(i * 1.71) + 0.012 * math.sin(i * 4.33)
    edge_noise_r = 1.0 + 0.022 * math.sin(i * 1.29 + 0.7)
    left_w = w * 0.90 * edge_noise_l
    right_w = w * 1.10 * edge_noise_r

    # Slight downward camber toward the outer vane edges.
    left = c + Vector((-left_w, -0.035 * (left_w / max_width) ** 2, 0.0))
    right = c + Vector((right_w, -0.050 * (right_w / max_width) ** 2, 0.0))

    centers.append(c)
    left_edge.append(left)
    right_edge.append(right)
    verts.extend([tuple(left), tuple(right)])

for i in range(samples - 1):
    a, b = 2 * i, 2 * i + 1
    c, d = 2 * (i + 1), 2 * (i + 1) + 1
    faces.append((a, c, d, b))

mesh = bpy.data.meshes.new(PREFIX + "VaneMesh")
mesh.from_pydata(verts, [], faces)
mesh.validate(verbose=False)
mesh.update()

vane = bpy.data.objects.new(PREFIX + "Vane", mesh)
coll.objects.link(vane)
mesh.materials.append(vane_mat)

for poly in mesh.polygons:
    poly.use_smooth = True

solid = vane.modifiers.new("MCP_Vane_Thickness", 'SOLIDIFY')
solid.thickness = 0.006
solid.offset = 0.0

bevel = vane.modifiers.new("MCP_Vane_EdgeSoftness", 'BEVEL')
bevel.width = 0.004
bevel.segments = 2

# --- rachis / shaft ---
curve = bpy.data.curves.new(PREFIX + "RachisCurve", 'CURVE')
curve.dimensions = '3D'
curve.resolution_u = 2
curve.bevel_depth = 0.025
curve.bevel_resolution = 4
curve.resolution_u = 2
curve.use_fill_caps = True

spline = curve.splines.new('POLY')
spline.points.add(samples - 1)
for i, p in enumerate(centers):
    t = i / (samples - 1)
    cp = spline.points[i]
    cp.co = (*p, 1.0)
    cp.radius = 1.15 - 0.82 * (t ** 0.90)

rachis = bpy.data.objects.new(PREFIX + "Rachis", curve)
coll.objects.link(rachis)
curve.materials.append(shaft_mat)

# --- barbs: many fine curve splines sharing one curve datablock ---
barb_curve = bpy.data.curves.new(PREFIX + "BarbsCurve", 'CURVE')
barb_curve.dimensions = '3D'
barb_curve.resolution_u = 1
barb_curve.bevel_depth = 0.0055
barb_curve.bevel_resolution = 2
barb_curve.resolution_u = 1
barb_curve.use_fill_caps = True

barb_count = 0
for i in range(5, samples - 3):
    t = i / (samples - 1)

    # Skip some barbs to create natural separations/gaps in the vane.
    if 0.23 < t < 0.88 and random.random() < 0.085:
        continue

    c = centers[i]
    for side, edge in ((-1.0, left_edge[i]), (1.0, right_edge[i])):
        # A four-point barb curves slightly toward the feather tip.
        root = c + Vector((side * 0.018, 0.0, 0.0))
        span = edge - root
        tip_bias = Vector((0.0, 0.0, 0.030 + 0.080 * t))
        p1 = root + span * 0.34 + tip_bias * 0.30
        p2 = root + span * 0.70 + tip_bias * 0.75
        p3 = edge + tip_bias

        # Small irregularity at outer edge makes the silhouette less synthetic.
        p3.x += side * random.uniform(-0.012, 0.012)
        p3.y += random.uniform(-0.008, 0.008)
        p3.z += random.uniform(-0.010, 0.018)

        sp = barb_curve.splines.new('POLY')
        sp.points.add(3)
        for point, co in zip(sp.points, (root, p1, p2, p3)):
            point.co = (*co, 1.0)
        barb_count += 1

barbs = bpy.data.objects.new(PREFIX + "Barbs", barb_curve)
coll.objects.link(barbs)
barb_curve.materials.append(barb_mat)

# --- calamus/quill at the base ---
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(0.0, 0.0, -0.10))
calamus = bpy.context.active_object
calamus.name = PREFIX + "Calamus"
calamus.scale = (0.055, 0.055, 0.18)
link_only(calamus)
calamus.data.materials.append(shaft_mat)

print({
    "ok": True,
    "objects": [o.name for o in coll.objects],
    "vane_vertices": len(mesh.vertices),
    "vane_faces": len(mesh.polygons),
    "barb_splines": barb_count,
    "length": length,
    "max_width": max_width,
})
