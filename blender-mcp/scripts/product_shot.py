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
