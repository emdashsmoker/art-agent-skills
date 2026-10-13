"""Scene meshes -> per-pixel geometry buffers (the 'form layer' handed to every medium)."""
import numpy as np

from .raster import rasterize, interpolate

SHADOW_MAP_SIZE = 2048
SHADOW_BIAS = 0.012          # metres; prevents self-shadow acne on curved skin
BACKGROUND_ID = -1
SHADOW_CASCADES, SHADOW_CASCADE_RATIO = 4, 3.5
SHADOW_NEAR_FACTOR = 2.5     # near cascade reaches this many times the nearest surface distance


def _merge(meshes):
    verts, faces, normals, uvs = [], [], [], []
    face_mat, face_part, attr_names = [], [], set()
    materials, parts = [], []
    offset = 0
    for mesh in meshes:
        attr_names.update(mesh.vertex_attr)
    attrs = {name: [] for name in attr_names}
    widths = {}
    for mesh in meshes:
        for name, value in mesh.vertex_attr.items():
            widths[name] = 1 if np.ndim(value) == 1 else np.shape(value)[1]
    for mesh in meshes:
        if mesh.material not in materials:
            materials.append(mesh.material)
        if mesh.part not in parts:
            parts.append(mesh.part)
        count = len(mesh.vertices)
        verts.append(mesh.vertices)
        normals.append(mesh.vertex_normals())
        faces.append(mesh.faces + offset)
        face_mat.append(np.full(len(mesh.faces), materials.index(mesh.material)))
        face_part.append(np.full(len(mesh.faces), parts.index(mesh.part)))
        uvs.append(mesh.face_uv if mesh.face_uv is not None else np.zeros((len(mesh.faces), 3, 2)))
        for name in attr_names:
            value = mesh.vertex_attr.get(name)
            width = widths[name]
            value = np.zeros((count, width), np.float32) if value is None else np.asarray(value, np.float32).reshape(count, width)
            attrs[name].append(value)
        offset += count
    return dict(vertices=np.concatenate(verts), faces=np.concatenate(faces),
                normals=np.concatenate(normals), face_uv=np.concatenate(uvs),
                face_material=np.concatenate(face_mat), face_part=np.concatenate(face_part),
                materials=materials, parts=parts,
                attrs={k: np.concatenate(v) for k, v in attrs.items()})


NON_CASTING_PARTS = ("wall",)


def _shadow_cascade(scene, axis_u, axis_v, to_light, points):
    """Shadow test for `points` using a map fitted tightly around them."""
    v = scene["vertices"]
    pu, pv = points @ axis_u, points @ axis_v
    u0, u1, v0, v1 = pu.min(), pu.max(), pv.min(), pv.max()
    span = max(u1 - u0, v1 - v0) * 1.04 + 1e-6
    scale = SHADOW_MAP_SIZE / span
    u, w = v @ axis_u, v @ axis_v
    dist = -(v @ to_light)                      # grows away from the light
    shift = dist.min() - 1.0
    sx, sy = (u - u0) * scale + 0.02 * SHADOW_MAP_SIZE, (w - v0) * scale + 0.02 * SHADOW_MAP_SIZE
    _, depth_map, _ = rasterize(np.stack([sx, sy], 1), dist - shift, scene.get("shadow_faces", scene["faces"]),
                                SHADOW_MAP_SIZE, SHADOW_MAP_SIZE, perspective=False)
    px = np.clip((pu - u0) * scale + 0.02 * SHADOW_MAP_SIZE, 0, SHADOW_MAP_SIZE - 1).astype(int)
    py = np.clip((pv - v0) * scale + 0.02 * SHADOW_MAP_SIZE, 0, SHADOW_MAP_SIZE - 1).astype(int)
    bias = max(SHADOW_BIAS, 2.5 / scale)        # coarser maps need a larger bias to avoid acne
    return (-(points @ to_light) - shift) <= depth_map[py, px] + bias


