"""3차원 입체: 임의 시점의 카메라, 상자와 기둥, 빛 방향에 따른 면 명암.

현대 사물(컴퓨터, 전화기, 컵, 책, 가구)은 직육면체와 기둥을 조합한 형태다.
면을 3차원으로 정의하고 카메라로 투영하면 어느 방향에서 보든 원근과 면의 명암이 맞는다.
장면 좌표: x 오른쪽, y 위, z 깊이(앞에서 뒤로). 단위는 자유이며 사물에는 cm를 권장한다.
"""
import numpy as np

from . import color as colors

MIN_DEPTH = 1e-3
DEFAULT_SEGMENTS = 64
SEAM_OVERLAP_PX = 0.6


def _normalize(vector):
    vector = np.asarray(vector, np.float64)
    return vector / max(np.linalg.norm(vector), 1e-12)


def _rotation(yaw, pitch):
    """pitch(x축) 뒤에 yaw(y축)를 적용하는 회전 행렬.

    yaw 양수: 위에서 볼 때 시계 방향. 정면(-z를 향한 면)이 화면 왼쪽으로 돈다.
    pitch 양수: 윗부분이 카메라 반대쪽(+z)으로 넘어간다.
    """
    a, b = np.deg2rad(yaw), np.deg2rad(pitch)
    pitch_matrix = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(b), -np.sin(b)], [0.0, np.sin(b), np.cos(b)]])
    yaw_matrix = np.array([[np.cos(a), 0.0, np.sin(a)], [0.0, 1.0, 0.0], [-np.sin(a), 0.0, np.cos(a)]])
    return yaw_matrix @ pitch_matrix


class Face:
    """평면 다각형 1개.

    vertices: (N, 3) 꼭짓점. normal: 바깥을 향한 단위 법선.
    frame: (원점, u 벡터, v 벡터). point(u, v)가 면 위의 점을 0-1 좌표로 찾는 기준이다.
        상자의 정면은 u가 왼쪽에서 오른쪽, v가 위에서 아래로 가서 화면 내용을 붙이기 쉽다.
    smooth: 곡면을 쪼갠 조각이면 True. 조각 사이에 모서리 선을 긋지 않는다.
    """

    def __init__(self, vertices, normal, name, frame=None, smooth=False):
        self.vertices = np.asarray(vertices, np.float64)
        self.normal = _normalize(normal)
        self.name = name
        if frame is None:
            v = self.vertices
            frame = (v[0], v[1] - v[0], v[-1] - v[0])
        self.frame = tuple(np.asarray(part, np.float64) for part in frame)
        self.smooth = smooth

    @property
    def center(self):
        return self.vertices.mean(axis=0)

    def point(self, u, v):
        """면 위의 점. (0, 0)은 frame 원점, (1, 1)은 반대쪽 모서리."""
        origin, u_vector, v_vector = self.frame
        return origin + u * u_vector + v * v_vector

    def region(self, u0, v0, u1, v1):
        """면 위의 사각 영역 꼭짓점 4개. 화면, 자판, 라벨, 창문을 면에 붙일 때 쓴다."""
        return np.array([self.point(u0, v0), self.point(u1, v0), self.point(u1, v1), self.point(u0, v1)])

    def transformed(self, matrix, offset):
        origin, u_vector, v_vector = self.frame
        return Face(self.vertices @ matrix.T + offset, matrix @ self.normal, self.name,
                    (matrix @ origin + offset, matrix @ u_vector, matrix @ v_vector), self.smooth)


class Solid:
    """면의 모음. 변형은 원본을 바꾸지 않고 새 Solid를 돌려준다."""

    def __init__(self, faces):
        self.faces = list(faces)

    def moved(self, offset):
        return Solid(face.transformed(np.eye(3), np.asarray(offset, np.float64)) for face in self.faces)

    def rotated(self, yaw=0.0, pitch=0.0, about=(0.0, 0.0, 0.0)):
        """about 점을 기준으로 pitch 뒤에 yaw를 적용해 회전."""
        matrix = _rotation(yaw, pitch)
        about = np.asarray(about, np.float64)
        return Solid(face.transformed(matrix, about - matrix @ about) for face in self.faces)

    def face(self, name):
        """이름이 같은 첫 면. 화면이나 자판을 붙일 면을 찾을 때 쓴다."""
        for face in self.faces:
            if face.name == name:
                return face
        raise KeyError(f"면 이름이 없음: {name!r}")

    @property
    def center(self):
        return np.mean([face.center for face in self.faces], axis=0)


