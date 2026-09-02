"""Blender 4.5 LTS - deterministic static fur demo for Blender MCP.

Creates an MCP-owned ellipsoidal body and a Hair Curves object with tapered,
directionally groomed strands. The geometry is constructed directly with the
Blender Curves data API so the example is deterministic and MCP friendly.

This is intentionally a static procedural demonstration, not a replacement for
an animated guide groom. For a deforming hero character, use attached guide
Hair Curves plus Generate/Interpolate Hair Curves and Deform Curves on Surface.
"""

import bpy
import math
import random
from mathutils import Vector

PREFIX = "MCP_FurDemo"
COLLECTION_NAME = f"{PREFIX}_Collection"
BODY_NAME = f"{PREFIX}_Body"
FUR_NAME = "MCP_Fur"
BODY_MATERIAL = f"{PREFIX}_BodyMaterial"
FUR_MATERIAL = f"{PREFIX}_FurMaterial"

SEED = 71342
FUR_COUNT = 1400
POINTS_PER_CURVE = 6
ELLIPSOID_RADII = Vector((1.25, 0.90, 0.82))
BASE_LENGTH = 0.115
LENGTH_VARIATION = 0.42
ROOT_RADIUS = 0.0023
TIP_RADIUS = 0.00035
ROOT_LIFT = 0.58
LAY_STRENGTH = 0.92
FRIZZ = 0.028


def remove_owned_data():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX) or obj.name == FUR_NAME:
            bpy.data.objects.remove(obj, do_unlink=True)

    for curves in list(bpy.data.hair_curves):
        if curves.name.startswith(PREFIX) or curves.name == FUR_NAME:
            if curves.users == 0:
                bpy.data.hair_curves.remove(curves)

    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection and collection.users == 0:
        bpy.data.collections.remove(collection)


def get_or_create_collection():
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    return collection


def make_body_material():
    mat = bpy.data.materials.get(BODY_MATERIAL) or bpy.data.materials.new(BODY_MATERIAL)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (0.12, 0.055, 0.025, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.72
    return mat


def make_fur_material():
    mat = bpy.data.materials.get(FUR_MATERIAL) or bpy.data.materials.new(FUR_MATERIAL)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (260, 0)

    if bpy.context.scene.render.engine == 'CYCLES':
        shader = nodes.new("ShaderNodeBsdfHairPrincipled")
        shader.parametrization = 'COLOR'
        if "Color" in shader.inputs:
            shader.inputs["Color"].default_value = (0.095, 0.028, 0.010, 1.0)
        if "Roughness" in shader.inputs:
            shader.inputs["Roughness"].default_value = 0.42
        if "Radial Roughness" in shader.inputs:
            shader.inputs["Radial Roughness"].default_value = 0.48
        if "Random Roughness" in shader.inputs:
            shader.inputs["Random Roughness"].default_value = 0.16
        if "Random Color" in shader.inputs:
            shader.inputs["Random Color"].default_value = 0.08
    else:
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        if "Base Color" in shader.inputs:
            shader.inputs["Base Color"].default_value = (0.095, 0.028, 0.010, 1.0)
        if "Roughness" in shader.inputs:
            shader.inputs["Roughness"].default_value = 0.46

    shader.location = (-40, 0)
    links.new(shader.outputs[0], output.inputs["Surface"])
    return mat


def create_body(collection):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, location=(0, 0, 0))
    body = bpy.context.active_object
    body.name = BODY_NAME
    body.scale = ELLIPSOID_RADII
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    for poly in body.data.polygons:
        poly.use_smooth = True

    for old_collection in list(body.users_collection):
        old_collection.objects.unlink(body)
    collection.objects.link(body)

    mat = make_body_material()
    body.data.materials.clear()
    body.data.materials.append(mat)

    if not body.data.uv_layers:
        uv_layer = body.data.uv_layers.new(name="UVMap")
    else:
        uv_layer = body.data.uv_layers.active
    body.data.uv_layers.active = uv_layer

    rest = body.data.attributes.get("rest_position")
    if rest is None:
        rest = body.data.attributes.new("rest_position", 'FLOAT_VECTOR', 'POINT')
    flat = []
    for vertex in body.data.vertices:
        flat.extend(vertex.co)
    rest.data.foreach_set("vector", flat)

    return body, uv_layer.name


def uniform_sphere_sample(rng):
    u = rng.random()
    v = rng.random()
    z = 1.0 - 2.0 * u
    radial = math.sqrt(max(0.0, 1.0 - z * z))
    phi = 2.0 * math.pi * v
    x = radial * math.cos(phi)
    y = radial * math.sin(phi)
    theta = math.acos(max(-1.0, min(1.0, z)))
    return Vector((x, y, z)), v, theta / math.pi


def ellipsoid_normal(unit_point):
    x, y, z = unit_point
    rx, ry, rz = ELLIPSOID_RADII
    return Vector((x / rx, y / ry, z / rz)).normalized()


def tangent_basis(normal):
    helper = Vector((0.0, 0.0, 1.0))
    if abs(normal.dot(helper)) > 0.92:
        helper = Vector((0.0, 1.0, 0.0))
    tangent_a = normal.cross(helper).normalized()
    tangent_b = normal.cross(tangent_a).normalized()
    return tangent_a, tangent_b


