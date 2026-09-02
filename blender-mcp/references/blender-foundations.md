# Blender Foundations and Modeling

# 6. Blender Data Model — Required Mental Model

## 6.1 Objects and datablocks are different

A Blender object is a transform/container referencing data.

Examples:

- mesh object → `bpy.types.Mesh`
- curve object → `bpy.types.Curve`
- camera object → `bpy.types.Camera`
- light object → `bpy.types.Light`
- armature object → `bpy.types.Armature`

Two objects can share the same mesh datablock.

```python
copy_obj = source.copy()
# copy_obj.data still points to source.data unless copied explicitly.

unique_obj = source.copy()
unique_obj.data = source.data.copy()
```

Use shared mesh data for repeated bolts, rivets, screws, and repeated props when independent mesh editing is not required.

## 6.2 Collections are organizational and linking structures

An object must be linked to at least one collection to appear in the scene.

Do not create datablocks and forget to link them.

## 6.3 Context is temporary state

`bpy.context` describes the current UI/context state. It is not the same thing as the scene database.

When using operators, deliberately set:

- mode;
- active object;
- selected objects.

## 6.4 Evaluated geometry differs from original geometry

Modifiers, Geometry Nodes, and some procedural systems create evaluated geometry that is not directly present in the base mesh.

Use the dependency graph when inspecting the final result.

```python
import bpy

depsgraph = bpy.context.evaluated_depsgraph_get()
obj = bpy.data.objects["MCP_Object"]
eval_obj = obj.evaluated_get(depsgraph)
mesh = eval_obj.to_mesh()
try:
    print({
        "verts": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polys": len(mesh.polygons),
    })
finally:
    eval_obj.to_mesh_clear()
```

Blender 4.5 also adds improved evaluated-geometry access around its GeometrySet APIs. Prefer documented 4.5 approaches when inspecting Geometry Nodes results.

---

# 7. Units, Transforms, and Spatial Conventions

## 7.1 Use coherent real-world scale

Default recommendation for general-purpose assets:

- unit system: Metric;
- 1 Blender unit = 1 meter;
- model products at plausible dimensions.

Examples:

- coffee mug: ~0.09–0.12 m tall;
- chair seat: ~0.45 m high;
- door: ~2.0–2.2 m high;
- shipping crate: often ~1 m scale;
- small screw head: millimeters, not tens of centimeters.

## 7.2 Scale matters for modifiers

Unapplied nonuniform scale commonly produces inconsistent:

- bevel widths;
- array spacing;
- procedural texture scale;
- physics behavior.

For static modeled assets, apply scale before precision bevel and boolean work unless there is a reason not to.

## 7.3 Distinguish local and world space

Use `matrix_world` when comparing or positioning objects in world space.

```python
world_point = obj.matrix_world @ local_point
local_point = obj.matrix_world.inverted() @ world_point
```

## 7.4 Rotation conventions

Blender uses radians internally.

```python
from math import radians
obj.rotation_euler.z = radians(45)
```

For camera and rig orientation, quaternions are often more robust than manually guessed Euler angles.

---

# 8. Reusable Utility Toolkit

Use helpers like these to keep scripts readable and deterministic.

```python
import bpy
import math
from mathutils import Vector

PREFIX = "MCP_"


def ensure_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if coll.name not in {c.name for c in parent.children}:
        parent.children.link(coll)
    return coll


def move_to_collection(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    if obj.name not in coll.objects:
        coll.objects.link(obj)


def delete_owned(prefix=PREFIX):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix):
            bpy.data.objects.remove(obj, do_unlink=True)


def set_active(obj):
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_scale(obj):
    set_active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def ensure_material(name, base_color=(0.5, 0.5, 0.5, 1.0), metallic=0.0,
                    roughness=0.5):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = base_color
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = metallic
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
    return mat


def assign_material(obj, mat, slot=0):
    if not hasattr(obj.data, "materials"):
        return
    if len(obj.data.materials) <= slot:
        while len(obj.data.materials) < slot:
            obj.data.materials.append(None)
        obj.data.materials.append(mat)
    else:
        obj.data.materials[slot] = mat


def add_bevel(obj, width=0.02, segments=3, name="MCP_Bevel"):
    mod = obj.modifiers.get(name)
    if mod is None:
        mod = obj.modifiers.new(name=name, type='BEVEL')
    mod.width = width
    mod.segments = segments
    if hasattr(mod, "limit_method"):
        mod.limit_method = 'ANGLE'
    if hasattr(mod, "harden_normals"):
        mod.harden_normals = True
    return mod


def look_at(obj, target, track_axis='-Z', up_axis='Y'):
    target = Vector(target)
    direction = target - obj.location
    if direction.length < 1e-8:
        return
    obj.rotation_euler = direction.to_track_quat(track_axis, up_axis).to_euler()


def object_report(obj):
    report = {
        "name": obj.name,
        "type": obj.type,
        "location": [round(v, 5) for v in obj.location],
        "rotation": [round(v, 5) for v in obj.rotation_euler],
        "scale": [round(v, 5) for v in obj.scale],
        "dimensions": [round(v, 5) for v in obj.dimensions],
        "modifiers": [(m.name, m.type) for m in obj.modifiers],
    }
    if obj.type == 'MESH':
        report.update({
            "verts": len(obj.data.vertices),
            "edges": len(obj.data.edges),
            "polys": len(obj.data.polygons),
        })
    return report
```

### Important

The utility toolkit is a pattern, not an excuse to blindly paste the same code into every call. Use only what the current operation needs.

---

# 9. Choosing a Modeling Technique

Use this decision hierarchy.

## 9.1 Primitive + modifier modeling

Best for:

- furniture;
- mechanical forms;
- product bodies;
- architecture;
- hard-surface props;
- simple characters/blockouts.

