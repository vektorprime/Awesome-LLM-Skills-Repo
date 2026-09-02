import bpy
import math
from mathutils import Vector

COLL_NAME = "MCP_SciFiCrate"
PREFIX = "MCP_Crate_"

# ---------- safe rebuild of this example only ----------
for obj in list(bpy.data.objects):
    if obj.name.startswith(PREFIX):
        bpy.data.objects.remove(obj, do_unlink=True)

coll = bpy.data.collections.get(COLL_NAME)
if coll is None:
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)


def move_to_coll(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def set_active(obj):
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_scale(obj):
    set_active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def add_bevel(obj, width, segments=3):
    mod = obj.modifiers.new("MCP_Bevel", 'BEVEL')
    mod.width = width
    mod.segments = segments
    if hasattr(mod, "limit_method"):
        mod.limit_method = 'ANGLE'
    if hasattr(mod, "harden_normals"):
        mod.harden_normals = True
    return mod


def make_box(name, loc, dims, material=None, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = dims
    apply_scale(obj)
    move_to_coll(obj)
    if bevel > 0:
        add_bevel(obj, bevel)
    if material:
        obj.data.materials.append(material)
    return obj


def make_material(name, color, metallic, roughness, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if emission is not None:
            # Socket names differ between Principled generations, so discover by name.
            for socket_name in ("Emission Color", "Emission"):
                if socket_name in bsdf.inputs:
                    bsdf.inputs[socket_name].default_value = emission
                    break
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


body_mat = make_material(
    "MCP_Crate_BodyMat",
    (0.075, 0.095, 0.115, 1),
    metallic=0.72,
    roughness=0.31,
)
armor_mat = make_material(
    "MCP_Crate_ArmorMat",
    (0.16, 0.19, 0.21, 1),
    metallic=0.55,
    roughness=0.37,
)
dark_mat = make_material(
    "MCP_Crate_DarkMat",
    (0.015, 0.02, 0.027, 1),
    metallic=0.6,
    roughness=0.46,
)
accent_mat = make_material(
    "MCP_Crate_AccentMat",
    (0.8, 0.15, 0.025, 1),
    metallic=0.25,
    roughness=0.28,
    emission=(1.0, 0.055, 0.006, 1),
    emission_strength=3.0,
)
label_mat = make_material(
    "MCP_Crate_LabelMat",
    (0.85, 0.88, 0.78, 1),
    metallic=0.0,
    roughness=0.48,
)

# ---------- primary form ----------
body = make_box(
    PREFIX + "Body",
    (0, 0, 0),
    (3.6, 2.4, 2.4),
    body_mat,
    bevel=0.12,
)

# Slightly oversized dark seam behind front panel.
seam = make_box(
    PREFIX + "Front_Seam",
    (0, -1.218, 0),
    (2.92, 0.055, 1.90),
    dark_mat,
    bevel=0.045,
)

# Front armor plate.
front = make_box(
    PREFIX + "Front_Plate",
    (0, -1.255, 0),
    (2.70, 0.085, 1.70),
    armor_mat,
    bevel=0.065,
)

# ---------- structural guards ----------
for x in (-1.64, 1.64):
    make_box(
        PREFIX + f"Guard_V_{'L' if x < 0 else 'R'}",
        (x, -1.265, 0),
        (0.26, 0.16, 2.12),
        armor_mat,
        bevel=0.05,
    )

for z in (-1.04, 1.04):
    make_box(
        PREFIX + f"Guard_H_{'B' if z < 0 else 'T'}",
        (0, -1.265, z),
        (3.12, 0.16, 0.25),
        armor_mat,
        bevel=0.05,
    )

# ---------- panel features ----------
# Emissive identity strip.
make_box(
    PREFIX + "Accent_Strip",
    (0, -1.314, 0.53),
    (1.58, 0.030, 0.095),
    accent_mat,
    bevel=0.025,
)

# Vents: dark inset bars on lower half.
vent_xs = [-0.72, -0.48, -0.24, 0.0, 0.24, 0.48, 0.72]
for i, x in enumerate(vent_xs):
    make_box(
        PREFIX + f"Vent_{i:02d}",
        (x, -1.314, -0.44),
        (0.105, 0.035, 0.48),
        dark_mat,
        bevel=0.018,
    )

# Small lower accent blocks.
for x in (-1.03, 1.03):
    make_box(
        PREFIX + f"Latch_{'L' if x < 0 else 'R'}",
        (x, -1.325, -0.58),
        (0.32, 0.055, 0.18),
        accent_mat,
        bevel=0.028,
    )

# ---------- one bolt mesh, many linked objects ----------
bpy.ops.mesh.primitive_cylinder_add(
    vertices=6,
    radius=0.085,
    depth=0.055,
    location=(0, 0, 0),
    rotation=(math.radians(90), 0, 0),
)
bolt_template = bpy.context.active_object
bolt_template.name = PREFIX + "Bolt_Template"
apply_scale(bolt_template)
move_to_coll(bolt_template)
bolt_template.data.materials.append(dark_mat)
add_bevel(bolt_template, 0.012, 2)

bolt_positions = [
    (-1.14, -1.335, 0.67),
    ( 1.14, -1.335, 0.67),
    (-1.14, -1.335,-0.67),
    ( 1.14, -1.335,-0.67),
    (-0.98, -1.335, 0.18),
    ( 0.98, -1.335, 0.18),
]

# Keep the first bolt visible and duplicate its mesh data for low memory cost.
bolt_template.location = bolt_positions[0]
for i, loc in enumerate(bolt_positions[1:], start=1):
    b = bolt_template.copy()
    b.data = bolt_template.data  # linked mesh
    b.name = PREFIX + f"Bolt_{i:02d}"
    b.location = loc
    coll.objects.link(b)

bolt_template.name = PREFIX + "Bolt_00"

# ---------- side handles as beveled curves ----------
def make_handle(name, side=1):
    # side = +1 right, -1 left
    x = side * 1.87
    pts = [
        (x, -0.52, 0.46),
        (x + side * 0.20, -0.52, 0.46),
        (x + side * 0.28, -0.20, 0.46),
        (x + side * 0.28,  0.20, 0.46),
        (x + side * 0.20,  0.52, 0.46),
        (x,  0.52, 0.46),
    ]
    data = bpy.data.curves.new(name + "_Curve", type='CURVE')
    data.dimensions = '3D'
    data.bevel_depth = 0.055
    data.bevel_resolution = 4
    data.resolution_u = 12
    spl = data.splines.new(type='BEZIER')
    spl.bezier_points.add(len(pts) - 1)
    for bp, co in zip(spl.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    data.materials.append(dark_mat)
    return obj

make_handle(PREFIX + "Handle_L", side=-1)
make_handle(PREFIX + "Handle_R", side=1)

# ---------- raised text label ----------
bpy.ops.object.text_add(
    location=(0.0, -1.342, 0.82),
    rotation=(math.radians(90), 0, 0),
)
text = bpy.context.active_object
text.name = PREFIX + "Label"
text.data.body = "A-17 // CARGO"
text.data.align_x = 'CENTER'
text.data.align_y = 'CENTER'
text.data.size = 0.20
text.data.extrude = 0.008
text.data.bevel_depth = 0.004
text.data.materials.append(label_mat)
move_to_coll(text)

# ---------- floor contact feet ----------
for x in (-1.42, 1.42):
    for y in (-0.82, 0.82):
        make_box(
            PREFIX + f"Foot_{x:+.2f}_{y:+.2f}",
            (x, y, -1.24),
            (0.36, 0.42, 0.18),
            dark_mat,
            bevel=0.045,
        )

print({
    "ok": True,
    "collection": COLL_NAME,
    "object_count": len(coll.objects),
    "body_dimensions": [round(v, 3) for v in body.dimensions],
    "materials": [body_mat.name, armor_mat.name, dark_mat.name, accent_mat.name, label_mat.name],
})
