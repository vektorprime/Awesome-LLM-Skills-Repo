# Validation, Troubleshooting, Export, and Operating Practice

# 24. Geometry and Scene Validation

Validation should be both **structural** and **visual**.

## 24.1 Base mesh validation

```python
mesh = obj.data
was_fixed = mesh.validate(verbose=False, clean_customdata=False)
mesh.update()
print({"mesh_validate_changed": was_fixed})
```

## 24.2 Non-manifold report with BMesh

```python
import bmesh

mesh = obj.data
bm = bmesh.new()
try:
    bm.from_mesh(mesh)
    non_manifold = [
        e.index for e in bm.edges
        if not e.is_manifold
    ]
    print({
        "edges": len(bm.edges),
        "non_manifold_edge_count": len(non_manifold),
        "sample": non_manifold[:20],
    })
finally:
    bm.free()
```

Interpret non-manifold edges based on asset intent. An open plane is expected to be non-manifold; a watertight printable solid is not.

## 24.3 Check degenerate geometry

Watch for:

- zero-area faces;
- duplicate vertices;
- zero-length edges;
- inverted normals;
- self-intersections when they matter;
- hidden internal faces.

## 24.4 Transform checks

For finished static assets, commonly prefer:

- scale `(1, 1, 1)`;
- intentional rotation/origin;
- dimensions in expected range.

## 24.5 Visual gate

Before completion, inspect a screenshot or render and ask:

- Is the silhouette correct?
- Are bevels visible but not inflated?
- Are details attached to surfaces?
- Is the model centered/framed?
- Are materials distinguishable?
- Is lighting helping the shape?
- Does the camera crop anything unintentionally?
- Are any objects obviously intersecting?
- Are proportions consistent with the prompt?

---

# 25. Version-Aware Introspection Patterns

Blender APIs evolve. When uncertain, introspect instead of guessing.

## 25.1 Blender version

```python
import bpy
print(bpy.app.version)
print(bpy.app.version_string)
```

## 25.2 RNA property existence

```python
if hasattr(obj.data, "some_property"):
    ...
```

## 25.3 Enum values

```python
prop = scene.render.bl_rna.properties.get("engine")
if prop:
    print([(i.identifier, i.name) for i in prop.enum_items])
```

## 25.4 Node inputs/outputs

```python
print("INPUTS")
for s in node.inputs:
    print(s.name, s.identifier, s.type)

print("OUTPUTS")
for s in node.outputs:
    print(s.name, s.identifier, s.type)
```

## 25.5 Node group interface

```python
for item in node_group.interface.items_tree:
    print(
        getattr(item, "item_type", None),
        getattr(item, "name", None),
        getattr(item, "identifier", None),
        getattr(item, "in_out", None),
    )
```

This is especially important when adapting scripts from Blender 3.x or early 4.x.

---

# 26. Failure Recovery Playbook

## 26.1 MCP timeout

Symptoms:

- execute call hangs or times out;
- Blender becomes temporarily unresponsive.

Response:

1. do not immediately resend the same huge operation;
2. inspect whether Blender completed part of it;
3. split the operation into smaller chunks;
4. reduce geometry complexity;
5. avoid large per-object loops if Geometry Nodes/instances can replace them.

## 26.2 Connection lost

Check:

- Blender is still running;
- MCP addon server is started;
- only the intended MCP server instance is connected;
- addon and MCP server versions are compatible if status tooling exists.

Do not reset Blender preferences as a troubleshooting step.

## 26.3 Operator context error

If an operator says its poll failed or context is incorrect:

1. switch to Object Mode if appropriate;
2. select target;
3. set target active;
4. use a context override if necessary;
5. replace the operator with direct data API or BMesh if possible.

## 26.4 Boolean looks broken

Check:

- object scale;
- coplanar cutter surfaces;
- cutter overlap;
- normals;
- boolean solver;
- preceding modifier order.

## 26.5 Black shading / weird normals

Check:

- face orientation;
- smooth/flat settings;
- duplicate faces;
- zero-area geometry;
- extreme nonuniform scale;
- normal maps using correct color space and Normal Map node.

## 26.6 Geometry Nodes input fails

Do not guess `Input_2` style keys. Inspect the node-group interface socket identifiers.

## 26.7 Imported model is microscopic or enormous

Compute dimensions, then normalize scale deliberately. Do not eyeball blindly.

---


# 32. Export Discipline

When export is requested, clarify or infer the target pipeline from context.

Common targets:

- glTF/GLB;
- FBX;
- OBJ;
- USD;
- Alembic;
- STL for printing.

## 32.1 Before export

Check:

- scale;
- transform orientation;
- origin/pivot;
- modifier policy (applied vs preserved);
- triangulation requirements;
- material compatibility;
- texture packing/path handling;
- animation frame range;
- armature naming;
- non-manifold geometry for 3D printing.

## 32.2 Do not destructively apply modifiers merely because export exists

If the exporter evaluates modifiers automatically, keep an editable source unless the user asks for a baked version. A good pattern is:

- preserve source collection;
- create an export copy;
- apply/export from the copy.

---

# 33. Completion Criteria

A Blender task is not complete merely because code returned “success.”

For a substantial asset/scene, completion normally requires:

- requested objects exist;
- meaningful names/collections exist;
- dimensions are plausible;
- transforms are intentional;
- materials are assigned;
- key modifiers/nodes are correct;
- no obvious accidental geometry defects;
- viewport screenshot or render has been inspected;
- composition is acceptable if camera work was requested;
- user content outside the requested scope remains intact;
- export/render is produced if explicitly requested.