def groom_direction(normal, unit_point, rng):
    # Body local X is treated as head-to-tail. Fur lays mostly toward -X,
    # with a downward component on the flanks and a little surface lift.
    downward = -0.28 * (1.0 - abs(unit_point.z))
    flow = Vector((-1.0, 0.0, downward)).normalized()
    tangent = flow - normal * flow.dot(normal)
    if tangent.length < 1e-6:
        tangent = Vector((-1.0, 0.0, 0.0))
    tangent.normalize()

    ta, tb = tangent_basis(normal)
    jitter = (ta * rng.uniform(-0.10, 0.10) + tb * rng.uniform(-0.10, 0.10))
    direction = normal * ROOT_LIFT + tangent * LAY_STRENGTH + jitter
    return direction.normalized(), tangent, ta, tb


def create_fur(collection, body, uv_map_name):
    rng = random.Random(SEED)
    curves = bpy.data.hair_curves.new(FUR_NAME)
    curves.add_curves([POINTS_PER_CURVE] * FUR_COUNT)
    curves.surface = body
    curves.surface_uv_map = uv_map_name
    curves.surface_collision_distance = 0.004

    obj = bpy.data.objects.new(FUR_NAME, curves)
    collection.objects.link(obj)

    positions = []
    radii = []
    root_uvs = []
    strand_lengths = []

    for strand_index in range(FUR_COUNT):
        unit_point, uv_u, uv_v = uniform_sphere_sample(rng)
        root = Vector((
            unit_point.x * ELLIPSOID_RADII.x,
            unit_point.y * ELLIPSOID_RADII.y,
            unit_point.z * ELLIPSOID_RADII.z,
        ))
        normal = ellipsoid_normal(unit_point)
        direction, tangent, tangent_a, tangent_b = groom_direction(normal, unit_point, rng)

        # Slightly shorter underneath and around the front cap, longer on the
        # back/top to make the coat more animal-like than uniformly spherical.
        region_scale = 0.78 + 0.20 * max(unit_point.z, 0.0) + 0.09 * max(-unit_point.x, 0.0)
        random_scale = 1.0 + rng.uniform(-LENGTH_VARIATION, LENGTH_VARIATION)
        length = BASE_LENGTH * region_scale * random_scale
        strand_lengths.append(length)

        sideways = tangent_a * rng.uniform(-FRIZZ, FRIZZ) + tangent_b * rng.uniform(-FRIZZ, FRIZZ)
        bend_strength = rng.uniform(0.06, 0.16) * length

        for point_index in range(POINTS_PER_CURVE):
            t = point_index / (POINTS_PER_CURVE - 1)
            smooth_t = t * t * (3.0 - 2.0 * t)
            root_clean = t * t
            arch = math.sin(math.pi * t)

            point = (
                root
                + direction * (length * t)
                + normal * (bend_strength * arch)
                + sideways * (length * root_clean)
                + tangent * (0.035 * length * smooth_t * smooth_t)
            )
            positions.extend(point)

            taper = (1.0 - t) ** 1.7
            radius = TIP_RADIUS + (ROOT_RADIUS - TIP_RADIUS) * taper
            radii.append(radius)

        root_uvs.extend((uv_u, uv_v))

    curves.attributes["position"].data.foreach_set("vector", positions)

    radius_attr = curves.attributes.get("radius")
    if radius_attr is None:
        radius_attr = curves.attributes.new("radius", 'FLOAT', 'POINT')
    radius_attr.data.foreach_set("value", radii)

    uv_attr = curves.attributes.get("surface_uv_coordinate")
    if uv_attr is None:
        uv_attr = curves.attributes.new("surface_uv_coordinate", 'FLOAT2', 'CURVE')
    uv_attr.data.foreach_set("vector", root_uvs)

    fur_mat = make_fur_material()
    curves.materials.append(fur_mat)

    # Useful custom metadata for an MCP agent or human inspecting the file.
    obj["mcp_seed"] = SEED
    obj["mcp_fur_count"] = FUR_COUNT
    obj["mcp_points_per_curve"] = POINTS_PER_CURVE
    obj["mcp_base_length"] = BASE_LENGTH
    obj["mcp_note"] = "Static direct-curves fur demo; use guide/interpolation workflow for animated hero grooms."

    return obj, strand_lengths


def main():
    remove_owned_data()
    collection = get_or_create_collection()
    body, uv_map_name = create_body(collection)
    fur, strand_lengths = create_fur(collection, body, uv_map_name)

    attrs = {a.name: (a.data_type, a.domain) for a in fur.data.attributes}
    print({
        "ok": True,
        "blender": bpy.app.version_string,
        "body": body.name,
        "body_dimensions": [round(v, 4) for v in body.dimensions],
        "fur": fur.name,
        "curve_count": len(fur.data.curves),
        "point_count": len(fur.data.points),
        "points_per_curve": POINTS_PER_CURVE,
        "length_min": round(min(strand_lengths), 5),
        "length_max": round(max(strand_lengths), 5),
        "length_mean": round(sum(strand_lengths) / len(strand_lengths), 5),
        "surface": fur.data.surface.name if fur.data.surface else None,
        "surface_uv_map": fur.data.surface_uv_map,
        "has_surface_uv_coordinate": "surface_uv_coordinate" in attrs,
        "has_radius": "radius" in attrs,
        "material": fur.data.materials[0].name if fur.data.materials else None,
    })


if __name__ == "__main__":
    main()
