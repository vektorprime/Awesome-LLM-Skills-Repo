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
