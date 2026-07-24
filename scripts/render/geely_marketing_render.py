import math
import os
from mathutils import Vector

import bpy


STL_PATH = os.environ.get("GEELY_STL_PATH", "/tmp/Geely_atlas_pro.stl")
OUTPUT_DIR = os.environ.get("MARKETING_OUTPUT_DIR", "/tmp/stl-master-marketing-assets")

# Marketing-only transform. The STL itself keeps its original orientation in the product pipeline.
# corrected_orientation: keep Blender Z as visual up so Geely Atlas stands on wheels, not bumper.
MARKETING_Z_ROTATION_DEG = -18
MARKETING_SCALE = 1.12


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_mat(name, color, roughness=0.55, metallic=0.0, alpha=1.0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
        if emission:
            bsdf.inputs["Emission Color"].default_value = emission[0]
            bsdf.inputs["Emission Strength"].default_value = emission[1]
    mat.blend_method = "BLEND"
    mat.use_screen_refraction = True
    return mat


BODY = make_mat("premium frosted cyan", (0.52, 0.84, 0.94, 0.98), 0.34, 0.04, 0.98, ((0.12, 0.58, 0.74, 1.0), 0.06))
WIRE = make_mat("wire glow", (0.86, 0.98, 1.0, 0.46), 0.5, 0.0, 0.46, ((0.25, 0.85, 1.0, 1.0), 0.08))
TURQ = make_mat("turquoise accent", (0.12, 0.92, 1.0, 0.58), 0.26, 0.0, 0.58, ((0.0, 0.72, 1.0, 1.0), 0.9))
RED = make_mat("defect red", (1.0, 0.16, 0.12, 0.84), 0.38, 0.0, 0.84, ((1.0, 0.08, 0.06, 1.0), 0.9))
ORANGE = make_mat("artifact orange", (1.0, 0.52, 0.1, 0.84), 0.35, 0.0, 0.84, ((1.0, 0.42, 0.05, 1.0), 0.75))
GREEN = make_mat("ready green", (0.24, 1.0, 0.64, 0.84), 0.35, 0.0, 0.84, ((0.18, 1.0, 0.52, 1.0), 0.8))
DARK_GLASS = make_mat("dark glass", (0.018, 0.065, 0.11, 0.66), 0.64, 0.0, 0.66)
MAGNET = make_mat("magnet steel", (0.72, 0.8, 0.84, 1.0), 0.27, 0.36, 1.0)


def bounds(obj):
    world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_v = Vector((min(v.x for v in world), min(v.y for v in world), min(v.z for v in world)))
    max_v = Vector((max(v.x for v in world), max(v.y for v in world), max(v.z for v in world)))
    return min_v, max_v, max_v - min_v


def center_on_floor(obj):
    min_v, max_v, _ = bounds(obj)
    obj.location.x -= (min_v.x + max_v.x) / 2
    obj.location.y -= (min_v.y + max_v.y) / 2
    obj.location.z -= min_v.z


def import_model():
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=STL_PATH)
    else:
        bpy.ops.import_mesh.stl(filepath=STL_PATH)
    model = bpy.context.object
    model.name = "Geely Atlas Pro STL corrected_orientation"
    model.data.materials.append(BODY)

    model.rotation_euler = (0, 0, math.radians(MARKETING_Z_ROTATION_DEG))
    model.scale = (MARKETING_SCALE, MARKETING_SCALE, MARKETING_SCALE)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    center_on_floor(model)

    bpy.context.view_layer.objects.active = model
    model.select_set(True)
    decimate = model.modifiers.new("marketing preview decimation", "DECIMATE")
    decimate.ratio = 0.18
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    bpy.ops.object.shade_smooth()
    center_on_floor(model)
    return model


def add_wire_duplicate(model):
    dup = model.copy()
    dup.data = model.data.copy()
    dup.name = "Geely wireframe overlay"
    bpy.context.collection.objects.link(dup)
    dup.data.materials.clear()
    dup.data.materials.append(WIRE)
    mod = dup.modifiers.new("wire overlay", "WIREFRAME")
    mod.thickness = 0.0038
    mod.use_even_offset = True
    return dup


