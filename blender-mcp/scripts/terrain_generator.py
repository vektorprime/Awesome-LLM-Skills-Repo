import bpy
import math

COLL_NAME = "MCP_Terrain_Example"
PREFIX = "MCP_Terrain_"
NAME = PREFIX + "Landscape"

for obj in list(bpy.data.objects):
    if obj.name.startswith(PREFIX):
        bpy.data.objects.remove(obj, do_unlink=True)

coll = bpy.data.collections.get(COLL_NAME)
if coll is None:
    coll = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(coll)


def hash2(ix, iy, seed=0):
    # Deterministic integer hash -> [0, 1]. No external noise dependency.
    n = ix * 374761393 + iy * 668265263 + seed * 1442695041
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0xFFFFFFFF) / 0xFFFFFFFF


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def value_noise(x, y, seed=0):
    x0 = math.floor(x)
    y0 = math.floor(y)
    tx = smoothstep(x - x0)
    ty = smoothstep(y - y0)

    a = hash2(x0, y0, seed)
    b = hash2(x0 + 1, y0, seed)
    c = hash2(x0, y0 + 1, seed)
    d = hash2(x0 + 1, y0 + 1, seed)

    ab = a + (b - a) * tx
    cd = c + (d - c) * tx
    return ab + (cd - ab) * ty


def fbm(x, y, octaves=6, lacunarity=2.03, gain=0.50, seed=0):
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for octave in range(octaves):
        total += amp * value_noise(x * freq, y * freq, seed + octave * 97)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / max(norm, 1e-8)


def ridged(x, y, octaves=5, seed=40):
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for octave in range(octaves):
        n = value_noise(x * freq, y * freq, seed + octave * 131)
        r = 1.0 - abs(2.0 * n - 1.0)
        r = r * r
        total += r * amp
        norm += amp
        amp *= 0.52
        freq *= 2.08
    return total / max(norm, 1e-8)


size = 28.0
resolution = 161
half = size * 0.5
verts = []
faces = []
heights = []

for iy in range(resolution):
    y = -half + size * iy / (resolution - 1)
    for ix in range(resolution):
        x = -half + size * ix / (resolution - 1)
        nx = x / size
        ny = y / size

        broad = fbm(nx * 5.0 + 11.2, ny * 5.0 - 3.8, octaves=6, seed=8)
        ridge = ridged(nx * 4.1 - 8.0, ny * 4.1 + 4.0, octaves=5, seed=21)
        micro = fbm(nx * 17.0, ny * 17.0, octaves=3, gain=0.42, seed=73)

        # Mountainous north/east area with a broad valley cut through the middle.
        mountain_mask = smoothstep(max(0.0, min(1.0, 0.48 + 0.85 * ny + 0.28 * nx)))
        terrain = (broad - 0.47) * 4.2
        terrain += mountain_mask * (ridge ** 2.1) * 7.0
        terrain += (micro - 0.5) * 0.65

        # Meandering river valley cut.
        river_center = 1.25 * math.sin(x * 0.18) + 0.40 * math.sin(x * 0.51 + 1.1)
        river_dist = abs(y - river_center)
        river_cut = math.exp(-((river_dist / 1.15) ** 2))
        terrain -= 2.6 * river_cut

        # Flatten extreme lowland slightly so a later river plane can sit cleanly.
        if river_dist < 0.42:
            terrain = terrain * 0.45 - 0.65

        verts.append((x, y, terrain))
        heights.append(terrain)

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

# Height-based helper groups make later biome scattering easier.
lowlands = obj.vertex_groups.new(name="MCP_Lowlands")
highlands = obj.vertex_groups.new(name="MCP_Highlands")
min_h = min(heights)
max_h = max(heights)
span = max(max_h - min_h, 1e-8)
for i, h in enumerate(heights):
    nh = (h - min_h) / span
    lowlands.add([i], max(0.0, 1.0 - nh * 2.1), 'REPLACE')
    highlands.add([i], max(0.0, (nh - 0.45) / 0.55), 'REPLACE')

mat = bpy.data.materials.get("MCP_Terrain_EarthMat") or bpy.data.materials.new("MCP_Terrain_EarthMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    if "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = (0.16, 0.105, 0.055, 1.0)
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.88
mesh.materials.append(mat)

print({
    "ok": True,
    "object": obj.name,
    "resolution": resolution,
    "verts": len(mesh.vertices),
    "faces": len(mesh.polygons),
    "height_range": [round(min_h, 3), round(max_h, 3)],
    "dimensions": [round(v, 3) for v in obj.dimensions],
})
