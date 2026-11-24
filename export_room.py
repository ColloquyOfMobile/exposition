# -*- coding: utf-8 -*-
# export_room.py

"""Take the room's geometry out of TJ's Rhino model, for the simulation.

    py export_room.py

Needs `rhino3dm` (`py -m pip install rhino3dm`) and the model,
`CAD/Rhino/ColloquyWorkingModel2020.06.20.3dm`, which is not in git: at
182 MB GitHub refuses it, so it lives only on the machines that have been
handed it. What the simulation needs from it is a few kilobytes, and that
is what this writes, committed, to `Source code/Python/colloquy/
virtual_drivers/room.json`:

- each body's vertical axis, seen from above, in the model's own frame
  (millimetres, x east, y north, the bar's pivot at 0,0);
- what each looks like from above, in its own frame: x to its right, y
  the way it faces at its origin (a female toward the pivot, a male away
  from it) - a female's shell, her mirror and the sensor on it, the
  barn doors either side of the sensor; a male's body box, the NeoPixel
  ring on its front and the ring light on top of him; the bar's plate;
- the model's digest, so a test can say the JSON is stale without
  having the model (`pytest_tests/virtual_drivers/test_room.py`).

Outlines are the convex hull of each part's cached render mesh, thinned
to a few millimetres: a plan, not a render. Only what is unambiguous is
taken - the parts parked at the model's origin (unplaced Dynamixel
dummies, some scaled wrong) are left out by requiring a part to lie
wholly near the body it belongs to, and the males' shoulder plates and
"splodges" are left out because the model does not say whether they turn
with the male or stay with the bar.

The model names no female. Which of its females is female1, 2 and 3 is
decided by the simulation from the calibration (`virtual_drivers/
room.py`), not here.

Re-run after the model changes. The `colloquy` package is not imported:
importing it wipes `local/logs`.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "CAD" / "Rhino" / "ColloquyWorkingModel2020.06.20.3dm"
OUT = ROOT / "Source code" / "Python" / "colloquy" / "virtual_drivers" / "room.json"

# How near its own axis a part must lie, all of it, to belong to a body.
NEAR = {"female": 800.0, "male": 400.0, "bar": 800.0}
# Hull points closer than this to the line through their neighbours go.
THIN_MM = 3.0


def digest(path):
    """Of the bytes as they are: a .3dm is binary, line endings and all."""
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def millimetres_per_unit(model):
    import rhino3dm

    units = model.Settings.ModelUnitSystem
    known = {
        rhino3dm.UnitSystem.Millimeters: 1.0,
        rhino3dm.UnitSystem.Centimeters: 10.0,
        rhino3dm.UnitSystem.Meters: 1000.0,
        rhino3dm.UnitSystem.Inches: 25.4,
        rhino3dm.UnitSystem.Feet: 304.8,
    }
    if units not in known:
        sys.exit(f"the model is in {units}, which this does not convert")
    return known[units]


class Part:
    """One visible object: its layer, its box and its mesh's vertices, in mm."""

    def __init__(self, layer, box, points):
        self.layer = layer
        self.box = box  # (x0, x1, y0, y1, z0, z1)
        self.points = points  # [(x, y, z)]

    @property
    def centre(self):
        x0, x1, y0, y1, z0, z1 = self.box
        return ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)

    def lies_within(self, axis, radius):
        """Judged on the mesh, which is the surface: rhino3dm boxes a NURBS
        part by its control points, which can stand far off it - a lower
        female's shell is boxed 886 mm out from her axis, its surface 620,
        and one head knob's box runs all the way to the model's origin."""
        if self.points:
            return all(math.dist(p[:2], axis) <= radius for p in self.points)
        x0, x1, y0, y1, _, _ = self.box
        return all(
            math.dist(corner, axis) <= radius
            for corner in ((x0, y0), (x0, y1), (x1, y0), (x1, y1))
        )


def _meshes(geometry):
    import rhino3dm

    if isinstance(geometry, rhino3dm.Brep):
        for face in geometry.Faces:
            mesh = face.GetMesh(rhino3dm.MeshType.Any)
            if mesh is not None:
                yield mesh
    elif isinstance(geometry, rhino3dm.Extrusion):
        mesh = geometry.GetMesh(rhino3dm.MeshType.Any)
        if mesh is not None:
            yield mesh
    elif isinstance(geometry, rhino3dm.Mesh):
        yield geometry


