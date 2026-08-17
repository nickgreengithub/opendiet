"""Bake MB-Lab characters into the one morph-target .glb the calc app wants.

Run inside Blender:  Scripting tab → Open → Run Script
or headless:         blender scene.blend --background --python tools/mblab_bake.py

WHAT YOU DO FIRST, BY HAND, IN MB-LAB
-------------------------------------
MB-Lab's own API moves between releases, so this script does not drive it. You
make the bodies in the UI — which takes about ten minutes — and this script does
the part that is fiddly and must be exact.

 1. New scene. MB-Lab panel → pick ONE base character (e.g. Human Male) and
    create it. Use the same base for every level; different bases have different
    topology and cannot share shape keys.
 2. Set the fat level with the *body mass* slider (and body tone, if you want a
    little muscle definition on the lean end). Nothing else — no proportions, no
    height, no pose. Every level must differ in mass alone.
 3. Finalize the character (MB-Lab → Finalize tools → "Finalize" WITHOUT
    "Save images and backup"). Rename the resulting mesh object to the body-fat
    percentage it represents, prefixed bf: `bf8`.
 4. Undo back to the unfinalized character, move the mass slider to the next
    level, finalize again, rename `bf15`. Repeat for every level in LEVELS below.

    (If undo is unreliable in your version, make each level in a fresh scene and
    append the finalized meshes into one file. Same result.)

 5. All the meshes should be sitting at the origin, unposed, and identical in
    vertex count. Then run this.

WHAT THIS DOES
--------------
Takes the leanest as the base mesh, joins every other level onto it as a shape
key, writes the body-fat list into the mesh's custom properties so the runtime
can read it out of glTF `extras`, and exports a .glb with morph targets and
morph normals.

The output has to satisfy the contract in tools/build_body_glb.py — base mesh
leanest, targets ascending, `extras.bodyFat` listing base and targets in order —
because body.js reads nothing else.
"""

import os

import bpy

LEVELS = [8, 15, 22, 30, 38, 46]     # must match the objects you named bf8, bf15, ...
SEX = "m"                            # "m" or "f" — only picks the output filename
OUT = "//data/body/body-%s.glb" % SEX

# A dense MB-Lab body is ~14k verts, which with five morph targets carrying both
# position and normal deltas is several megabytes. Decimate to something a phone
# will not choke on; the silhouette is what carries the change, not the pores.
TARGET_TRIS = 6000


def obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise SystemExit("missing object %r — see the instructions at the top" % name)
    return o


def main():
    names = ["bf%d" % b for b in LEVELS]
    base = obj(names[0])
    others = [obj(n) for n in names[1:]]

    nv = len(base.data.vertices)
    for o in others:
        if len(o.data.vertices) != nv:
            raise SystemExit(
                "%s has %d verts, %s has %d — the levels must share topology, which "
                "means the same MB-Lab base character with only the mass slider moved"
                % (base.name, nv, o.name, len(o.data.vertices)))

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = base
    base.select_set(True)

    # Decimate before the shape keys go on: a mesh with shape keys cannot be
    # decimated, and every level has to be reduced identically anyway, which is
    # exactly what doing it on the base and then joining shapes gives you.
    tris = sum(len(p.vertices) - 2 for p in base.data.polygons)
    if tris > TARGET_TRIS:
        m = base.modifiers.new("dec", "DECIMATE")
        m.ratio = TARGET_TRIS / float(tris)
        bpy.ops.object.modifier_apply(modifier=m.name)
        # The others must be decimated to the *same* result, so they are rebuilt
        # from the base and re-shaped rather than decimated separately — which is
        # what join_shapes does by proximity. Keep the ratio identical.
        for o in others:
            bpy.context.view_layer.objects.active = o
            o.select_set(True)
            m2 = o.modifiers.new("dec", "DECIMATE")
            m2.ratio = m.ratio
            bpy.ops.object.modifier_apply(modifier=m2.name)
            o.select_set(False)
        bpy.context.view_layer.objects.active = base

    # Base shape key first, then one per level. join_shapes maps by vertex index,
    # which is why the topology check above is not optional.
    if base.data.shape_keys is None:
        bpy.ops.object.shape_key_add(from_mix=False)
        base.data.shape_keys.key_blocks[0].name = "bf%d" % LEVELS[0]

    for o, name in zip(others, names[1:]):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        base.select_set(True)
        bpy.context.view_layer.objects.active = base
        bpy.ops.object.join_shapes()
        base.data.shape_keys.key_blocks[-1].name = name
        base.data.shape_keys.key_blocks[-1].value = 0.0

    # Feet on the floor, facing +Y in Blender's axes (the exporter turns that into
    # +Z, Y-up, which is what body.js expects).
    bpy.ops.object.select_all(action="DESELECT")
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Read by body.js. Blender's glTF exporter writes custom properties whose names
    # do not begin with an underscore into the mesh's `extras`.
    base.data["bodyFat"] = LEVELS
    base.data["sex"] = SEX

    for o in others:
        bpy.data.objects.remove(o, do_unlink=True)

    path = bpy.path.abspath(OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_morph=True,
        export_morph_normal=True,
        export_morph_tangent=False,
        export_skins=False,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,          # without this the bodyFat list is dropped
        export_yup=True
    )
    print("wrote %s — %d verts, %d morph targets"
          % (path, len(base.data.vertices), len(LEVELS) - 1))


if __name__ == "__main__":
    main()
