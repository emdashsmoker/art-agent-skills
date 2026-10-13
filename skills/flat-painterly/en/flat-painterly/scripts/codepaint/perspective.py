"""One-point perspective: projects 3D scene coordinates onto the screen.

Scenes that recede in depth, such as streets, interiors and corridors, read as space only when parallel lines meet
at a vanishing point.
Define buildings as boxes and project them, and window rows and rooflines line up with the vanishing point
automatically.
Scene coordinates: x is left-right (right positive), y is height (up positive, ground 0), z is depth (larger is
farther, must be above 0).
"""
import numpy as np


class Perspective:
    """A camera with one vanishing point.

    vanish: screen coordinates of the vanishing point. The horizon passes through its y.
    eye_height: eye level in scene units. In meters, 1.6 is the eye line of a standing person.
    focal: screen length (logical units) of a scene length of 1 at depth 1. Larger values give a telephoto look.
    """

    def __init__(self, vanish, eye_height=1.6, focal=900.0):
        self.vanish = np.asarray(vanish, np.float64)
        self.eye_height = float(eye_height)
        self.focal = float(focal)

    def project(self, x, y, z):
        """Project one scene point to screen coordinates."""
        if z <= 0.0:
            raise ValueError("depth z must be greater than 0")
        return (self.vanish[0] + x * self.focal / z, self.vanish[1] + (self.eye_height - y) * self.focal / z)

    def path(self, points):
        """Project a scene point list [(x, y, z), ...] to a screen path."""
        return np.array([self.project(*point) for point in points])

    def scale_at(self, z):
        """Screen length of a scene length of 1 at depth z. Used to size parts such as people and streetlights."""
        return self.focal / z

    def side_wall(self, x, z_near, z_far, y_bottom, y_top):
        """A wall that recedes in depth (the side face of buildings along a street)."""
        return self.path([(x, y_bottom, z_near), (x, y_top, z_near), (x, y_top, z_far), (x, y_bottom, z_far)])

    def front_wall(self, x_left, x_right, z, y_bottom, y_top):
        """A wall facing the camera (the building at the end of the street, the front of a side building)."""
        return self.path([(x_left, y_bottom, z), (x_left, y_top, z), (x_right, y_top, z), (x_right, y_bottom, z)])

    def ground(self, x_left, x_right, z_near, z_far, y=0.0):
        """A rectangle on the ground (roadway, sidewalk, crosswalk stripe)."""
        return self.path([(x_left, y, z_near), (x_right, y, z_near), (x_right, y, z_far), (x_left, y, z_far)])

    def side_wall_grid(self, x, z_near, z_far, y_bottom, y_top, columns, rows, margin=0.25):
        """List of rectangles that divide a side wall into cells (windows, doors). margin is the gap ratio to the
        cell size."""
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
        """List of rectangles that divide a facing wall into cells."""
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
