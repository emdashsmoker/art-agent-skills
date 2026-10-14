#!/usr/bin/env python3
"""Contact sheet of a pose from two angles, for checking a pose before rendering the picture.

  python pose_sheet.py -o sheet.png contrapposto venus          (preset names)
  python pose_sheet.py -o sheet.png --spec pose.json            (a pose spec, or a picture spec: its first figure is used)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np                                   # noqa: E402
from atelier import poses, spec as specs             # noqa: E402
from atelier.camera import Camera                    # noqa: E402
from atelier.figure import BODY_RANGE                # noqa: E402
from atelier.gbuffer import render_gbuffer           # noqa: E402
from atelier.shade import lighting                   # noqa: E402

TILE = 300
VIEWS = ((0.35, -1.0, 0.12), (1.0, -0.25, 0.12))       # front three-quarter, side
SKIN = np.array([0.90, 0.76, 0.66])


def tile(pose_spec):
    figure = poses.make_figure(pose_spec, name="a")
    body = figure.vertices[BODY_RANGE[0]:BODY_RANGE[1]]
    centre = (body.min(0) + body.max(0)) / 2
    extent = (body.max(0) - body.min(0)).max()
    row = []
    for direction in VIEWS:
        d = np.asarray(direction) / np.linalg.norm(direction)
        camera = Camera(centre + d * extent * 2.6, centre, 26, TILE, TILE)
        g = render_gbuffer(figure.meshes(subdivisions=0), camera, supersample=1)
        tone, _ = lighting(g)
        row.append(np.where(g["mask"][..., None], (0.3 + 0.7 * tone)[..., None] * SKIN, 1.0))
    return np.concatenate(row, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("presets", nargs="*")
    parser.add_argument("--spec")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    pose_specs = list(args.presets)
    if args.spec:
        with open(args.spec, encoding="utf-8") as handle:
            data = json.load(handle)
        pose_specs.append(data["figures"][0].get("pose", "stand") if "figures" in data else data)
    if not pose_specs:
        pose_specs = list(poses.BODY_POSES)
    tiles = [tile(p) for p in pose_specs]
    columns = min(3, len(tiles))
    blank = np.ones_like(tiles[0])
    rows = [np.concatenate(tiles[i:i + columns] + [blank] * (columns - len(tiles[i:i + columns])), 1)
            for i in range(0, len(tiles), columns)]
    specs.save(np.concatenate(rows, 0), args.output)
    print(f"saved {args.output}: {len(tiles)} pose(s), each shown front three-quarter then side")


if __name__ == "__main__":
    main()
