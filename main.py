from logging import logThreads
from xml.etree.ElementTree import ElementTree, Element
from xml.etree import ElementTree as ET
from parse import compile
from svg.path import parse_path, Path as svgpath, Move, CubicBezier, Arc, Line, Close
import numpy as np
import bezier
import matplotlib.pyplot as plt
import math
from multiprocessing import pool as mp_pool

import json
from time import sleep

no_namespace = compile("{{{namespace}}}{tag}")

def find_all(root:Element, tag:str) -> list[Element]:
    r = []
    for l in root:
        _tag = no_namespace.parse(l.tag).named["tag"]
        if _tag == tag:
            r.append(l)
        else:
            r.extend(find_all(l, tag))
    return r

def to_lines(p:svgpath) -> list[tuple[float, float]]:
    pass

class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def magnitude(self):
        return math.sqrt( math.pow(self.x,2) + math.pow(self.y,2) )

    def normal(self):
        m = self.magnitude()
        if m == 0:
            x_norm = 0.5
            y_norm = 0.5
        else:
            x_norm = self.x / m
            y_norm = self.y / m
        return Point(x_norm, y_norm)

    def rotate_n90(self):
        x = self.x
        y = self.y
        return Point(-y,x)

    def rotate_90(self):
        x = self.x
        y = self.y
        return Point(y,-x)

    @classmethod
    def from_complex(cls, cmplx: complex):
        return cls(cmplx.real, cmplx.imag)

    @classmethod
    def from_xy(cls, x, y):
        return cls(x, y)

    def __repr__(self):
        return json.dumps(self.__dict__)

    def __sub__(self, other):
        x = self.x - other.x
        y = self.y - other.y
        return Point(x,y)

    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        return Point(x,y)

    def __mul__(self, other):
        x = self.x * other
        y = self.y * other
        return Point(x,y)

class Polygon(object):
    def __init__(self):
        self.coords : list[Point] = []
        self.closed = False

    def add_point(self, p):
        if self.closed:
            return
        self.coords.append(p)

    def add_points(self, p):
        self.coords = p
        self.closed = True

    # we need a shape to work with so the polygon needs to be closed
    def to_shape(self):
        r2 = []

        if len(self.coords) == 2:
            start = self.coords[0]
            finish = self.coords[1]
            n = (finish - start).normal()*0.8
            r2.append(start + n.rotate_n90())
            r2.append(finish + n.rotate_n90())
            r2.append(finish + n.rotate_90())
            r2.append(start + n.rotate_90())
            pass
        else:
            last = self.coords[0]
            first = True
            initial = 0
            n = 0
            for r in self.coords[1:]:
                n = (r - last).normal()*0.8
                dn = n.rotate_n90()
                if first:
                    initial = last + dn
                    r2.append(initial)
                    first = False
                r2.append(r + dn)
                #r2.append(Point.from_xy(r.x + 1.0, r.y + 1.0))
                last = r
            if False:
                r2.append(last + n + n.rotate_n90() * 0.8)
                r2.append(last + n + n.rotate_90() * 0.8)

            last = self.coords[-1]
            first = True
            for r in self.coords[-2::-1]:
                n = (r - last).normal() * 0.8
                dn = n.rotate_n90()
                if first:
                    r2.append(last + dn)
                    first = False
                r2.append(r+dn)
                #r2.append(Point.from_xy(r.x + 1.0, r.y + 1.0))
                last = r
            if False:
                r2.append(last + n + n.rotate_n90() * 0.8)
                r2.append(last + n + n.rotate_90() * 0.8)

        op = Polygon()
        op.add_points(r2)
        return op

    def to_openscad(self):
        sb = "polygon(["
        for p in self.coords:
            sb += f"[{p.x:.2f},{p.y:.2f}],"
        return sb[:-1] + "]);"

def map_path(path):
    path = parse_path(path)
    this_poly = Polygon()
    for segment in path:
        match segment:
            case x if type(x) is Move:
                x: Move
                pass  # We can ignore Moves

            case x if type(x) is CubicBezier:
                x: CubicBezier
                ls = np.linspace(0.0, 1.0, int(x.length()) + 2)
                for l in ls:
                    p = Point.from_complex(x.point(l))
                    this_poly.add_point(p)

            case x if type(x) is Line:
                x: Line
                ls = np.linspace(0.0, 1.0, int(x.length()) + 2)
                for l in ls:
                    p = Point.from_complex(x.point(l))
                    this_poly.add_point(p)

            case x if type(x) is Arc:
                x: Arc
                ls = np.linspace(0.0, 1.0, int(x.length()) + 2)
                for l in ls:
                    p = Point.from_complex(x.point(l))
                    this_poly.add_point(p)

            case x if type(x) is Close:
                x: Close
                pass  # ignore
            case x:
                print(f"unexpected type {type(x)}")
    return this_poly

if __name__ == "__main__":
    print("opening the svg")
    with open("./blue wren.svg", "r") as svgf:
        print("parsing the svg")
        root: Element  = ET.parse(svgf).getroot()
        print("finding all paths")
        paths = find_all(root, "path")
        paths = [x.attrib["d"] for x in paths if x.attrib.get("d", False)]

    print("svg closed")

    """
    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    """
    print("converting paths and segments into paths")


    with mp_pool.Pool(12) as pool:
        polygons = pool.map(map_path, paths)

    print("finished parsing paths")

    for p in polygons:
        p.coords = [Point( round(x.x, 2), round(x.y,2)) for x in p.coords]
    

    for p in polygons:
        while True:
            clean = True
            t = p.coords[::]
            r = [t[0]]
            last = None
            for c in t:
                if last is None:
                    last = c
                    continue
                d = c - last
                m = d.magnitude()
                if m <= 0.3 and len(r) > 2:
                    av = (c + last) * 0.5
                    clean = False
                    r = r[:-1]
                    r.append(av)
                else:
                    r.append(c)
                last = c
            p.coords = r
            if clean:
                break

    print("opening output file, converting to 'shapes' and converting to openscad format")
    with open("scadout.scad", "w") as scf:
        for polygon in polygons:
            if len(polygon.coords) < 2:
                continue
            scf.write(polygon.to_shape().to_openscad())
            scf.write("\n")