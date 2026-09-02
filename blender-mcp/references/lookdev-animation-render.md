# Look Development, Animation, Rendering, and Performance

# 17. Lighting

Lighting should reveal the form and support the requested mood.

## 17.1 Product lighting

A robust product-lighting setup often uses:

- large key Area light;
- weaker fill Area light;
- rim/back Area light;
- neutral or slightly graded world;
- broad floor/background plane.

Large area lights create broad specular reflections that make bevels and material roughness legible.

## 17.2 Dramatic/cinematic lighting

Use motivated contrast:

- a dominant direction;
- controlled fill;
- practical/emissive sources;
- rim separation;
- volumetrics only if they support composition.

Avoid adding many random lights because the render “looks dark.” Diagnose exposure, world strength, material roughness, and light scale first.

## 17.3 Engine selection should be introspected

Do not assume an engine identifier from an old Blender version.

You can inspect valid render engine identifiers:

```python
scene = bpy.context.scene
prop = scene.render.bl_rna.properties.get("engine")
if prop:
    print([item.identifier for item in prop.enum_items])
```

Then select a supported engine.

## 17.4 Physical scale

Light size and distance matter. A 5 cm area light placed 10 m from a 1 m prop is not equivalent to a 3 m softbox 2 m away.

---

# 18. Cameras and Composition

## 18.1 Camera creation

```python
import bpy
from mathutils import Vector

cam_data = bpy.data.cameras.new("MCP_Camera_Data")
cam = bpy.data.objects.new("MCP_Camera", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam.location = (4.5, -6.0, 3.2)

def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

look_at(cam, (0, 0, 0.6))
cam.data.lens = 55
```

## 18.2 Lens choice

General heuristics:

- 24–35 mm: environmental, wide, more perspective;
- 45–70 mm: natural product/portrait-like perspective;
- 80–120 mm: compressed product/detail shots.

Use orthographic for technical/isometric views when requested.

## 18.3 Frame the actual bounds

Do not blindly point the camera at world origin if the object is elsewhere.

Calculate world-space bounding-box center:

```python
from mathutils import Vector

corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
center = sum(corners, Vector()) / len(corners)
print(center)
```

For multiple objects, combine all relevant bounds.

## 18.4 Depth of field

Use DOF intentionally. Do not blur most of the model if the user needs to inspect design detail.

---

# 19. Animation

## 19.1 Keyframe properties explicitly

```python
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)
obj.location = (0, 0, 2)
obj.keyframe_insert(data_path="location", frame=48)
```

## 19.2 Interpolation

For mechanical motion, linear interpolation may be more appropriate than default bezier easing.

```python
action = obj.animation_data.action
for fcurve in action.fcurves:
    for kp in fcurve.keyframe_points:
        kp.interpolation = 'LINEAR'
```

Use easing for natural motion.

## 19.3 Turntable

A product turntable is often best implemented using an Empty parent or rotating the product collection/root object, leaving camera and lighting stable.

## 19.4 Constraints and drivers

Use constraints for relationships rather than manually keyframing everything.

Examples:

- Track To / Damped Track for camera targeting;
- Copy Rotation for linked mechanical parts;
- Limit Rotation for hinges;
- driver for gear ratios.

Driver example concept:

- Gear B rotation Z = `-GearA.rotation_euler.z * teethA / teethB`

Avoid scripting hundreds of redundant keyframes when a driver expresses the mechanism exactly.

---

# 20. Rigging

Rigging requires careful mode management.

Typical armature workflow:

1. create armature object;
2. enter Edit Mode;
3. create/edit bones;
4. leave Edit Mode;
5. set pose constraints;
6. parent/deform mesh;
7. create or assign weights;
8. test poses.

## 20.1 Validate rig hierarchy

Check:

- bone parent relationships;
- connected status where appropriate;
- roll/orientation;
- deformation flags;
- constraints;
- vertex groups;
- extreme poses.

## 20.2 Do not call a rig “finished” after parenting

Test at least a few representative deformations.

For humanoid or organic rigs, shoulder, elbow, hip, knee, wrist, and neck regions need particular attention.

---

# 21. Physics and Simulation

Use physics only when it materially improves the result.

Potential systems:

- rigid bodies;
- cloth;
- soft body;
- fluid/smoke workflows;
- particle-like procedural systems;
- simulation zones in Geometry Nodes.

## 21.1 Simulation discipline

- verify real-world scale;
- set frame range;
- set deterministic seeds when available;
- keep collision geometry reasonable;
- use low-resolution tests before expensive final bakes;
- do not bake huge simulations before validating the setup.

## 21.2 Cache awareness

Simulation caches can become stale when source geometry changes. Re-bake or invalidate cache appropriately.

---

# 22. Rendering and Color Management

## 22.1 Preview first

Before a high-quality final render:

1. render small resolution;
2. use low/moderate sample count;
3. inspect composition and materials;
4. fix issues;
5. increase final quality only after the scene is correct.

## 22.2 Resolution

Set explicit output resolution for deliverables.

```python
scene = bpy.context.scene
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
```

## 22.3 Color management

Blender 4.x commonly uses AgX-oriented color management. Preserve a modern default unless the user requests a specific display transform or pipeline.

Do not randomly change view transforms to make an image “pop.” Prefer fixing lighting, exposure, and material values first.

## 22.4 Transparency

For product cutouts or compositing:

```python
scene.render.film_transparent = True
```

## 22.5 Compositor

Use compositor nodes when needed for:

- glare/bloom-like effects;
- color balance;
- denoise passes;
- alpha handling;
- depth-based effects;
- render-layer compositing.

Do not use post effects to hide modeling or lighting errors.

---

# 23. Performance and Complexity Management

## 23.1 Use instances

For repeated components such as:

- screws;
- bolts;
- seats;
- windows;
- trees;
- rocks;
- fence posts;

prefer shared mesh datablocks or Geometry Nodes instances.

## 23.2 Keep modifier segment counts proportional to camera distance

A 128-segment cylinder for a 2-pixel-wide screw is wasteful.

## 23.3 Avoid object explosion

10,000 individually named bolt objects are harder to manage than a Geometry Nodes instancing system.

## 23.4 Batch updates

Do not force dependency-graph updates inside tight loops unless necessary.

## 23.5 Avoid global orphan purge unless authorized

Global orphan purges can remove data the user intended to keep. If cleanup is required, remove only agent-owned orphan data when possible.

---

