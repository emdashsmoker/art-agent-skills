"""Stage: scene coordinates where two or more people and props share one line of sight.

World coordinates: x points to screen right, y points down (floor is 0), z points away from the viewer. The unit is
the head height.
Each person gets a figure3d rig, and the screen origin comes from projecting the world position of the pelvis with
the shared view.
The projection is orthographic, so the depth order, heights and contact points of two people and props stay
consistent within one view.
reach computes arm angles so that the wrist meets a world-coordinate target (holding hands, lifting a cup, gripping
an umbrella shaft).
collisions finds places where one person's arm passes through another person's torso or arm.
A piercing arm looks cut in the middle whatever the paint order, so check it before rendering.
"""
from dataclasses import dataclass

import numpy as np

from . import character
from .figure import BONE_LENGTH, LIMB_PROFILE
from .figure3d import Figure3D, _yaw, view_matrix
from .geometry import Frame

# direction the elbow points to (body coordinates: outward, down, back). Only the component perpendicular to
# the target direction is used.
# For two people standing shoulder to shoulder, the inner arm's outward side faces the partner, so place's
# poles overrides the outward component with 0 or a negative value.
ELBOW_POLE = (0.45, 1.0, 0.35)
REACH_SLACK = 0.995               # margin that keeps the arm from fully straightening
CYLINDER_SEGMENTS = 48
FIST_REACH = 0.42                 # the fist center lies this fraction of the hand length beyond the wrist
FIST_FIT_ROUNDS = 6               # iterations that correct the wrist target when fists aligns the fist center. With 6, the error is around 0.0001 head heights
ARM_BONES = (("upper_arm", "shoulder", "elbow"), ("forearm", "elbow", "wrist"))
BONE_SAMPLES = 25                 # number of points per bone in the penetration check. The spacing is about a quarter of the arm thickness


@dataclass(frozen=True)
class Collision:
    """One penetration. The model's limb (for example forearm_r) pierces the other's part (torso or an arm bone such
    as upper_arm_l)."""
    model: int
    limb: str
    other: int
    part: str


def _direction_angles(direction, side):
    """Convert a unit direction in body coordinates to figure3d (spread, forward-back swing) angles. Inverse of
    _down."""
    sign = -1.0 if side == "l" else 1.0
    swing = np.rad2deg(np.arcsin(np.clip(-direction[2], -1.0, 1.0)))
    abduct = np.rad2deg(np.arctan2(sign * direction[0], direction[1]))
    return float(abduct), float(swing)


def _fist_point(wrist, elbow):
    """Fist center, FIST_REACH beyond the wrist along the forearm."""
    axis = (wrist - elbow) / max(np.linalg.norm(wrist - elbow), 1e-9)
    return wrist + axis * BONE_LENGTH["hand"] * FIST_REACH


def arm_toward(shoulder, target, side, upper=BONE_LENGTH["upper_arm"], fore=BONE_LENGTH["forearm"],
               pole=ELBOW_POLE):
    """Angles that fold a two-bone arm from the shoulder to the target. ((upper arm spread, forearm spread), (upper
    arm swing, forearm swing)).

    A target beyond arm length gives a nearly straight arm in that direction. All coordinates are body coordinates.
    """
    sign = -1.0 if side == "l" else 1.0
    offset = np.asarray(target, np.float64) - shoulder
    distance = min(max(np.linalg.norm(offset), 1e-6), (upper + fore) * REACH_SLACK)
    axis = offset / max(np.linalg.norm(offset), 1e-9)
    along = (upper ** 2 - fore ** 2 + distance ** 2) / (2.0 * distance)
    height = np.sqrt(max(upper ** 2 - along ** 2, 0.0))
    bend = np.array([sign * pole[0], pole[1], pole[2]], np.float64)
    bend = bend - axis * np.dot(bend, axis)
    bend = bend / max(np.linalg.norm(bend), 1e-9)
    elbow = shoulder + axis * along + bend * height
    wrist = shoulder + axis * distance
    upper_angles = _direction_angles((elbow - shoulder) / upper, side)
    fore_angles = _direction_angles((wrist - elbow) / max(np.linalg.norm(wrist - elbow), 1e-9), side)
    return (upper_angles[0], fore_angles[0]), (upper_angles[1], fore_angles[1])