def read_parts(model, scale):
    """Every visible object on a layer this uses, with its mesh."""
    wanted = ("Females", "Males", "Male ring light", "Bar plates", "armature::8020 bar")
    layers = {i: (layer.FullPath, layer.Visible) for i, layer in enumerate(model.Layers)}
    parts = []
    for item in model.Objects:
        path, visible = layers[item.Attributes.LayerIndex]
        if not visible or not path.startswith(wanted):
            continue
        geometry = item.Geometry
        try:
            box = geometry.GetBoundingBox()
        except Exception:
            continue
        points = []
        for mesh in _meshes(geometry):
            vertices = mesh.Vertices
            points.extend(
                (vertices[i].X * scale, vertices[i].Y * scale, vertices[i].Z * scale)
                for i in range(len(vertices))
            )
        low, high = box.Min, box.Max
        parts.append(
            Part(
                path,
                (low.X * scale, high.X * scale, low.Y * scale, high.Y * scale,
                 low.Z * scale, high.Z * scale),
                points,
            )
        )
    return parts


def on_layer(parts, prefix):
    return [part for part in parts if part.layer.startswith(prefix)]


def cluster(points, within):
    """Group points lying within `within` of a group's first point."""
    groups = []
    for point in points:
        for group in groups:
            if math.dist(group[0], point) <= within:
                group.append(point)
                break
        else:
            groups.append([point])
    return groups


def mean(points):
    return tuple(sum(c) / len(points) for c in zip(*points))


def heading(vector):
    """Degrees clockwise from north, seen from above, in [0, 360) to the
    hundredth: a body a hair west of north is at 0, not at 360."""
    return round(math.degrees(math.atan2(vector[0], vector[1])), 2) % 360


class Frame:
    """A body's own frame: origin on its axis, y the way it faces, x to
    its right - both as seen from above."""

    def __init__(self, axis, facing):
        length = math.hypot(*facing)
        self.axis = axis
        self.forward = (facing[0] / length, facing[1] / length)
        # Clockwise a quarter turn, seen from above: facing north, right
        # is east.
        self.right = (self.forward[1], -self.forward[0])

    def local(self, point):
        dx, dy = point[0] - self.axis[0], point[1] - self.axis[1]
        return (
            dx * self.right[0] + dy * self.right[1],
            dx * self.forward[0] + dy * self.forward[1],
        )

    def box(self, parts):
        """(x0, x1, y0, y1, z0, z1) of these parts' meshes, in this frame."""
        local = [self.local(p) + (p[2],) for part in parts for p in part.points]
        if not local:
            sys.exit(f"no mesh on {[p.layer for p in parts]}: save the model with render meshes")
        xs, ys, zs = zip(*local)
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

    def outline(self, parts):
        flat = {
            (round(x, 1), round(y, 1))
            for part in parts
            for x, y in (self.local(p) for p in part.points)
        }
        if len(flat) < 3:
            sys.exit(f"no mesh on {[p.layer for p in parts]}: save the model with render meshes")
        return [[round(x), round(y)] for x, y in thin(hull(sorted(flat)))]


def hull(points):
    """Convex hull, counter-clockwise (Andrew's monotone chain)."""

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def thin(polygon):
    """Drop points that sit within THIN_MM of the line their neighbours make."""
    points = list(polygon)
    changed = True
    while changed and len(points) > 8:
        changed = False
        for i in range(len(points)):
            a, b, c = points[i - 1], points[i], points[(i + 1) % len(points)]
            base = math.dist(a, c)
            if base == 0:
                continue
            area2 = abs((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0]))
            if area2 / base < THIN_MM:
                del points[i]
                changed = True
                break
    return points


def near(parts, axis, radius):
    return [part for part in parts if part.lies_within(axis, radius)]


