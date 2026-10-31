"""Tiny perspective renderer for a ballfield + Statcast pitch trajectories (feet, Statcast axes).

x: catcher's right (+), y: toward the mound, z: up. Home plate apex at origin.
"""
import math
import numpy as np

PLATE_Y = 17 / 12          # front of plate, where Statcast measures plate_x / plate_z
BALL_R = 0.121             # feet


def norm(v):
    return v / np.linalg.norm(v)


class Camera:
    def __init__(self, pos, target, focal=1500, cx=960, cy=540):
        self.c = np.array(pos, float)
        f = norm(np.array(target, float) - self.c)
        r = norm(np.cross(f, [0, 0, 1]))
        u = np.cross(r, f)
        self.R = np.stack([r, u, f])
        self.focal, self.cx, self.cy = focal, cx, cy

    def cam(self, P):
        return (np.asarray(P, float) - self.c) @ self.R.T   # columns: right, up, depth

    def to_screen(self, q):
        q = np.atleast_2d(q)
        return np.stack([self.cx + self.focal * q[:, 0] / q[:, 2], self.cy - self.focal * q[:, 1] / q[:, 2]], 1)

    def project(self, P):
        return self.to_screen(self.cam(P))

    def scale(self, P):
        return self.focal / self.cam(P)[..., 2]

    def poly(self, P, near=0.6):
        """Project a 3D polygon, clipping against the near plane (Sutherland-Hodgman)."""
        q = self.cam(P)
        out = []
        n = len(q)
        for i in range(n):
            a, b = q[i], q[(i + 1) % n]
            ina, inb = a[2] >= near, b[2] >= near
            if ina:
                out.append(a)
            if ina != inb:
                t = (near - a[2]) / (b[2] - a[2])
                out.append(a + t * (b - a))
        if len(out) < 3:
            return []
        return [tuple(p) for p in self.to_screen(np.array(out))]


def lerp_cam(c0, c1, x, focal0=1500, focal1=1500):
    """Interpolate camera (pos, target) pairs; x in 0..1 already eased."""
    p = [a + (b - a) * x for a, b in zip(c0[0], c1[0])]
    t = [a + (b - a) * x for a, b in zip(c0[1], c1[1])]
    return Camera(p, t, focal0 + (focal1 - focal0) * x)


def ring(cx, cy, r, n=72, z=0.0):
    return [(cx + r * math.cos(a), cy + r * math.sin(a), z) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def trajectory(k, n=90, bounce=False):
    """Statcast 9-parameter fit -> (times, points). vx0.. are at y=50 ft; solve for plate time, back out y=50 pos."""
    ay, vy0 = k["ay"], k["vy0"]
    # time from y=50 to plate front
    a, b, c = 0.5 * ay, vy0, 50 - PLATE_Y
    tp = (-b - math.sqrt(b * b - 4 * a * c)) / (2 * a)
    x0 = k["plate_x"] - k["vx0"] * tp - 0.5 * k["ax"] * tp ** 2
    z0 = k["plate_z"] - k["vz0"] * tp - 0.5 * k["az"] * tp ** 2
    # release time (y = release_pos_y > 50 -> negative t)
    c2 = 50 - k["release_pos_y"]
    tr = (-b - math.sqrt(b * b - 4 * a * c2)) / (2 * a)

    def pos(t):
        return (x0 + k["vx0"] * t + 0.5 * k["ax"] * t * t,
                50 + vy0 * t + 0.5 * ay * t * t,
                z0 + k["vz0"] * t + 0.5 * k["az"] * t * t)

    ts = list(np.linspace(tr, tp, n))
    pts = [pos(t) for t in ts]
    hit = None
    for i, p in enumerate(pts):
        if p[2] <= BALL_R:
            hit = i
            break
    if hit is not None:
        # find exact ground time, then a short damped hop toward the plate
        lo, hi = ts[hit - 1], ts[hit]
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if pos(mid)[2] > BALL_R else (lo, mid)
        tg = hi
        g = pos(tg)
        vx = k["vx0"] + k["ax"] * tg
        vy = vy0 + ay * tg
        vz = -(k["vz0"] + k["az"] * tg) * 0.32
        ts = [t for t in ts if t < tg] + [tg]
        pts = [pos(t) for t in ts[:-1]] + [g]
        if bounce:
            for s in np.linspace(0.01, 0.16, 24):
                pts.append((g[0] + vx * 0.5 * s, g[1] + vy * 0.45 * s, BALL_R + vz * s - 16.1 * s * s))
                ts.append(tg + s)
                if pts[-1][2] < BALL_R:
                    pts[-1] = (pts[-1][0], pts[-1][1], BALL_R)
                    break
        return np.array(ts), np.array(pts), len([t for t in ts if t <= tg]) - 1
    return np.array(ts), np.array(pts), None


def field_polys():
    """Static ground geometry: list of (points3d, colour key) drawn back-to-front."""
    s = 90 / math.sqrt(2)
    polys = [
        ([(-400, -60, 0), (400, -60, 0), (400, 420, 0), (-400, 420, 0)], "grass"),
        (ring(0, 60.5, 95, 120), "dirt"),
        ([(0, 4, 0), (s - 4, s, 0), (0, 2 * s - 4, 0), (-s + 4, s, 0)], "grass2"),
        (ring(0, 60.5, 9, 60), "dirt"),
        (ring(0, 0.7, 13, 60), "dirt"),
    ]
    return polys


PLATE = [(-0.708, PLATE_Y, 0.01), (0.708, PLATE_Y, 0.01), (0.708, 0.708, 0.01), (0, 0, 0.01), (-0.708, 0.708, 0.01)]
RUBBER = [(-1, 60.5, 0.02), (1, 60.5, 0.02), (1, 61.0, 0.02), (-1, 61.0, 0.02)]