def look_at(obj, target):
    direction = Vector(target) - Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera(model):
    _, _, size = bounds(model)
    target_z = max(9, size.z * 0.42)
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, target_z))
    target = bpy.context.object
    cam_data = bpy.data.cameras.new("camera")
    cam = bpy.data.objects.new("camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (92, -154, 72)
    look_at(cam, (0, 0, target_z))
    cam_data.lens = 48
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target
    cam_data.dof.aperture_fstop = 8
    bpy.context.scene.camera = cam
    return cam


def setup_world():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 840
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0.28
    scene.view_settings.gamma = 1.0
    scene.world = bpy.data.worlds.new("dark studio world")
    scene.world.color = (0.006, 0.018, 0.028)

    bpy.ops.object.light_add(type="AREA", location=(-72, -86, 118))
    key = bpy.context.object
    key.name = "large cyan softbox"
    key.data.energy = 1120
    key.data.size = 92

    bpy.ops.object.light_add(type="AREA", location=(80, 62, 76))
    rim = bpy.context.object
    rim.name = "turquoise rim wash"
    rim.data.energy = 230
    rim.data.size = 58
    rim.data.color = (0.25, 0.95, 1.0)

    bpy.ops.object.light_add(type="POINT", location=(-46, 54, 42))
    fill = bpy.context.object
    fill.name = "soft dashboard fill"
    fill.data.energy = 130
    fill.data.color = (0.55, 0.78, 1.0)


def add_floor(model):
    _, _, size = bounds(model)
    plate_size = max(150, max(size.x, size.y) * 1.28)
    bpy.ops.mesh.primitive_plane_add(size=plate_size, location=(0, 0, -0.14))
    plane = bpy.context.object
    plane.name = "printer build plate"
    plane.data.materials.append(DARK_GLASS)
    return plane


def add_split_plane(model):
    _, _, size = bounds(model)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, size.z * 0.48))
    obj = bpy.context.object
    obj.name = "cut plane preview"
    obj.dimensions = (1.2, max(70, size.y * 0.88), max(32, size.z * 1.18))
    obj.data.materials.append(TURQ)
    return obj


def add_pin_pair(x, y, z):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=2.3, depth=16, location=(x, y, z), rotation=(0, math.radians(90), 0))
    pin = bpy.context.object
    pin.name = "connector pin"
    pin.data.materials.append(TURQ)


def add_magnet(x, y, z):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=3.8, depth=2.2, location=(x, y, z), rotation=(0, math.radians(90), 0))
    magnet = bpy.context.object
    magnet.name = "magnet pocket"
    magnet.data.materials.append(MAGNET)


def add_marker(x, y, z, radius, mat, name):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=radius, location=(x, y, z))
    marker = bpy.context.object
    marker.name = name
    marker.data.materials.append(mat)
    return marker


def add_brush_region():
    add_marker(-17, -10, 18, 7.6, ORANGE, "local smoothing brush area")
    bpy.ops.mesh.primitive_torus_add(major_radius=12, minor_radius=0.24, location=(-17, -10, 18), rotation=(math.radians(70), 0, math.radians(-18)))
    ring = bpy.context.object
    ring.name = "brush radius ring"
    ring.data.materials.append(TURQ)


def add_scene_overlays(kind, model):
    if kind in {"hero", "split", "connectors", "before_after"}:
        add_split_plane(model)
    if kind == "connectors":
        for coords in [(-4, -18, 16), (-4, 20, 16)]:
            add_pin_pair(*coords)
        for coords in [(5, -18, 16), (5, 20, 16)]:
            add_magnet(*coords)
    if kind in {"before", "before_after", "repair"}:
        add_marker(-24, -22, 18, 4.1, RED, "defect cluster")
        add_marker(24, 8, 25, 3.6, ORANGE, "ai artifact")
        add_marker(2, -31, 11, 3.2, RED, "broken island")
    if kind in {"after", "print_check"}:
        add_marker(-23, -19, 18, 2.8, GREEN, "fixed zone")
        add_marker(21, 8, 24, 2.8, GREEN, "clean zone")
    if kind == "local":
        add_brush_region()


def add_mockup_panel(kind):
    if kind != "hero":
        return
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-44, -28, 36))
    panel = bpy.context.object
    panel.name = "operations panel"
    panel.dimensions = (1.1, 30, 24)
    panel.data.materials.append(DARK_GLASS)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(38, -31, 10))
    status = bpy.context.object
    status.name = "download status panel"
    status.dimensions = (1.1, 34, 13)
    status.data.materials.append(DARK_GLASS)


def render_asset(name, kind):
    clear_scene()
    setup_world()
    model = import_model()
    add_wire_duplicate(model)
    add_floor(model)
    add_scene_overlays(kind, model)
    add_mockup_panel(kind)
    setup_camera(model)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, name)
    bpy.ops.render.render(write_still=True)


def main():
    assets = {
        "geely-hero-render.png": "hero",
        "geely-before-render.png": "before",
        "geely-after-render.png": "after",
        "geely-split-render.png": "split",
        "geely-connectors-render.png": "connectors",
        "geely-local-smoothing-render.png": "local",
        "geely-print-check-render.png": "print_check",
    }
    for filename, kind in assets.items():
        render_asset(filename, kind)


if __name__ == "__main__":
    main()
