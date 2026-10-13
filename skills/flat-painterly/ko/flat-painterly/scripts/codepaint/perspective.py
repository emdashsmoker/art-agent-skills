"""1점 투시: 3차원 장면 좌표를 화면에 투영한다.

거리, 실내, 복도처럼 깊이 방향으로 뻗는 장면은 평행선이 소실점으로 모여야 공간으로 읽힌다.
건물을 상자로 정의하고 투영하면 창문 줄과 지붕선이 저절로 소실점에 맞는다.
장면 좌표: x는 좌우(오른쪽 양수), y는 높이(위 양수, 지면 0), z는 깊이(멀수록 큼, 0보다 커야 함).
"""
import numpy as np


class Perspective:
    """소실점이 1개인 카메라.

    vanish: 소실점의 화면 좌표. 지평선은 이 점의 y를 지난다.
    eye_height: 눈높이(장면 단위). 미터로 잡으면 1.6이 선 사람의 시선이다.
    focal: 깊이 1에 있는 장면 길이 1이 화면에서 차지하는 길이(논리 단위). 클수록 망원.
    """

    def __init__(self, vanish, eye_height=1.6, focal=900.0):
        self.vanish = np.asarray(vanish, np.float64)
        self.eye_height = float(eye_height)
        self.focal = float(focal)

    def project(self, x, y, z):
        """장면의 점 1개를 화면 좌표로."""
        if z <= 0.0:
            raise ValueError("깊이 z는 0보다 커야 함")
        return (self.vanish[0] + x * self.focal / z, self.vanish[1] + (self.eye_height - y) * self.focal / z)

    def path(self, points):
        """장면 점열 [(x, y, z), ...]을 화면 경로로."""
        return np.array([self.project(*point) for point in points])

    def scale_at(self, z):
        """깊이 z에서 장면 길이 1의 화면 길이. 사람, 가로등 같은 부품의 크기를 정할 때 쓴다."""
        return self.focal / z

    def side_wall(self, x, z_near, z_far, y_bottom, y_top):
        """깊이 방향으로 뻗은 벽(길 양옆 건물의 옆면)."""
        return self.path([(x, y_bottom, z_near), (x, y_top, z_near), (x, y_top, z_far), (x, y_bottom, z_far)])

    def front_wall(self, x_left, x_right, z, y_bottom, y_top):
        """카메라를 마주 보는 벽(길 끝 건물, 옆 건물의 정면)."""
        return self.path([(x_left, y_bottom, z), (x_left, y_top, z), (x_right, y_top, z), (x_right, y_bottom, z)])

    def ground(self, x_left, x_right, z_near, z_far, y=0.0):
        """지면 위의 사각형(차도, 인도, 횡단보도 줄)."""
        return self.path([(x_left, y, z_near), (x_right, y, z_near), (x_right, y, z_far), (x_left, y, z_far)])

    def side_wall_grid(self, x, z_near, z_far, y_bottom, y_top, columns, rows, margin=0.25):
        """옆면 벽을 칸으로 나눈 사각형 목록(창문, 문). margin은 칸 크기 대비 여백 비율."""
        cells = []
        depth = (z_far - z_near) / columns
        height = (y_top - y_bottom) / rows
        for column in range(columns):
            for row in range(rows):
                z0 = z_near + depth * (column + margin)
                z1 = z_near + depth * (column + 1 - margin)
                y0 = y_bottom + height * (row + margin)
                y1 = y_bottom + height * (row + 1 - margin)
                cells.append(self.path([(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]))
        return cells

    def front_wall_grid(self, x_left, x_right, z, y_bottom, y_top, columns, rows, margin=0.25):
        """정면 벽을 칸으로 나눈 사각형 목록."""
        cells = []
        width = (x_right - x_left) / columns
        height = (y_top - y_bottom) / rows
        for column in range(columns):
            for row in range(rows):
                x0 = x_left + width * (column + margin)
                x1 = x_left + width * (column + 1 - margin)
                y0 = y_bottom + height * (row + margin)
                y1 = y_bottom + height * (row + 1 - margin)
                cells.append(self.path([(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)]))
        return cells
