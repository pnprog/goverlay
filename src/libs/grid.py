from collections import defaultdict
from math import pow, sqrt
from random import random

import cv2
import numpy as np


class Found(Exception):
    pass


class Grid:
    def __init__(self, dim=19):
        print(f"initializing new grid with size {19}")
        self.dim = dim
        self.dots = None
        self.all_dots = None
        self.radius = None

        print(" * generating new grid")
        space = 100 / (dim + 1)

        dots = {}
        for i in range(dim):
            for j in range(dim):
                if i in [0, dim - 1] and j in [0, dim - 1]:
                    id = f"c-{i}-{j}"
                    dot = {
                        "i": i,
                        "j": j,
                        "cx": (1 + dim // 2 + i) * space / 2,
                        "cy": (1 + dim // 2 + j) * space / 2,
                        "stroke": "red",
                    }
                    dot["cx"] += (random() - 0.5) * space * 0.001
                    dot["cy"] += (random() - 0.5) * space * 0.001
                    dots[id] = dot
        self.dots = dots

    def update_data(self, id, cx, cy):
        print("update_data")

        _, i, j = id.split("-")

        print(f"new dot {i}/{j}")
        dot = {
            "i": int(i),
            "j": int(j),
            "cx": float(cx),
            "cy": float(cy),
            "stroke": "red",
        }

        self.dots[id] = dot
        return self.recalculate_dots()

    def apply_simple_distortion(self):
        print("get_all_dots")
        grid = {}
        all_dots = {}
        for i in range(self.dim):
            for j in range(self.dim):
                id = f"c-{i}-{j}"
                if id in self.dots:
                    grid[(i, j)] = self.dots[id]
                    all_dots[id] = self.dots[id]

        new_positions = defaultdict(list)

        while 1:
            missing = 0
            for i in range(self.dim):
                for j in range(self.dim):
                    if (i, j) not in grid:
                        # let's see if it is positionned horizontally between two defined dots
                        missing += 2
                        try:
                            for ii in range(1, i + 1):
                                if (i - ii, j) in grid:
                                    for iii in range(1, self.dim - i):
                                        if (i + iii, j) in grid:
                                            # print(f"{i}/{j} in between {i-ii}/{j} and {i+iii}/{j}")
                                            ratio = ii / (ii + iii)
                                            x1, y1 = (
                                                grid[(i - ii, j)]["cx"],
                                                grid[(i - ii, j)]["cy"],
                                            )
                                            x2, y2 = (
                                                grid[(i + iii, j)]["cx"],
                                                grid[(i + iii, j)]["cy"],
                                            )
                                            distance = sqrt(
                                                pow(x1 - x2, 2) + pow(y1 - y2, 2)
                                            )
                                            u, v = (x2 - x1) / distance, (
                                                y2 - y1
                                            ) / distance
                                            x = x1 + u * ratio * distance
                                            y = y1 + v * ratio * distance
                                            new_positions[(i, j)].append(
                                                [ii + iii, x, y]
                                            )
                                            raise Found()
                        except Found:
                            missing -= 1

                        # let's see if it is positionned vertically between two defined dots
                        try:
                            for jj in range(1, j + 1):
                                if (i, j - jj) in grid:
                                    for jjj in range(1, self.dim - j):
                                        if (i, j + jjj) in grid:
                                            # calculating position here
                                            ratio = jj / (jj + jjj)
                                            x1, y1 = (
                                                grid[(i, j - jj)]["cx"],
                                                grid[(i, j - jj)]["cy"],
                                            )
                                            x2, y2 = (
                                                grid[(i, j + jjj)]["cx"],
                                                grid[(i, j + jjj)]["cy"],
                                            )
                                            distance = sqrt(
                                                pow(x1 - x2, 2) + pow(y1 - y2, 2)
                                            )
                                            u, v = (x2 - x1) / distance, (
                                                y2 - y1
                                            ) / distance
                                            x = x1 + u * ratio * distance
                                            y = y1 + v * ratio * distance
                                            new_positions[(i, j)].append(
                                                [jj + jjj, x, y]
                                            )
                                            raise Found()
                        except Found:
                            missing -= 1

            for ij, positions in new_positions.items():
                _, cx, cy = sorted(positions)[0]
                i, j = ij
                id = f"c-{i}-{j}"
                dot = {"i": i, "j": j, "cx": cx, "cy": cy, "stroke": "green"}

                grid[(i, j)] = dot
                all_dots[id] = dot

            if not missing:
                break

        for dot in all_dots.values():
            i = dot["i"]
            j = dot["j"]
            cx = dot["cx"]
            cy = dot["cy"]

            box = {}

            distances = []
            for i2, j2 in [
                [i, j - 1],
                [i + 1, j],
                [i, j + 1],
                [i - 1, j],
            ]:
                key = f"c-{i2}-{j2}"
                if key in all_dots:
                    cx2 = all_dots[key]["cx"]
                    cy2 = all_dots[key]["cy"]
                    distances.append(sqrt(pow(cx - cx2, 2) + pow(cy - cy2, 2)))
            radius = sum(distances) / len(distances)
            for label, i2, j2 in [
                ["n", 0, -1],
                ["ne", 1, -1],
                ["e", 1, 0],
                ["se", 1, 1],
                ["s", 0, 1],
                ["sw", -1, 1],
                ["w", -1, 0],
                ["nw", -1, -1],
            ]:
                cx2 = cx + i2 * radius
                cy2 = cy + j2 * radius
                box[label] = [(cx + cx2) / 2, (cy + cy2) / 2]
            dot["box"] = box
        return all_dots

    def apply_optical_distortion(self):
        objpoints = []
        imgpoints = []
        for dot in self.dots.values():
            objpoints.append(np.array([dot["i"], dot["j"], 0], np.float32))
            imgpoints.append(np.array([dot["cx"], dot["cy"]], np.float32))
        all_dots = dict(self.dots)
        if len(all_dots) < 8:
            raise Exception("Not enough points for proper calibration")
        # https://learnopencv.com/camera-calibration-using-opencv/
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            np.array([objpoints], np.float32),
            np.array([imgpoints], np.float32),
            [90, 90],
            None,
            None,
        )
        print("calibration working")
        for i in range(self.dim):
            for j in range(self.dim):
                id = f"c-{i}-{j}"
                if id not in self.dots:
                    cx, cy = cv2.projectPoints(
                        np.array([np.array([i, j, 0], np.float32)]),
                        rvecs[0],
                        tvecs[0],
                        mtx,
                        dist,
                    )[0][0][0]
                    cx = float(cx)
                    cy = float(cy)
                    dot = {"i": i, "j": j, "cx": cx, "cy": cy, "stroke": "green"}
                    all_dots[id] = dot

        for dot in all_dots.values():
            i = dot["i"]
            j = dot["j"]
            cx = dot["cx"]
            cy = dot["cy"]

            box = {}
            for label, i2, j2 in [
                ["n", i, j - 1],
                ["ne", i + 1, j - 1],
                ["e", i + 1, j],
                ["se", i + 1, j + 1],
                ["s", i, j + 1],
                ["sw", i - 1, j + 1],
                ["w", i - 1, j],
                ["nw", i - 1, j - 1],
            ]:
                cx2, cy2 = cv2.projectPoints(
                    np.array([np.array([i2, j2, 0], np.float32)]),
                    rvecs[0],
                    tvecs[0],
                    mtx,
                    dist,
                )[0][0][0]
                cx = float(cx)
                cy = float(cy)

                box[label] = [(cx + cx2) / 2, (cy + cy2) / 2]
            dot["box"] = box

        return all_dots

    def recalculate_dots(self):
        print(f"recalculate_dots")
        dim = self.dim

        try:
            all_dots = self.apply_optical_distortion()
            calibration_used = True
        except:
            all_dots = self.apply_simple_distortion()
            calibration_used = False

        found = False
        if dim == 19:
            found = False
            for i, j in [
                [3, 3],
                [9, 3],
                [3, 9],
                [9, 9],
                [15, 3],
                [3, 15],
                [9, 15],
                [15, 9],
                [15, 15],
            ]:
                id = f"c-{i}-{j}"
                if all_dots[id]["stroke"] == "green":
                    all_dots[id]["stroke"] = "yellow"
                    found = True

        if not found or calibration_used:
            if dim == 19:
                for i, j in [
                    [0, 3],
                    [3, 0],
                    [0, 15],
                    [15, 0],
                    [18, 3],
                    [3, 18],
                    [15, 15],
                    [3, 15],
                    [15, 3],
                    [15, 18],
                    [18, 15],
                    [0, 9],
                    [9, 0],
                    [18, 9],
                    [9, 18],
                ]:
                    id = f"c-{i}-{j}"
                    if all_dots[id]["stroke"] == "green":
                        all_dots[id]["stroke"] = "blue"
                        found = True
        elif found:
            all_dots = {
                id: dot for id, dot in all_dots.items() if dot["stroke"] != "green"
            }

        dot_tl = self.dots["c-0-0"]
        dot_tr = self.dots[f"c-{dim-1}-0"]
        dot_bl = self.dots[f"c-0-{dim-1}"]
        dot_br = self.dots[f"c-{dim-1}-{dim-1}"]

        self.radius = (
            min(
                [
                    sqrt(
                        pow(dot_tl["cx"] - dot_tr["cx"], 2)
                        + pow(dot_tl["cy"] - dot_tr["cy"], 2)
                    ),
                    sqrt(
                        pow(dot_tl["cx"] - dot_bl["cx"], 2)
                        + pow(dot_tl["cy"] - dot_bl["cy"], 2)
                    ),
                    sqrt(
                        pow(dot_br["cx"] - dot_tr["cx"], 2)
                        + pow(dot_br["cy"] - dot_tr["cy"], 2)
                    ),
                    sqrt(
                        pow(dot_br["cx"] - dot_bl["cx"], 2)
                        + pow(dot_br["cy"] - dot_bl["cy"], 2)
                    ),
                ]
            )
            / (dim - 1)
            / 2
            * 0.8
        )

        self.all_dots = all_dots
        response = {
            "dim": self.dim,
            "radius": self.radius,
            "dots": all_dots,
        }
        return response

    def get_dots(
        self,
    ):
        print("get_dots")
        response = {
            "dim": self.dim,
            "radius": self.radius,
            "dots": self.all_dots,
        }
        return response