def females(parts):
    """Her axis: midway between the two tall square tubes she hangs on
    (the cable comes down between them)."""
    tubes = [
        part.centre[:2]
        for part in on_layer(parts, "Females::armature::form")
        if part.box[5] - part.box[4] > 600
    ]
    found = []
    for pair in cluster(tubes, 200):
        if len(pair) != 2:
            sys.exit(f"expected two tubes per female, found {pair}")
        axis = mean(pair)
        frame = Frame(axis, (-axis[0], -axis[1]))
        mine = near(parts, axis, NEAR["female"])
        sensor = frame.box(on_layer(mine, "Females::mirror::sensor_mount"))
        mirror = frame.box(on_layer(mine, "Females::mirror::mirror surf"))
        doors = [frame.box([d]) for d in on_layer(mine, "Females::mirror::barn doors")]
        # The drawing's premise: at her origin she faces the pivot. Her
        # sensor on the line from her axis to the pivot is the model
        # saying so.
        if abs((sensor[0] + sensor[1]) / 2) > 15:
            sys.exit(f"the female at {axis} does not face the pivot: sensor {sensor}")
        found.append(
            {
                "axis": [round(axis[0], 1), round(axis[1], 1)],
                "at": heading(axis),
                "shell": frame.outline(on_layer(mine, "Females::shell")),
                "mirror": {
                    "left": round(mirror[0]), "right": round(mirror[1]),
                    "forward": round((mirror[2] + mirror[3]) / 2),
                    "height": round(mirror[5] - mirror[4]),
                },
                "sensor": {
                    "forward": round(sensor[3]),
                    "height": round((sensor[4] + sensor[5]) / 2),
                },
                "barn doors": [
                    {"left": round(d[0], 1), "right": round(d[1], 1),
                     "back": round(d[2], 1), "front": round(d[3], 1)}
                    for d in sorted(doors)
                ],
            }
        )
    return sorted(found, key=lambda female: female["at"])


def males(parts):
    """His axis: the tube he hangs from."""
    found = []
    for tube in on_layer(parts, "Males::tube::solid"):
        axis = tube.centre[:2]
        frame = Frame(axis, axis)
        mine = near(parts, axis, NEAR["male"])
        body = on_layer(mine, "Males::body")
        box = frame.box(body)
        if box[1] - box[0] < 2 * (box[3] - box[2]):
            sys.exit(f"the male at {axis} does not face out from the pivot: body {box}")
        ring = frame.box(on_layer(mine, "Males::body::box neopixel"))
        up = frame.box(on_layer(mine, "Male ring light::ring base::solid"))
        found.append(
            {
                "axis": [round(axis[0], 1), round(axis[1], 1)],
                "at": heading(axis),
                "body": frame.outline(body),
                "ring": {
                    "forward": round(ring[3]),
                    "across": round(ring[1] - ring[0]),
                    "height": round((ring[4] + ring[5]) / 2),
                },
                "up ring": {
                    "forward": round((up[2] + up[3]) / 2),
                    "across": round(up[1] - up[0]),
                },
            }
        )
    return sorted(found, key=lambda male: male["at"])


def bar(parts, toward):
    frame = Frame((0.0, 0.0), toward)
    mine = near(parts, (0.0, 0.0), NEAR["bar"])
    beam = max(
        (frame.box([p]) for p in on_layer(mine, "armature::8020 bar::extrusion")),
        key=lambda box: box[3] - box[2],
    )
    return {
        "plate": frame.outline(on_layer(mine, "Bar plates::solid")),
        "beam": [round(beam[2]), round(beam[3])],
    }


def main():
    try:
        import rhino3dm
    except ImportError:
        sys.exit("needs rhino3dm: py -m pip install rhino3dm")
    if not MODEL.is_file():
        sys.exit(f"{MODEL.relative_to(ROOT)} is not on this machine (it is not in git)")

    model = rhino3dm.File3dm.Read(str(MODEL))
    parts = read_parts(model, millimetres_per_unit(model))
    the_males = males(parts)
    record = {
        "source": MODEL.relative_to(ROOT).as_posix(),
        "source sha256": digest(MODEL),
        "units": "mm",
        "frame": (
            "seen from above: x east, y north, the bar's pivot at 0,0; a body's "
            "own outlines with x to its right and y the way it faces at its origin"
        ),
        "females": females(parts),
        "males": the_males,
        "bar": bar(parts, the_males[0]["axis"]),
    }
    if len(record["females"]) != 3 or len(record["males"]) != 2:
        sys.exit(f"expected 3 females and 2 males, found {len(record['females'])} and {len(record['males'])}")
    OUT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for kind in ("females", "males"):
        for body in record[kind]:
            print(f"  {kind[:-1]} at {body['at']:6.2f} deg, axis {body['axis']}, r {math.hypot(*body['axis']):.0f} mm")


if __name__ == "__main__":
    main()