def box(center, size):
    """직육면체. size는 (폭, 높이, 깊이).

    면 이름: front(-z), back(+z), left(-x), right(+x), top(+y), bottom(-y).
    top 면은 u가 왼쪽에서 오른쪽, v가 뒤에서 앞으로 간다(자판의 줄 순서).
    """
    cx, cy, cz = center
    w, h, d = (value / 2.0 for value in size)
    x0, x1, y0, y1, z0, z1 = cx - w, cx + w, cy - h, cy + h, cz - d, cz + d
    quads = {
        "front": ([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], (0, 0, -1)),
        "back": ([(x1, y1, z1), (x0, y1, z1), (x0, y0, z1), (x1, y0, z1)], (0, 0, 1)),
        "left": ([(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)], (-1, 0, 0)),
        "right": ([(x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (x1, y0, z0)], (1, 0, 0)),
        "top": ([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], (0, 1, 0)),
        "bottom": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
    }
    return Solid(Face(vertices, normal, name) for name, (vertices, normal) in quads.items())


def slab(center, size, radius=0.0, segments=10):
    """모서리가 둥근 판. 전화기, 노트북, 모니터, 태블릿처럼 정면이 둥근 사각형인 물건에 쓴다.

    size는 (폭, 높이, 두께). 정면(front)이 -z를 향해 서 있다. 눕히려면 rotated(pitch=90, about=중심).
    면 이름: front, back, side.
    """
    width, height, depth = size
    radius = min(radius, width / 2.0, height / 2.0)
    if radius > 0.0:
        quarter = np.linspace(0.0, np.pi / 2.0, segments)
        x, y = width / 2.0 - radius, height / 2.0 - radius
        corners = [(x, -y, -np.pi / 2.0), (x, y, 0.0), (-x, y, np.pi / 2.0), (-x, -y, np.pi)]
        outline = np.vstack([np.column_stack([cx + radius * np.cos(start + quarter),
                                              cy + radius * np.sin(start + quarter)])
                             for cx, cy, start in corners])
    else:
        outline = np.array([(-width / 2.0, -height / 2.0), (width / 2.0, -height / 2.0),
                            (width / 2.0, height / 2.0), (-width / 2.0, height / 2.0)])
    solid = prism(outline, depth, smooth_sides=radius > 0.0)
    return solid.moved((center[0], center[1], center[2] - depth / 2.0))


def prism(outline, depth, smooth_sides=False):
    """xy 평면의 윤곽(y 위 방향)을 z 0에서 depth까지 밀어낸 기둥. 면 이름: front, back, side."""
    outline = np.asarray(outline, np.float64)
    x, y = outline[:, 0], outline[:, 1]
    if np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) > 0.0:
        outline = outline[::-1]   # 정면에서 볼 때 시계 방향으로 맞춘다
    x_min, y_min = outline.min(axis=0)
    x_max, y_max = outline.max(axis=0)
    front = np.column_stack([outline, np.zeros(len(outline))])
    back = np.column_stack([outline, np.full(len(outline), float(depth))])
    faces = [
        Face(front, (0, 0, -1), "front", ((x_min, y_max, 0.0), (x_max - x_min, 0.0, 0.0), (0.0, y_min - y_max, 0.0))),
        Face(back[::-1], (0, 0, 1), "back", ((x_max, y_max, depth), (x_min - x_max, 0.0, 0.0),
                                             (0.0, y_min - y_max, 0.0))),
    ]
    count = len(outline)
    for index in range(count):
        a, b = outline[index], outline[(index + 1) % count]
        edge = b - a
        # 시계 방향으로 도는 윤곽에서 바깥 법선은 진행 방향의 왼쪽이다.
        normal = (-edge[1], edge[0], 0.0)
        quad = [(*a, 0.0), (*b, 0.0), (*b, depth), (*a, depth)]
        faces.append(Face(quad, normal, "side", smooth=smooth_sides))
    return Solid(faces)


