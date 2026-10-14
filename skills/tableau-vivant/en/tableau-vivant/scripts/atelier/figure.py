"""Parametric human figure: body shape, face shape, expression, pose.

Why a parametric mesh: hands, feet and faces come out anatomically complete by
construction (five fingers are topology, not a statistical guess). The body model
is Anny (Apache-2.0) on MakeHuman assets (CC0).

Axes: X = figure's left(+)/right(-), Y = back(+)/front(-), Z = up. Units: metres.
"""
import functools
import warnings
import numpy as np

from .mesh import Mesh, euler_matrix, subdivide

# Anny's own calibration of its age axis against body measurements (anny 0.6.1, data files girls.pth and boys.pth,
# "morphological_age_mapping"; piecewise linear): age parameter -> morphological age in years.
AGE_ANCHORS = (0.0, 0.05, 0.215, 0.415, 0.67, 0.77, 0.83, 1.0)
AGE_YEARS = (0.0, 1.0, 4.0, 11.0, 16.0, 18.0, 64.0, 110.0)
ADULT_YEARS = 18.0


def age_for_years(years):
    """Anny age parameter whose body is calibrated to `years` (inverse of the model's own mapping)."""
    return float(np.interp(years, AGE_YEARS, AGE_ANCHORS))


def years_for_age(age):
    """Morphological age in years of an Anny age parameter."""
    return float(np.interp(age, AGE_ANCHORS, AGE_YEARS))


# The model's own 18-year mark. Any age can be drawn; a body under it is only drawn clothed (Scene.add_figure).
ADULT_AGE_MIN = age_for_years(ADULT_YEARS)            # 0.77
NEUTRAL_AXIS = 0.5                                     # a phenotype axis at the model's middle
BUST_SHAPING = ("breast-", "measure-bust-", "measure-underbust-")   # local changes that shape the bust
YOUNG_ADULT_AGE = age_for_years(22.6)                 # 0.776, the default
DEFAULT_PHENOTYPE = dict(gender=1.0, age=YOUNG_ADULT_AGE, muscle=0.5, weight=0.45, height=0.55,
                         proportions=0.15, cupsize=0.5, firmness=0.6,
                         african=0.33, asian=0.34, caucasian=0.33)
# The template is a coordinate frame, never a rendered body: per-vertex positions of one fixed rest mesh that face
# paint, garment cuts, landmarks and hair are written in. It keeps the phenotype all those numbers were measured on.
TEMPLATE_PHENOTYPE = dict(DEFAULT_PHENOTYPE, age=0.67)

# Named points on the body in template space (default adult, metres, pelvis origin). Used as reach targets.
LANDMARKS = {
    "head_top": (0.0, -0.05, 1.01), "forehead": (0.0, -0.148, 0.95), "temple.L": (0.07, -0.10, 0.92), "temple.R": (-0.07, -0.10, 0.92),
    "cheek.L": (0.05, -0.13, 0.85), "cheek.R": (-0.05, -0.13, 0.85), "mouth": (0.0, -0.163, 0.823), "chin": (0.0, -0.15, 0.795),
    "ear.L": (0.085, -0.045, 0.87), "ear.R": (-0.085, -0.045, 0.87), "nape": (0.0, 0.04, 0.77), "throat": (0.0, -0.09, 0.73),
    "shoulder.L": (0.145, -0.03, 0.71), "shoulder.R": (-0.145, -0.03, 0.71), "chest": (0.0, -0.14, 0.58),
    "shoulder_top.L": (0.105, 0.005, 0.735), "shoulder_top.R": (-0.105, 0.005, 0.735),      # where a resting hand lies
    "heart": (0.06, -0.15, 0.55), "breast.L": (0.085, -0.17, 0.52), "breast.R": (-0.085, -0.17, 0.52),
    "ribs.L": (0.09, -0.14, 0.44), "ribs.R": (-0.09, -0.14, 0.44), "belly": (0.0, -0.14, 0.33), "waist.L": (0.13, -0.04, 0.36), "waist.R": (-0.13, -0.04, 0.36),
    "pocket.L": (0.155, -0.085, 0.115), "pocket.R": (-0.155, -0.085, 0.115), "hip.L": (0.18, -0.04, 0.20), "hip.R": (-0.18, -0.04, 0.20), "pelvis": (0.0, -0.12, 0.11), "small_of_back": (0.0, 0.08, 0.33),
    "back_upper.L": (0.08, 0.063, 0.56), "back_upper.R": (-0.08, 0.063, 0.56), "spine_upper": (0.0, 0.07, 0.55),
    "spine_lower": (0.0, 0.035, 0.36),
    "back_lower.L": (0.07, 0.024, 0.38), "back_lower.R": (-0.07, 0.024, 0.38),
    "thigh.L": (0.12, -0.12, -0.05), "thigh.R": (-0.12, -0.12, -0.05), "knee.L": (0.147, -0.10, -0.28), "knee.R": (-0.147, -0.10, -0.28),
}