def _shadow(scene, world_pos, covered, depth, light_dir):
    """1 where the key light reaches the pixel, 0 where another surface blocks it.

    Several cascades: a tight map around the nearest surfaces (crisp contact shadows) and looser ones
    farther away, so a huge ground plane does not starve the subject of resolution.
    """
    to_light = -np.asarray(light_dir, float)
    to_light /= np.linalg.norm(to_light)
    helper = np.array([0.0, 0.0, 1.0]) if abs(to_light[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    axis_u = np.cross(helper, to_light); axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(to_light, axis_u)
    out = np.ones(covered.shape, np.float32)
    if not covered.any():
        return out
    p = world_pos[covered].astype(np.float64)
    d = depth[covered]
    near_limit = np.percentile(d, 5) * SHADOW_NEAR_FACTOR
    # cascades grow geometrically with distance, so a subject a few metres away in a street scene
    # still gets a fine map instead of sharing one with buildings a hundred metres off
    limits = [near_limit * SHADOW_CASCADE_RATIO ** k for k in range(SHADOW_CASCADES - 1)] + [np.inf]
    lit = np.ones(len(p), bool)
    lower = -np.inf
    for upper in limits:
        select = (d > lower) & (d <= upper)
        if select.any():
            lit[select] = _shadow_cascade(scene, axis_u, axis_v, to_light, p[select])
        lower = upper
    out[covered] = lit
    return out


def render_gbuffer(meshes, camera, light_dir=(-0.5, 0.6, -0.6), supersample=2):
    """Rasterize the scene once; media layers only read these buffers."""
    scene = _merge(meshes)
    cam = camera.scaled(supersample) if supersample != 1 else camera
    screen_xy, depth = cam.project(scene["vertices"])
    face_buf, depth_buf, bary = rasterize(screen_xy, depth, scene["faces"], cam.height, cam.width)
    covered = face_buf >= 0
    faces = scene["faces"]
    normal = interpolate(face_buf, bary, faces, scene["normals"])
    length = np.linalg.norm(normal, axis=-1, keepdims=True)
    normal = normal / np.maximum(length, 1e-9)
    position = interpolate(face_buf, bary, faces, scene["vertices"])
    material = np.full(face_buf.shape, BACKGROUND_ID, np.int32)
    part = np.full(face_buf.shape, BACKGROUND_ID, np.int32)
    material[covered] = scene["face_material"][face_buf[covered]]
    part[covered] = scene["face_part"][face_buf[covered]]
    # per-corner UV needs its own interpolation because UV seams split vertices
    uv = np.zeros(face_buf.shape + (2,), np.float32)
    corner_uv = scene["face_uv"][face_buf[covered]]
    b0, b1 = bary[covered][:, 0:1], bary[covered][:, 1:2]
    uv[covered] = corner_uv[:, 0] * b0 + corner_uv[:, 1] * b1 + corner_uv[:, 2] * (1 - b0 - b1)
    attrs = {name: interpolate(face_buf, bary, faces, values) for name, values in scene["attrs"].items()}
    # flip normals that face away from the viewer (thin shells such as hair cards, cloth)
    view = cam.view_dirs()
    facing = np.sum(normal * view, axis=-1, keepdims=True)
    normal = np.where(facing > 0, -normal, normal)
    # room walls stand around the set like a studio's flats: they receive the key light but do not block it
    walls = [index for index, name in enumerate(scene["parts"]) if name in NON_CASTING_PARTS]
    scene["shadow_faces"] = scene["faces"][~np.isin(scene["face_part"], walls)] if walls else scene["faces"]
    shadow = _shadow(scene, position, covered, depth_buf, light_dir)
    depth_buf = np.where(covered, depth_buf, np.nan)
    return dict(mask=covered, depth=depth_buf, normal=normal, position=position,
                material=material, part=part, uv=uv, attrs=attrs, shadow=shadow,
                view=view, materials=scene["materials"], parts=scene["parts"],
                camera=cam, supersample=supersample, light_dir=np.asarray(light_dir, float))