def cylinder(base_center, radius, height, top_radius=None, segments=DEFAULT_SEGMENTS):
    """세운 원기둥 또는 원뿔대. top_radius를 주면 위가 좁거나 넓은 원뿔대(컵, 전등갓).

    면 이름: top, bottom, side. base_center는 밑면 중심.
    """
    top_radius = radius if top_radius is None else top_radius
    cx, cy, cz = base_center
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    cos, sin = np.cos(angles), np.sin(angles)
    bottom = np.column_stack([cx + radius * cos, np.full(segments, cy), cz + radius * sin])
    top = np.column_stack([cx + top_radius * cos, np.full(segments, cy + height), cz + top_radius * sin])
    slope = (radius - top_radius) / max(height, 1e-9)
    faces = [Face(top[::-1], (0, 1, 0), "top", ((cx - top_radius, cy + height, cz + top_radius),
                                               (2 * top_radius, 0, 0), (0, 0, -2 * top_radius))),
             Face(bottom, (0, -1, 0), "bottom")]
    for index in range(segments):
        nxt = (index + 1) % segments
        # 마지막 조각은 각도가 2π에서 0으로 넘어가므로 두 각의 평균을 쓰면 법선이 반대로 뒤집힌다.
        middle = angles[index] + np.pi / segments
        normal = (np.cos(middle), slope, np.sin(middle))
        faces.append(Face([top[index], top[nxt], bottom[nxt], bottom[index]], normal, "side", smooth=True))
    return Solid(faces)


def circle(center, radius, segments=DEFAULT_SEGMENTS):
    """수평 원 위의 3차원 점열. 컵 테두리, 접시, 받침의 윤곽을 그릴 때 camera.path와 함께 쓴다."""
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    cx, cy, cz = center
    return np.column_stack([cx + radius * np.cos(angles), np.full(segments, cy), cz + radius * np.sin(angles)])


def _inflate(path, distance):
    """볼록 다각형의 변을 바깥으로 distance만큼 밀어낸다.

    이웃한 면이 안티에일리어싱 경계에서 서로 반쯤만 덮으면 그 사이로 실선 같은 틈이 보인다.
    면마다 반 픽셀쯤 부풀려 겹치게 하면 틈이 사라진다.
    """
    x, y = path[:, 0], path[:, 1]
    sign = 1.0 if np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) > 0.0 else -1.0
    edges = np.roll(path, -1, axis=0) - path
    lengths = np.maximum(np.linalg.norm(edges, axis=1, keepdims=True), 1e-9)
    normals = sign * np.column_stack([edges[:, 1], -edges[:, 0]]) / lengths
    before, after = np.roll(normals, 1, axis=0), normals
    denominator = np.maximum(1.0 + np.sum(before * after, axis=1, keepdims=True), 0.2)
    return path + distance * (before + after) / denominator


