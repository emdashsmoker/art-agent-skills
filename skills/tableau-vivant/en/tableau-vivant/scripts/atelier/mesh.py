"""Mesh container shared by every form generator (figure, hair, props, terrain)."""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Mesh:
    vertices: np.ndarray                 # (V, 3) world space
    faces: np.ndarray                    # (F, 3) vertex indices
    material: str = "default"            # key into the palette
    part: str = "object"                 # outline grouping: lines are drawn between parts
    face_uv: np.ndarray | None = None    # (F, 3, 2) per-corner UV
    vertex_attr: dict = field(default_factory=dict)   # name -> (V,) or (V, k) pose-invariant data
    smooth: bool = True                  # smooth vertex normals vs faceted

    def vertex_normals(self):
        v, f = self.vertices, self.faces
        face_n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        normals = np.zeros_like(v)
        for corner in range(3):
            np.add.at(normals, f[:, corner], face_n)
        length = np.linalg.norm(normals, axis=1, keepdims=True)
        return normals / np.maximum(length, 1e-12)

    def transformed(self, matrix4):
        m = np.asarray(matrix4, float)
        moved = self.vertices @ m[:3, :3].T + m[:3, 3]
        return Mesh(moved, self.faces, self.material, self.part, self.face_uv, dict(self.vertex_attr), self.smooth)


def euler_matrix(rx_deg=0.0, ry_deg=0.0, rz_deg=0.0):
    """Rotation about world X, then Y, then Z (degrees) as a 3x3 matrix."""
    rx, ry, rz = np.radians([rx_deg, ry_deg, rz_deg])
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def transform(translate=(0, 0, 0), rotate_deg=(0, 0, 0), scale=1.0):
    m = np.eye(4)
    m[:3, :3] = euler_matrix(*rotate_deg) * np.asarray(scale, float)
    m[:3, 3] = translate
    return m


# ---------------------------------------------------------------------------------------------
# Loop subdivision. The body mesh is game-resolution; without this, silhouettes show facets.
# The scheme depends only on connectivity, so the (sparse) operator is cached per topology.
_SUBDIVISION_CACHE = {}


def _loop_operator(faces, n_vertices):
    """Sparse matrix S with new_vertices = S @ old_vertices, plus the refined face list."""
    from scipy import sparse
    f = faces
    edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    opposite = np.concatenate([f[:, 2], f[:, 0], f[:, 1]])
    unique, inverse, counts = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    inverse = inverse.ravel()
    n_edges = len(unique)
    interior = counts == 2
    rows, cols, vals = [], [], []
    # edge points: 3/8 of each endpoint + 1/8 of each opposite vertex (1/2 + 1/2 on borders)
    end_w = np.where(interior, 0.375, 0.5)
    for k in range(2):
        rows.append(n_vertices + np.arange(n_edges)); cols.append(unique[:, k]); vals.append(end_w)
    is_interior_corner = interior[inverse]
    rows.append(n_vertices + inverse[is_interior_corner])
    cols.append(opposite[is_interior_corner])
    vals.append(np.full(is_interior_corner.sum(), 0.125))
    # original points: pulled toward the average of their neighbours
    valence = np.bincount(unique.ravel(), minlength=n_vertices)
    on_border = np.zeros(n_vertices, bool)
    on_border[unique[~interior].ravel()] = True
    beta = np.where(valence > 3, 3.0 / (8.0 * np.maximum(valence, 1)), 3.0 / 16.0)
    used = valence > 0
    keep = np.where(on_border, 0.75, 1.0 - valence * beta)
    keep[~used] = 1.0
    rows.append(np.arange(n_vertices)); cols.append(np.arange(n_vertices)); vals.append(keep)
    for a, b in ((0, 1), (1, 0)):
        src, dst = unique[:, a], unique[:, b]
        smooth = ~on_border[dst]                       # interior vertex: every neighbour contributes beta
        rows.append(dst[smooth]); cols.append(src[smooth]); vals.append(beta[dst[smooth]])
        crease = on_border[dst] & ~interior            # border vertex: only border neighbours, 1/8 each
        rows.append(dst[crease]); cols.append(src[crease]); vals.append(np.full(crease.sum(), 0.125))
    operator = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                                 shape=(n_vertices + n_edges, n_vertices))
    e01, e12, e20 = (n_vertices + inverse[i * len(f):(i + 1) * len(f)] for i in range(3))
    new_faces = np.concatenate([
        np.stack([f[:, 0], e01, e20], 1), np.stack([f[:, 1], e12, e01], 1),
        np.stack([f[:, 2], e20, e12], 1), np.stack([e01, e12, e20], 1)])
    return operator, new_faces


def subdivide(mesh, levels=1):
    """Smooth-subdivide a mesh. Vertex attributes ride along; per-corner UVs are split at midpoints."""
    for _ in range(levels):
        used, compact = np.unique(mesh.faces, return_inverse=True)
        faces = compact.reshape(mesh.faces.shape)
        key = (faces.shape, hash(faces.tobytes()))
        if key not in _SUBDIVISION_CACHE:
            _SUBDIVISION_CACHE[key] = _loop_operator(faces, len(used))
        operator, new_faces = _SUBDIVISION_CACHE[key]
        vertices = operator @ mesh.vertices[used]
        attrs = {name: operator @ np.asarray(value)[used] for name, value in mesh.vertex_attr.items()}
        face_uv = None
        if mesh.face_uv is not None:
            a, b, c = mesh.face_uv[:, 0], mesh.face_uv[:, 1], mesh.face_uv[:, 2]
            ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
            face_uv = np.concatenate([np.stack([a, ab, ca], 1), np.stack([b, bc, ab], 1),
                                      np.stack([c, ca, bc], 1), np.stack([ab, bc, ca], 1)])
        mesh = Mesh(vertices, new_faces, mesh.material, mesh.part, face_uv, attrs, mesh.smooth)
    return mesh


def cut_by_margin(vertices, attrs, faces, margin):
    """Keep the region margin >= 0 with a clean edge: vertices just outside slide onto the cut line."""
    inside = margin >= 0
    faces = faces[inside[faces].any(1)]
    vertices = vertices.copy()
    attrs = {k: np.array(v, np.float64) for k, v in attrs.items()}
    total = np.zeros_like(vertices); count = np.zeros(len(vertices))
    attr_total = {k: np.zeros_like(v) for k, v in attrs.items()}
    for i, j in ((0, 1), (1, 2), (2, 0), (1, 0), (2, 1), (0, 2)):
        a, b = faces[:, i], faces[:, j]
        crossing = inside[a] & ~inside[b]
        a, b = a[crossing], b[crossing]
        t = (margin[b] / (margin[b] - margin[a]))[:, None]          # 0 at the outside vertex, 1 at the inside one
        np.add.at(total, b, vertices[b] + (vertices[a] - vertices[b]) * t)
        np.add.at(count, b, 1.0)
        for k, v in attrs.items():
            np.add.at(attr_total[k], b, v[b] + (v[a] - v[b]) * (t if v.ndim > 1 else t[:, 0]))
    moved = count > 0
    vertices[moved] = total[moved] / count[moved, None]
    for k, v in attrs.items():
        v[moved] = attr_total[k][moved] / (count[moved, None] if v.ndim > 1 else count[moved])
    return vertices, attrs, faces