Common primitives:

- cube;
- cylinder;
- sphere / UV sphere;
- ico sphere;
- cone;
- torus;
- plane;
- curve.

## 9.2 `Mesh.from_pydata`

Best when you can mathematically define vertices/faces.

Use for:

- gears;
- panels;
- architectural profiles;
- grids;
- generated low-poly forms;
- parametric shapes.

After creation:

```python
mesh.from_pydata(verts, edges, faces)
mesh.validate(verbose=False)
mesh.update()
```

## 9.3 BMesh

Best for more complex mesh construction or editing existing geometry.

```python
import bpy
import bmesh

obj = bpy.data.objects["MCP_Target"]
mesh = obj.data
bm = bmesh.new()
try:
    bm.from_mesh(mesh)
    # bmesh operations here
    bm.normal_update()
    bm.to_mesh(mesh)
finally:
    bm.free()
mesh.update()
```

Use `bmesh.ops` for controlled operations such as extrusion, inset, bevel, triangulation, dissolve, and transforms.

## 9.4 Curves

Best for:

- cables;
- ropes;
- hoses;
- rails;
- handles;
- pipes;
- wires;
- stylized strokes.

Curves are often more reliable and editable than constructing many tube segments manually.

## 9.5 Geometry Nodes

Best for:

- repeated details;
- scattering;
- arrays along curves;
- parametric architecture;
- procedural vegetation;
- instanced bolts/rivets;
- non-destructive variations;
- large systems where instancing improves performance.

## 9.6 Booleans

Best for meaningful cutouts and hard-surface intersections.

Do not use hundreds of booleans if layered geometry, normal maps, or Geometry Nodes would communicate the same visual detail more efficiently.

---

# 10. Hard-Surface Modeling Strategy

## 10.1 Detail hierarchy

Build in this order:

### Primary forms

The silhouette and large mass.

Examples:

- crate body;
- helmet shell;
- vehicle hull;
- furniture carcass.

### Secondary forms

Structural features.

Examples:

- rails;
- doors;
- major panels;
- handles;
- braces;
- wheel wells.

### Tertiary forms

Visual richness.

Examples:

- screws;
- vents;
- seams;
- engraved labels;
- warning stripes;
- cable clamps;
- chamfers;
- micro-panels.

Do not spend 300,000 polygons on tertiary detail before the primary silhouette is correct.

## 10.2 Bevels are essential

Perfectly sharp real-world edges usually look synthetic because they do not catch highlights.

Use bevel widths appropriate to scale.

As a starting heuristic:

- tiny manufactured prop: 0.2–2 mm;
- furniture: 1–8 mm;
- large crate/vehicle panels: 3–30 mm;
- stylized asset: larger as art direction requires.

Use enough segments for the final framing. Three segments is often sufficient for a medium-distance hard-surface prop; hero closeups may need more.

## 10.3 Boolean order

A common modifier order is:

1. symmetry/mirror;
2. major boolean cuts;
3. bevel;
4. normal/shading correction as appropriate;
5. subdivision only if the design requires it.

Modifier order is design-dependent. Inspect the evaluated result.

## 10.4 Boolean robustness

Before a boolean:

- apply or normalize scale where appropriate;
- avoid coincident coplanar surfaces;
- ensure cutter volume actually intersects target;
- use sufficiently clean operands;
- consider `EXACT` solver for difficult hard-surface cuts if available.

If a boolean fails:

1. inspect operand dimensions;
2. move cutter slightly to avoid coplanarity;
3. verify normals;
4. try a simpler cutter;
5. apply preceding transforms/modifiers only if justified.

## 10.5 Shading

Do not rely on legacy auto-smooth assumptions from older Blender tutorials. Blender's normal workflow has changed across 4.x.

Use Blender 4.5-compatible techniques:

- smooth or flat shading intentionally;
- sharp edges where needed;
- bevels to produce real highlight transitions;
- custom normals or Geometry Nodes normal tools for specialized workflows.

For mechanical assets, topology and bevel shape are more reliable than trying to hide bad topology using shading tricks.

---

# 11. Organic and Sculpt-Oriented Work

MCP automation can produce organic models, but the workflow differs from hard-surface modeling.

Recommended hierarchy:

1. block silhouette with primitives or simple mesh;
2. establish symmetry;
3. use subdivision or voxel remesh only where needed;
4. sculpt large forms before small forms;
5. retopologize if animation/deformation quality matters;
6. add microdetail through displacement/normal/bump rather than extreme base geometry.

## 11.1 Context caution

Sculpt operators can be more context-sensitive than direct mesh APIs. For procedural organic creation, consider:

- metaball-like construction converted to mesh;
- voxel remesh workflows;
- skin/subdivision techniques;
- Geometry Nodes;
- explicit mathematical surfaces.

## 11.2 Character quality

For characters, do not treat “a body made from spheres” as finished merely because it resembles a person from one angle. Validate:

- silhouette;
- joint placement;
- limb proportions;
- deformation topology if rigged;
- facial feature alignment;
- symmetry;
- material/eye orientation.

---

# 12. Curves for Cables, Handles, Tubes, and Wires

A robust curve helper:

```python
import bpy


def make_poly_tube(name, points, radius=0.02, bevel_resolution=3, collection=None):
    curve = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = bevel_resolution
    curve.resolution_u = 12

    spline = curve.splines.new(type='POLY')
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)

    obj = bpy.data.objects.new(name, curve)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj
```

For smoother manufactured handles, use Bezier splines and explicitly set handle types.

Curves are excellent for:

- U-shaped handles;
- cable bundles;
- piping around a machine;
- neon tubes;
- architectural handrails.

Convert to mesh only if required for downstream operations or export.

---