class Camera:
    """눈 위치에서 목표점을 바라보는 원근 카메라.

    focal: 거리 1에 있는 길이 1이 화면에서 차지하는 길이(논리 단위). 클수록 망원.
    center: 목표점이 놓이는 화면 좌표.
    """

    def __init__(self, eye, target, focal=1200.0, center=(800.0, 450.0), up=(0.0, 1.0, 0.0)):
        self.eye = np.asarray(eye, np.float64)
        self.forward = _normalize(np.asarray(target, np.float64) - self.eye)
        self.right = _normalize(np.cross(up, self.forward))
        self.up = np.cross(self.forward, self.right)
        self.focal = float(focal)
        self.center = np.asarray(center, np.float64)

    def _camera_space(self, points):
        relative = np.atleast_2d(np.asarray(points, np.float64)) - self.eye
        return relative @ self.right, relative @ self.up, relative @ self.forward

    def path(self, points):
        """장면 점열을 화면 경로로."""
        x, y, z = self._camera_space(points)
        if np.any(z <= MIN_DEPTH):
            raise ValueError("카메라 뒤에 있는 점은 투영할 수 없음")
        return np.column_stack([self.center[0] + x * self.focal / z, self.center[1] - y * self.focal / z])

    def project(self, point):
        """장면의 점 1개를 화면 좌표로."""
        return tuple(self.path([point])[0])

    def depth(self, point):
        return float(self._camera_space([point])[2][0])

    def scale_at(self, point):
        """그 점의 깊이에서 장면 길이 1의 화면 길이."""
        return self.focal / self.depth(point)

    def facing(self, face):
        """카메라를 향한 면인가. 뒤를 향한 면은 그리지 않는다."""
        return float(np.dot(face.normal, self.eye - face.center)) > 0.0

    def visible_faces(self, solid):
        """카메라를 향한 면을 먼 것부터 정렬."""
        faces = [face for face in solid.faces if self.facing(face)]
        return sorted(faces, key=lambda face: -self.depth(face.center))

    def order(self, solids):
        """여러 입체를 먼 것부터 정렬. 서로 떨어진 물건을 그리는 순서로 쓴다."""
        return sorted(solids, key=lambda solid: -self.depth(solid.center))

    def region(self, face, u0, v0, u1, v1):
        """면 위 사각 영역의 화면 경로."""
        return self.path(face.region(u0, v0, u1, v1))

    def face_ellipse(self, face, u, v, radius_u, radius_v=None, segments=DEFAULT_SEGMENTS):
        """면 위 (u, v)를 중심으로 한 타원의 화면 경로. 스피커, 렌즈 테, 단추, 시계 문자판에 쓴다.

        반지름은 면 크기 대비 비율이다. 면이 정사각형이 아니면 radius_v를 따로 주어 원으로 맞춘다.
        """
        radius_v = radius_u if radius_v is None else radius_v
        angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        return self.path([face.point(u + radius_u * np.cos(a), v + radius_v * np.sin(a)) for a in angles])


def face_color(base, normal, light, ambient=0.35, highlight=0.25):
    """빛을 받는 각도에 따른 면의 색. light는 빛이 오는 쪽을 가리키는 3차원 방향.

    어두운 면은 검정을 섞지 않고 color.shade로 색상을 옮겨 탁해지지 않게 한다.
    """
    lit = max(float(np.dot(_normalize(normal), _normalize(light))), 0.0)
    amount = ambient + (1.0 - ambient) * lit
    shaded = colors.mix(colors.shade(base, 1.2), base, amount)
    return colors.mix(shaded, colors.tint(base, 0.6), highlight * lit ** 6)


def draw(canvas, camera, solid, paint, light=(-0.5, 0.8, -0.4), line=None, width=2.0, opacity=1.0,
         ambient=0.35, highlight=0.25):
    """입체를 칠하고 면 이름별 형태 사전을 돌려준다.

    paint: 색 1개 또는 {면 이름: 색} 사전. 사전에 없는 면은 "*" 키의 색, 그것도 없으면 그리지 않는다.
    line: 주면 바깥 윤곽과 평면 사이의 모서리에 선을 긋는다. 곡면 조각 사이에는 긋지 않는다.
    """
    faces = camera.visible_faces(solid)
    if not faces:
        return {}
    exact = [camera.path(face.vertices) for face in faces]
    seam = SEAM_OVERLAP_PX / canvas.scale
    paths = [_inflate(path, seam) for path in exact]
    # 보이는 면들은 화면에서 서로 겹치지 않고 이어 붙으므로 짝홀 규칙으로 채워도 실루엣이 된다.
    # 부풀린 경로를 쓰면 겹친 띠가 구멍이 되므로 원래 경로로 만든다.
    silhouette = canvas.shape(*exact)
    first = paint.get(faces[-1].name, paint.get("*")) if isinstance(paint, dict) else paint
    if first is not None:
        canvas.fill(silhouette, face_color(first, faces[-1].normal, light, ambient, 0.0), opacity=opacity)
    shapes = {}
    for face, path in zip(faces, paths):
        base = paint.get(face.name, paint.get("*")) if isinstance(paint, dict) else paint
        if base is None:
            continue
        shape = canvas.shape(path)
        canvas.fill(shape, face_color(base, face.normal, light, ambient, highlight), opacity=opacity)
        shapes[face.name] = shapes[face.name] | shape if face.name in shapes else shape
        if line is not None and not face.smooth:
            canvas.stroke(path, line, width=width, closed=True, opacity=opacity)
    if line is not None:
        canvas.fill(canvas.contour(silhouette, width), line, opacity=opacity)
    shapes["silhouette"] = silhouette
    return shapes
