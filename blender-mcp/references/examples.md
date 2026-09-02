# Advanced Worked Examples

# 27. Advanced Example 1 — Procedural Precision Gear

This example creates a real ring gear-style mesh with a central hole and repeated teeth, rather than merely placing boxes around a cylinder.

The construction uses four angular samples per tooth, creates inner and outer rings on top and bottom, closes the top/bottom surfaces, and builds both inner and outer walls.

```python
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
```

### Validation steps after running

1. inspect `MCP_PrecisionGear` with object info;
2. capture viewport screenshot;
3. confirm the central bore is open;
4. confirm all teeth are present and evenly spaced;
5. confirm bevel does not round away the tooth shape;
6. if it is a hero asset, add hub detail, keyed shaft slot, engraved numbering, or a secondary material.

### Advanced extensions

- Add a hub cylinder with bolt holes.
- Add a keyway cut using a boolean cube.
- Create a second gear and use a driver for mechanically correct counter-rotation.
- Generate an involute tooth profile mathematically when actual gear engineering accuracy is required.
- Add grease/wear shader masks driven by curvature or geometry attributes.

---

# 28. Advanced Example 2 — Detailed Sci-Fi Storage Crate

This example demonstrates a reliable layered hard-surface workflow. It avoids an unnecessarily fragile boolean stack while still creating primary, secondary, and tertiary detail.

It creates:

- rounded main body;
- front recessed/seam layer;
- front armor plate;
- corner guards;
- structural rails;
- vent slots;
- repeated hex bolts using shared mesh data;
- emissive accent strip;
- raised text label;
- side handles using curves;
- multiple materials.

```python
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
```

### Visual inspection goals

After building:

1. capture a front three-quarter screenshot;
2. verify the rails project enough to catch highlights;
3. verify vents do not float far in front of the plate;
4. verify the text faces outward;
5. inspect side handles from a side angle;
6. confirm the silhouette reads as a heavy manufactured container;
7. add scratches/decals only after the large forms are strong.

### Hero-detail extensions

For a higher-end asset:

- add true recessed panel cuts with a restrained boolean stack;
- add corner screws on side faces;
- add a top hatch;
- add hinge geometry;
- add small warning decals;
- introduce roughness variation;
- add edge wear using a procedural mask;
- create a latch mechanism with pivots;
- add a cable seal or RFID plate;
- UV unwrap and bake if exporting to a game engine.

---

# 29. Advanced Example 3 — Geometry Nodes Rivet Scatter

This example demonstrates a Blender 4.5-style Geometry Nodes modifier that scatters small rivet-like icospheres across a surface while preserving the original geometry.

Use this as a pattern for bolts, studs, lights, stones, droplets, or other repeated detail.

```python
import bpy

OBJ_NAME = "MCP_RivetPanel"
GROUP_NAME = "MCP_RivetScatter_GN"

# Create or reuse a panel object.
obj = bpy.data.objects.get(OBJ_NAME)
if obj is None:
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = OBJ_NAME
    obj.dimensions = (3.0, 2.0, 0.12)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Remove old group/modifier created by this example.
old_mod = obj.modifiers.get("MCP_RivetScatter")
if old_mod:
    obj.modifiers.remove(old_mod)
old_group = bpy.data.node_groups.get(GROUP_NAME)
if old_group and old_group.users == 0:
    bpy.data.node_groups.remove(old_group)

ng = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
ng.interface.new_socket(
    name="Geometry",
    in_out='INPUT',
    socket_type='NodeSocketGeometry',
)
ng.interface.new_socket(
    name="Geometry",
    in_out='OUTPUT',
    socket_type='NodeSocketGeometry',
)

nodes = ng.nodes
links = ng.links
nodes.clear()

gin = nodes.new("NodeGroupInput")
gin.location = (-620, 60)

gout = nodes.new("NodeGroupOutput")
gout.location = (520, 60)

scatter = nodes.new("GeometryNodeDistributePointsOnFaces")
scatter.location = (-360, -140)
if "Density" in scatter.inputs:
    scatter.inputs["Density"].default_value = 12.0

ico = nodes.new("GeometryNodeMeshIcoSphere")
ico.location = (-360, -360)
if "Radius" in ico.inputs:
    ico.inputs["Radius"].default_value = 0.035
if "Subdivisions" in ico.inputs:
    ico.inputs["Subdivisions"].default_value = 2

instance = nodes.new("GeometryNodeInstanceOnPoints")
instance.location = (-80, -180)

join = nodes.new("GeometryNodeJoinGeometry")
join.location = (270, 60)

# Connect using names after checking they exist.
links.new(gin.outputs["Geometry"], scatter.inputs["Mesh"])
links.new(scatter.outputs["Points"], instance.inputs["Points"])
links.new(ico.outputs["Mesh"], instance.inputs["Instance"])
links.new(gin.outputs["Geometry"], join.inputs["Geometry"])
links.new(instance.outputs["Instances"], join.inputs["Geometry"])
links.new(join.outputs["Geometry"], gout.inputs["Geometry"])

mod = obj.modifiers.new("MCP_RivetScatter", 'NODES')
mod.node_group = ng

print({
    "ok": True,
    "object": obj.name,
    "node_group": ng.name,
    "nodes": [n.bl_idname for n in nodes],
    "interface": [
        (getattr(i, "name", ""), getattr(i, "identifier", ""), getattr(i, "in_out", ""))
        for i in ng.interface.items_tree
    ],
})
```