# Vertex index ranges of the MakeHuman base mesh (hm08).
BODY_RANGE = (0, 13380)


@functools.lru_cache(maxsize=1)
def _model():
    import anny
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return anny.Anny(rig="makehuman", topology="anny-full",
                         local_changes="default", facial_actions="all", phenotypes="all",
                         pose_parameterization="local-ref")


@functools.lru_cache(maxsize=1)
def _base_obj_groups():
    """Faces of helper geometry (tights, skirt, hair cap) that the body model drops."""
    import anny, os
    path = os.path.join(anny.__path__[0], "data", "mpfb2", "3dobjs", "base.obj")
    groups, current = {}, None
    with open(path) as handle:
        for line in handle:
            if line.startswith("g "):
                current = line.split()[1]
            elif line.startswith("f ") and current and current.startswith("helper-"):
                idx = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
                tris = [idx[:3]] if len(idx) == 3 else [[idx[0], idx[1], idx[2]], [idx[0], idx[2], idx[3]]]
                groups.setdefault(current, []).extend(tris)
    return {k: np.asarray(v, np.int64) for k, v in groups.items()}


@functools.lru_cache(maxsize=1)
def _template_vertices():
    """Rest mesh of the template phenotype. Used as a fixed 3D texture space: face paint defined here
    follows every body shape, expression and pose because it is tied to vertices, not to space."""
    import torch
    m = _model()
    ph = {k: torch.tensor([float(v)], dtype=m.dtype) for k, v in TEMPLATE_PHENOTYPE.items()}
    eye4 = torch.eye(4, dtype=m.dtype)[None, None].repeat(1, m.bone_count, 1, 1)
    with torch.no_grad(), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = m(pose_parameters=eye4, phenotype_kwargs=ph)
    return out["rest_vertices"][0].numpy()


def bone_names():
    return list(_model().bone_labels)


def shape_names():
    m = _model()
    return dict(phenotype=list(m.phenotype_labels), local=list(m.local_change_labels),
                expression=list(m.facial_action_labels))