class Stage:
    """A stage that shares one line of sight. origin is the screen coordinate of the world origin (floor center),
    unit is the screen length of one head height."""

    def __init__(self, origin, unit, elevation=0.0):
        self.origin = np.asarray(origin, np.float64)
        self.unit = float(unit)
        self.elevation = float(elevation)
        self.view = view_matrix(0.0, elevation)

    def project(self, points):
        """Project a world-coordinate point list to screen coordinates."""
        rotated = np.atleast_2d(np.asarray(points, np.float64)) @ self.view.T
        return self.origin + rotated[:, :2] * self.unit

    def point(self, x, y, z):
        return tuple(self.project([(x, y, z)])[0])

    def depth(self, point):
        """View depth. Larger is farther."""
        return float((self.view @ np.asarray(point, np.float64))[2])

    def facing(self, normal):
        return float(-(self.view @ np.asarray(normal, np.float64))[2])

    # ---------- people ----------

    def _settings(self, look, turn, pose):
        return dict(build=look.build, depth=look.depth, turn=turn, stretch=dict(character.STRETCH),
                    shoulder_drop=look.shoulder_drop, **pose)

    def pelvis_height(self, look, turn, floor=0.0, **pose):
        """World y of the pelvis when the lowest foot touches the floor."""
        probe = Figure3D(Frame((0.0, 0.0), 1.0), **self._settings(look, turn, pose))
        return floor - max(probe._foot_cloud(side)[:, 1].max() for side in "lr")

    def place(self, look, x, z, turn, floor=0.0, head_pitch=0.0, ink=character.ANIME, outfit=None, reach=None,
              pelvis_y=None, grips=(), palm_out=(), poles=None, fists=None, **pose):
        """A person standing at world (x, z). With reach={"arm_r": world target}, arm angles are set so that wrist
        meets the target.

        fists={"arm_r": world target} aligns the center of the closed fist (fist_world) to the target in place of
        the wrist (umbrella shaft, held hands).
        poles={"arm_r": (outward, down, back)} replaces ELBOW_POLE as that arm's elbow direction.
        With palm_out=("r",), the palm of that closed hand faces the person beside (held hands).
        With pelvis_y, the pelvis sits at that height in place of standing on the feet (seated with feet off the
        floor).
        """
        pose = dict(pose)
        height = self.pelvis_height(look, turn, floor, **pose) if pelvis_y is None else pelvis_y
        pelvis = np.array([x, height, z], np.float64)
        targets = dict(reach or {})
        if fists:
            targets.update(self._fist_targets(look, turn, pelvis, targets, fists, pose, poles or {}))
        if targets:
            pose = self._reach_pose(look, turn, pelvis, targets, pose, poles or {})
        model = character.place(look, tuple(self.project([pelvis])[0]), self.unit, turn, self.elevation, head_pitch,
                                ink, outfit, grips, palm_out=palm_out, **pose)
        model.world = pelvis
        return model

    def _reach_pose(self, look, turn, pelvis, reach, pose, poles):
        probe = Figure3D(Frame((0.0, 0.0), 1.0), **self._settings(look, turn, pose))
        to_body = _yaw(turn).T
        swing = dict(pose.get("swing") or {})
        pose = dict(pose)
        for limb, target in reach.items():
            side = limb[-1]
            local = to_body @ (np.asarray(target, np.float64) - pelvis)
            abduct, swings = arm_toward(probe.joints3["shoulder_" + side], local, side,
                                        pole=poles.get(limb, ELBOW_POLE))
            pose[limb] = abduct
            swing[limb] = swings
        pose["swing"] = swing
        return pose

    def _fist_targets(self, look, turn, pelvis, reach, fists, pose, poles):
        """Wrist target that puts the fist center on the fists point. Repeats placing the wrist and shifting the
        target by the fist offset."""
        goals = {limb: np.asarray(point, np.float64) for limb, point in fists.items()}
        targets = dict(goals)
        for _ in range(FIST_FIT_ROUNDS):
            probe = Figure3D(Frame((0.0, 0.0), 1.0),
                             **self._settings(look, turn, self._reach_pose(look, turn, pelvis, {**reach, **targets},
                                                                           pose, poles)))
            to_world = _yaw(turn)
            for limb, goal in goals.items():
                side = limb[-1]
                wrist, elbow = (to_world @ probe.joints3[f"{joint}_{side}"] + pelvis for joint in ("wrist", "elbow"))
                targets[limb] = targets[limb] + (goal - _fist_point(wrist, elbow))
        return targets

    def to_world(self, model, point):
        """Convert a person's body-coordinate point to world coordinates."""
        return _yaw(model.body.turn) @ np.asarray(point, np.float64) + model.world

    def joint_world(self, model, name):
        return self.to_world(model, model.body.joints3[name])

    def fist_world(self, model, side):
        """World coordinates of the closed hand center. About half a hand length beyond the wrist along the forearm
        (umbrella shaft, handle position)."""
        return _fist_point(self.joint_world(model, "wrist_" + side), self.joint_world(model, "elbow_" + side))

    def far_first(self, models):
        """People sorted from the farthest pelvis. Paint the far person first."""
        return sorted(models, key=lambda model: -self.depth(model.world))

    # ---------- penetration check ----------

    def collisions(self, models):
        """List of penetrations between people [Collision, ...]. An empty list means no arm pierces another person's
        torso or arms.

        A penetration is an arm bone center line inside another person's torso, or two people's arm bones closer
        than the sum of their thicknesses.
        An arm touching a body is no penetration. Overlaps within one person and legs, clothes and hands are not
        checked.
        """
        found = []
        for index, model in enumerate(models):
            for other_index, other in enumerate(models):
                if other_index == index:
                    continue
                for side in "lr":
                    for bone, _, _ in ARM_BONES:
                        if any(other.body.inside_torso(self._to_body(other, point))
                               for point in self._bone_samples(model, side, bone)[0]):
                            found.append(Collision(index, f"{bone}_{side}", other_index, "torso"))
                if other_index < index:
                    continue
                for side in "lr":
                    for other_side in "lr":
                        for bone, _, _ in ARM_BONES:
                            for other_bone, _, _ in ARM_BONES:
                                if self._bones_cross(model, side, bone, other, other_side, other_bone):
                                    found.append(Collision(index, f"{bone}_{side}", other_index,
                                                           f"{other_bone}_{other_side}"))
        return found

    def _to_body(self, model, point):
        """Convert a world-coordinate point to the person's body coordinates. Inverse of to_world."""
        return _yaw(model.body.turn).T @ (np.asarray(point, np.float64) - model.world)

    def _bone_samples(self, model, side, bone):
        """Points along an arm bone (world coordinates, BONE_SAMPLES x 3) and the radius there (follows the
        thickness profile of LIMB_PROFILE)."""
        start, end = next((self.joint_world(model, f"{a}_{side}"), self.joint_world(model, f"{b}_{side}"))
                          for name, a, b in ARM_BONES if name == bone)
        ts = np.linspace(0.0, 1.0, BONE_SAMPLES)
        widths = np.asarray(LIMB_PROFILE[bone]) * model.look.build.arm
        radii = np.interp(ts, np.linspace(0.0, 1.0, len(widths)), widths) / 2.0
        return start + np.outer(ts, end - start), radii

    def _bones_cross(self, model, side, bone, other, other_side, other_bone):
        points, radii = self._bone_samples(model, side, bone)
        other_points, other_radii = self._bone_samples(other, other_side, other_bone)
        gaps = np.linalg.norm(points[:, None, :] - other_points[None, :, :], axis=2)
        return bool((gaps < radii[:, None] + other_radii[None, :]).any())

    # ---------- props ----------

    def box(self, x_range, y_range, z_range):
        """Visible faces of a box [(name, screen outline, outward normal), ...]. Names are top, bottom, front, back,
        left, right."""
        (x0, x1), (y0, y1), (z0, z1) = x_range, y_range, z_range
        faces = {"top": ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
                 "bottom": ((0, 1, 0), [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]),
                 "front": ((0, 0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]),
                 "back": ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
                 "left": ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
                 "right": ((1, 0, 0), [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)])}
        return [(name, self.project(corners), np.array(normal, np.float64))
                for name, (normal, corners) in faces.items() if self.facing(normal) > 0.0]

    def ellipse(self, center, radius, y, segments=CYLINDER_SEGMENTS, radius_z=None):
        """A circle parallel to the floor (table top, plate, floor shadow). center is (x, z)."""
        theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
        radius_z = radius if radius_z is None else radius_z
        ring = np.column_stack([center[0] + radius * np.cos(theta), np.full(segments, y),
                                center[1] + radius_z * np.sin(theta)])
        return self.project(ring)

    def cylinder(self, center, radius, top, bottom, segments=CYLINDER_SEGMENTS):
        """An upright cylinder (cup, table leg, pillar). {'side': side outline, 'top': top outline}. top and bottom
        are world y.

        The side comes down from the left and right ends of the top and passes the front arc of the bottom. Paint
        the top after the side to form a cylinder.
        """
        upper, lower = self.ellipse(center, radius, top, segments), self.ellipse(center, radius, bottom, segments)
        right, left = int(np.argmax(upper[:, 0])), int(np.argmin(upper[:, 0]))
        forward = [(right + step) % segments for step in range((left - right) % segments + 1)]
        backward = [(right - step) % segments for step in range((right - left) % segments + 1)]
        near = forward if lower[forward, 1].mean() > lower[backward, 1].mean() else backward
        return {"side": np.vstack([upper[[right]], lower[near], upper[[left]]]), "top": upper}