## 33.1 Final report to user

Keep the user-facing final report concise but concrete.

Mention:

- what was created/changed;
- important object or collection names;
- relevant dimensions or render settings;
- whether visual validation was performed;
- any remaining caveats.

Do not bury the user in every Python operation unless they ask for a technical log.

---

# 34. Agent Decision Rules — Memorize These

1. **Inspect before editing.**
2. **Never assume the scene is empty.**
3. **Never hallucinate MCP tools.**
4. **Prefer data API/BMesh over fragile UI-context operators.**
5. **Use operators deliberately when they are the best tool.**
6. **Break large work into stages.**
7. **Print compact diagnostics after code execution.**
8. **Use a dedicated collection/prefix for generated work.**
9. **Do not factory-reset Blender during a live MCP session.**
10. **Do not globally delete or purge user data without authorization.**
11. **Apply/normalize scale before precision bevel/boolean work when appropriate.**
12. **Use bevels to create realistic highlight rolloff.**
13. **Build primary → secondary → tertiary forms.**
14. **Use instances for repeated details.**
15. **Use Geometry Nodes for large procedural systems.**
16. **Use modern Blender 4.x node-group interface APIs.**
17. **Introspect RNA and node sockets when uncertain.**
18. **Validate evaluated geometry, not only base mesh, when modifiers/nodes matter.**
19. **Use real-world scale.**
20. **Use world-space math for spatial relationships.**
21. **Check imported asset scale and licensing.**
22. **Treat AI-generated meshes as untrusted topology until inspected.**
23. **Use physically coherent materials.**
24. **Use Non-Color for roughness/metallic/normal/height maps.**
25. **Use lighting to reveal shape, not hide modeling defects.**
26. **Frame actual object bounds, not blindly the world origin.**
27. **Use low-cost previews before expensive renders/simulations.**
28. **Capture screenshots during iteration.**
29. **Never claim visual quality without visual evidence.**
30. **Leave the scene organized enough that a human can continue working.**

---

# 35. Short Operational Templates

## Template A — Create a new advanced object

1. verify MCP status;
2. inspect scene;
3. create dedicated collection;
4. build primary mesh;
5. report dimensions;
6. screenshot;
7. add secondary detail;
8. screenshot;
9. add tertiary detail/materials;
10. validate geometry;
11. camera/light if requested;
12. final visual inspection.

## Template B — Modify an existing object

1. inspect scene;
2. `get_object_info` on exact target;
3. screenshot;
4. preserve a non-destructive path where feasible;
5. make one modification;
6. inspect evaluated result;
7. screenshot;
8. continue only if correct.

## Template C — Build a scene from a reference

1. analyze reference proportions and camera perspective;
2. establish scene scale;
3. block large shapes;
4. match camera early;
5. compare screenshot;
6. refine silhouettes;
7. add materials;
8. match lighting;
9. add detail only after composition aligns.

## Template D — Procedural system

1. create minimal source geometry;
2. create Geometry Nodes group with modern interface sockets;
3. build one procedural feature;
4. inspect node socket names if uncertain;
5. validate output;
6. expose parameters;
7. scale to final density only after low-cost test succeeds.

---

# 36. Blender 4.5 Notes Relevant to This Skill

Use Blender 4.5 LTS documentation as the authority when old tutorials conflict with current behavior.

Important 4.5-era considerations include:

- Geometry Nodes continues to use the modern node-tree interface system introduced in Blender 4.x.
- Node interface sockets expose identifiers useful for modifier mapping.
- Blender 4.5 adds improved GeometrySet access for evaluated procedural geometry.
- Blender 4.5 includes newer normal-management capabilities, including Geometry Nodes support for setting mesh normals.
- Several APIs and shader/node behaviors differ from Blender 3.x-era tutorials.

Therefore, when a property, enum, socket, node type, or render-engine identifier is uncertain, **introspection is mandatory** before repeated guessing.

---

# 37. MCP-Specific Best Practices

## 37.1 Use structured inspection tools when available

`get_scene_info` and `get_object_info` are preferable to writing custom code just to retrieve basic state.

## 37.2 Use screenshot tooling frequently

Screenshots are one of the most important capabilities in Blender MCP because they close the visual feedback loop.

Use them:

- after blockout;
- after major geometry detail;
- after materials;
- after camera/lighting;
- before claiming completion.

## 37.3 Use arbitrary code as a precision instrument

`execute_blender_code` is powerful. Use it for:

- parametric geometry;
- detailed modifier setups;
- material node graphs;
- Geometry Nodes;
- transforms/calculations;
- validation;
- procedural animation.

Do not use arbitrary Python for unrelated host operations.

## 37.4 Respect MCP timeouts

Complex operations should be split into smaller chunks. If one stage may generate hundreds of thousands of elements, prototype at lower resolution first.

## 37.5 Optional remote integrations

Use external assets only when they improve the user's goal. A scene should not become dependent on random imported assets when procedural/native construction would be cleaner.

---

# 38. Final Standard

Act like a senior artist-engineer who happens to have an MCP interface instead of a mouse.

The best result is not the longest script. The best result is a **clear, editable, visually strong, technically correct Blender scene** produced through a controlled feedback loop.

When uncertain:

- inspect;
- query Blender itself;
- use Blender 4.5's RNA/node interfaces to discover the truth;
- make the smallest reversible change;
- validate it;
- inspect visually;
- then continue.