class Figure:
    """A posed figure. `meshes()` yields render-ready parts."""

    def __init__(self, phenotype=None, face=None, expression=None, pose=None,
                 position=(0, 0, 0), facing_deg=0.0, ground=True, name="figure", stylize=None):
        self.name = name
        import torch
        m = _model()
        ph = dict(DEFAULT_PHENOTYPE)
        ph.update(phenotype or {})
        if float(ph["age"]) < ADULT_AGE_MIN:
            # adult presets carry bust shaping (cup size, lift, volume); a young body keeps the model's own neutral shape
            ph["cupsize"] = ph["firmness"] = NEUTRAL_AXIS
            face = {k: v for k, v in (face or {}).items() if not k.startswith(BUST_SHAPING)}
        dtype = m.dtype
        as_t = lambda d: {k: torch.tensor([float(v)], dtype=dtype) for k, v in d.items()}
        unknown = [k for k in (face or {}) if k not in m.local_change_labels]
        unknown += [k for k in (expression or {}) if k not in m.facial_action_labels]
        # pose: {bone: 3x3 rotation} from poses.resolve(), or {bone: (rx, ry, rz)} raw Euler angles
        unknown += [k for k in (pose or {}) if k not in m.bone_labels]
        if unknown:
            raise KeyError(f"unknown figure parameters: {unknown}")
        deltas = torch.eye(4, dtype=dtype)[None, None].repeat(1, m.bone_count, 1, 1)
        for bone, rotation in (pose or {}).items():
            matrix = rotation if np.shape(rotation) == (3, 3) else euler_matrix(*rotation)
            deltas[0, m.bone_labels.index(bone), :3, :3] = torch.tensor(np.asarray(matrix), dtype=dtype)
        with torch.no_grad(), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = m(pose_parameters=deltas, phenotype_kwargs=as_t(ph),
                    local_changes_kwargs=as_t(face or {}) or None,
                    facial_actions=as_t(expression or {}) or None)
        self.model = m
        self.rest_vertices = out["rest_vertices"][0].numpy().astype(np.float64)
        self.bone_poses = out["bone_poses"][0].numpy().astype(np.float64)
        self.rest_bone_poses = out["rest_bone_poses"][0].numpy().astype(np.float64)
        verts = out["vertices"][0].numpy().astype(np.float64)
        if stylize:
            verts = verts + self._stylize_offsets(stylize)
        spin = euler_matrix(0, 0, facing_deg)
        verts = verts @ spin.T
        offset = np.asarray(position, float).copy()
        if ground:  # put the lowest body point on z = position.z
            offset[2] -= verts[BODY_RANGE[0]:BODY_RANGE[1], 2].min()
        self.vertices = verts + offset
        self.world = np.eye(4); self.world[:3, :3] = spin; self.world[:3, 3] = offset
        self.faces = m.faces.numpy().astype(np.int64)
        uv = m.texture_coordinates.numpy()
        self.face_uv = uv[m.face_texture_coordinate_indices.numpy()]
        self.rest_attr = self._rest_attributes()

    def _stylize_offsets(self, style):
        """Face restyling offsets, measured on the rest mesh and turned with the head into the posed mesh."""
        from . import face_shape
        eyes = [self._group_range(f"helper-{side}-eye") for side in ("l", "r")]
        delta = face_shape.offsets(self.rest_vertices, _template_vertices(), eyes, style)
        i = self.model.bone_labels.index("head")
        head_turn = self.bone_poses[i][:3, :3] @ self.rest_bone_poses[i][:3, :3].T
        return delta @ head_turn.T

    # -- pose-invariant attributes -------------------------------------------------
    def _rest_attributes(self):
        """Per-vertex data measured on the rest mesh so it survives posing."""
        rest = self.rest_vertices
        attr = {}
        iris = np.full(len(rest), np.pi, np.float32)
        eye = np.zeros((len(rest), 3), np.float32)
        eye[:, 0] = np.pi
        for side in ("l", "r"):
            lo, hi = self._group_range(f"helper-{side}-eye")
            ball = rest[lo:hi]
            centre = ball.mean(0)
            direction = ball - centre
            direction /= np.linalg.norm(direction, axis=1, keepdims=True)
            # angle from the forward (-Y) axis: 0 at the pupil centre
            iris[lo:hi] = np.arccos(np.clip(-direction[:, 1], -1, 1))
            # (angle, sideways, upward) lets the eye painter draw iris gradients and highlights
            eye[lo:hi, 0] = iris[lo:hi]
            eye[lo:hi, 1] = direction[:, 0]
            eye[lo:hi, 2] = direction[:, 2]
        attr["eye"] = eye
        attr["tpl"] = _template_vertices().astype(np.float32)
        return attr

    @staticmethod
    def _group_range(name):
        import anny, json, os
        path = os.path.join(anny.__path__[0], "data", "mpfb2", "mesh_metadata", "basemesh_vertex_groups.json")
        if not hasattr(Figure, "_groups"):
            with open(path) as handle:
                Figure._groups = json.load(handle)
        lo, hi = Figure._groups[name][0]
        return lo, hi + 1

    def bone_head(self, bone):
        """World position of a bone's origin (useful for attaching props or aiming the camera)."""
        p = self.bone_poses[self.model.bone_labels.index(bone)][:3, 3]
        return self.world[:3, :3] @ p + self.world[:3, 3]

    def bone_rotation(self, bone):
        """World rotation a bone has accumulated from its rest orientation (before the figure's facing)."""
        i = self.model.bone_labels.index(bone)
        return self.bone_poses[i][:3, :3] @ self.rest_bone_poses[i][:3, :3].T

    def bone_position(self, bone):
        """Bone origin in the figure's own space (before facing and placement)."""
        return self.bone_poses[self.model.bone_labels.index(bone)][:3, 3]

    def palm(self, side):
        """World frame of a palm: (centre inside the hand, normal out of the palm, finger direction).

        side: "L" or "R". Used to put an object in a hand."""
        from .poses import _hand_axes
        bones = [f"wrist.{side}", f"finger2-1.{side}", f"finger3-1.{side}", f"finger5-1.{side}"]
        centre = np.mean([self.bone_head(b) for b in bones], axis=0)
        hand_dir, _, palm = _hand_axes(side)
        turn = self.world[:3, :3] @ self.bone_rotation(f"wrist.{side}")
        return centre, turn @ palm, turn @ hand_dir

    def pinch(self, side):
        """Where a cigarette sits between the index and middle fingers: (point, direction out past the index
        finger, palm normal), world space."""
        point = (self.bone_head(f"finger2-2.{side}") + self.bone_head(f"finger3-2.{side}")) / 2
        across = self.bone_head(f"finger2-1.{side}") - self.bone_head(f"finger5-1.{side}")
        _, normal, _ = self.palm(side)
        return point, across / max(np.linalg.norm(across), 1e-9), normal

    def landmark(self, name, offset=0.0, local=False):
        """Position of a named body landmark on the posed skin, pushed `offset` metres off the surface.

        local=True returns the point in the figure's own space (before facing and placement)."""
        vertex, normal = self._landmark_vertex(name)
        point = vertex + normal * offset
        if local:
            return self.world[:3, :3].T @ (point - self.world[:3, 3])
        return point

    def surface_normal(self, name):
        """World direction out of the skin at a named landmark (a palm laid there faces the opposite way)."""
        return self._landmark_vertex(name)[1]

    def _landmark_vertex(self, name):
        if name not in LANDMARKS:
            raise KeyError(f"unknown landmark '{name}'. Available: {sorted(LANDMARKS)}")
        tpl = self.rest_attr["tpl"][BODY_RANGE[0]:BODY_RANGE[1]]
        index = int(np.argmin(np.linalg.norm(tpl - np.asarray(LANDMARKS[name]), axis=1)))
        body_faces = self.faces[(self.faces < BODY_RANGE[1]).all(1)]
        normal = Mesh(self.vertices, body_faces).vertex_normals()[index]
        return self.vertices[index], normal

    def bone_frame(self, bone):
        m = self.world @ self.bone_poses[self.model.bone_labels.index(bone)]
        return m

    def _material_of_faces(self):
        first = self.faces[:, 0]
        mat = np.full(len(self.faces), "skin", object)
        for name, material in (("helper-l-eye", "eye"), ("helper-r-eye", "eye"),
                               ("helper-upper-teeth", "teeth"), ("helper-lower-teeth", "teeth"),
                               ("helper-tongue", "tongue"),
                               ("helper-l-eyelashes-1", "lash"), ("helper-l-eyelashes-2", "lash"),
                               ("helper-r-eyelashes-1", "lash"), ("helper-r-eyelashes-2", "lash")):
            for lo, hi in Figure._groups[name] if hasattr(Figure, "_groups") else []:
                mat[(first >= lo) & (first <= hi)] = material
        return mat

    def meshes(self, subdivisions=1):
        """Body parts as meshes. Materials are namespaced '<figure name>.<material>'."""
        self._group_range("body")  # ensure groups are loaded
        mats = self._material_of_faces()
        out = []
        for material in ("skin", "eye", "teeth", "tongue", "lash"):
            sel = mats == material
            if sel.any():
                # eyes, teeth and lashes share the body's outline group so no ink line rings the eyeball
                part = Mesh(self.vertices, self.faces[sel], f"{self.name}.{material}", self.name,
                            self.face_uv[sel], dict(self.rest_attr))
                out.append(subdivide(part, subdivisions) if subdivisions else part)
        # teeth are helper geometry the body model leaves out; they ride the jaw like any other vertex
        teeth = np.concatenate([_base_obj_groups()["helper-upper-teeth"], _base_obj_groups()["helper-lower-teeth"]])
        out.append(Mesh(self.vertices, teeth, f"{self.name}.teeth", self.name, None, {"tpl": self.rest_attr["tpl"]}))
        return out

    def helper_mesh(self, helper, material, part=None):
        """Helper shells that hug the body: 'helper-tights', 'helper-skirt', 'helper-hair'."""
        faces = _base_obj_groups()[helper]
        return Mesh(self.vertices, faces, material, part or material, None, {"tpl": self.rest_attr["tpl"]})