### Important artistic note

A raw face scatter places rivets everywhere. For production art, control the selection using:

- face sets/material index;
- named attributes;
- procedural masks;
- edge-distance fields;
- a dedicated emitter mesh;
- curves converted to points;
- explicit grid point placement.

The purpose of this example is to establish the modern 4.5 node-interface and instancing pattern.

---

# 30. Advanced Example 4 — Product Shot Around an Existing Object

This example creates a neutral studio floor, camera, and three area lights around a target object without deleting the model.

```python
import bpy
from mathutils import Vector

TARGET_NAME = "MCP_PrecisionGear"  # change to actual target

target = bpy.data.objects.get(TARGET_NAME)
if target is None:
    raise RuntimeError(f"Target not found: {TARGET_NAME}")

# World-space bounding center.
corners = [target.matrix_world @ Vector(c) for c in target.bound_box]
center = sum(corners, Vector()) / len(corners)
max_dim = max(target.dimensions)

# Floor.
if bpy.data.objects.get("MCP_StudioFloor") is None:
    bpy.ops.mesh.primitive_plane_add(size=max(8.0, max_dim * 5.0), location=(center.x, center.y, center.z - target.dimensions.z * 0.55))
    floor = bpy.context.active_object
    floor.name = "MCP_StudioFloor"
    mat = bpy.data.materials.new("MCP_StudioFloor_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.08, 0.08, 0.085, 1)
        bsdf.inputs["Roughness"].default_value = 0.55
    floor.data.materials.append(mat)

# Camera.
cam = bpy.data.objects.get("MCP_StudioCamera")
if cam is None:
    cam_data = bpy.data.cameras.new("MCP_StudioCamera_Data")
    cam = bpy.data.objects.new("MCP_StudioCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam)

cam.location = center + Vector((max_dim * 2.6, -max_dim * 3.2, max_dim * 1.9))
cam.data.lens = 58
cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam


def area_light(name, location, energy, size, color, target_pt):
    obj = bpy.data.objects.get(name)
    if obj is None:
        data = bpy.data.lights.new(name + "_Data", type='AREA')
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.data.energy = energy
    obj.data.shape = 'DISK'
    obj.data.size = size
    obj.data.color = color
    obj.rotation_euler = (Vector(target_pt) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj

area_light(
    "MCP_Key",
    center + Vector((-max_dim * 2.0, -max_dim * 2.2, max_dim * 3.0)),
    950,
    max_dim * 2.2,
    (1.0, 0.91, 0.82),
    center,
)
area_light(
    "MCP_Fill",
    center + Vector((max_dim * 2.7, -max_dim * 1.2, max_dim * 1.3)),
    430,
    max_dim * 2.5,
    (0.75, 0.86, 1.0),
    center,
)
area_light(
    "MCP_Rim",
    center + Vector((0, max_dim * 2.4, max_dim * 2.4)),
    800,
    max_dim * 1.8,
    (1.0, 0.65, 0.35),
    center,
)

scene = bpy.context.scene
scene.render.resolution_x = 1280
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100

print({
    "ok": True,
    "camera": cam.name,
    "target_center": [round(v, 4) for v in center],
    "target_dimensions": [round(v, 4) for v in target.dimensions],
    "lights": ["MCP_Key", "MCP_Fill", "MCP_Rim"],
})
```

After running, render or capture a camera view and adjust based on visual feedback. Light energy is scene-dependent; do not treat the example values as universal physical truth.

---

# 31. Advanced Modeling Recipes

## 31.1 Detailed mechanical panel

Recommended approach:

1. rounded base slab;
2. inset panel seam;
3. one or two true boolean cutouts;
4. raised frame rails;
5. repeated bolts via linked mesh or Geometry Nodes;
6. vents as layered geometry or cut slots;
7. decals/labels;
8. two to four materials;
9. subtle procedural roughness;
10. grazing light to reveal bevels.

## 31.2 Stylized building

1. block building volumes;
2. create one window module;
3. instance it with arrays/Geometry Nodes;
4. add cornices/trim as curves or extruded profiles;
5. add roof silhouette;
6. create material palette;
7. add controlled irregularity;
8. scatter props/vegetation using instances.

## 31.3 Industrial cable bundle

1. model connector ends;
2. define several curves;
3. vary curve radius slightly;
4. assign rubber material;
5. add clamps at intervals;
6. use bevel resolution appropriate to camera distance;
7. convert to mesh only for export if required.

## 31.4 Procedural fence

1. create one post and one rail module;
2. build a guide curve;
3. resample curve;
4. instance posts on points;
5. align posts to a chosen axis or terrain normal;
6. generate rails along curve;
7. preserve instances.

## 31.5 Hero product bottle

1. create side profile curve;
2. revolve/screw around axis;
3. bevel lip and base;
4. create separate cap;
5. create label mesh or UV label;
6. glass/plastic material;
7. studio lighting;
8. 70–100 mm camera for premium product compression.

---

