# One-take city blockout (grey-box previz) for a "Blender -> Seedance" reel.
# Builds the whole scene procedurally and renders it with Blender's Workbench (solid viewport) engine.
#   python onetake.py -- --mode stills --times 0,2,4.9 --res 640x360 --out out/stills
#   python onetake.py -- --mode anim --start 0 --end 899 --out out/frames
#   python onetake.py -- --mode blend --out out          (bakes keyframes, saves onetake.blend)
import bpy, bmesh, math, sys, os, random, bisect
from mathutils import Vector, Quaternion

A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None):
    return A[A.index(name) + 1] if name in A else default
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = arg('--out', os.path.join(HERE, 'out'))
MODE = arg('--mode', 'stills')
RX, RY = [int(v) for v in arg('--res', '1280x720').split('x')]
FPS, DUR = 30, 30.0
NF = int(FPS * DUR)
random.seed(7)
rad = math.radians

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

# ------------------------------------------------------------------ materials
def lin(c):
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
MATS = {}
def mat(name, rgb):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (lin(rgb[0]), lin(rgb[1]), lin(rgb[2]), 1.0)
        MATS[name] = m
    return MATS[name]
def grey(name, v):
    return mat(name, (v, v, v))
def texmat(name):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new('tex_' + name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(os.path.join(HERE, 'tex', name + '.png'))
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    nt.nodes.active = tex
    MATS[name] = m
    return m

ASPHALT = grey('asphalt', 0.44); SIDEWALK = grey('sidewalk', 0.64); ALLEYF = grey('alley_floor', 0.52)
PAINT = grey('paint', 0.86); YELLOWL = mat('lane_yellow', (0.85, 0.70, 0.15))
WINDOW = grey('window', 0.32); STORE = grey('storefront', 0.36); TRIM = grey('trim', 0.74)
BM = [grey('bld_white', 0.97), grey('bld_light', 0.90), grey('bld_mid', 0.82), grey('bld_dark', 0.72), grey('bld_darker', 0.62)]
MANN = grey('mannequin', 0.93); PED = grey('ped', 0.80); TREE = grey('tree', 0.82); METAL = grey('metal', 0.52)
DARK = grey('dark', 0.18); TIRE = grey('tire', 0.12); GLASS = grey('glass', 0.22)
CAB = mat('cab', (0.96, 0.78, 0.08)); TURQ = mat('turq', (0.10, 0.74, 0.72)); INTERIOR = mat('interior', (0.95, 0.93, 0.88))
CHROME = grey('chrome', 0.80); BRASS = mat('brass', (0.86, 0.66, 0.18))
GREEN = mat('dumpster_green', (0.12, 0.40, 0.26)); BLUE = mat('dumpster_blue', (0.12, 0.28, 0.62))
RED = mat('awn_red', (0.74, 0.14, 0.12)); NAVY = mat('awn_navy', (0.10, 0.14, 0.40)); AWNG = mat('awn_green', (0.12, 0.44, 0.24))
WOOD = mat('wood', (0.55, 0.40, 0.25)); CUP = grey('cup', 0.97)
CARCOL = [CAB, CAB, CAB, grey('car_grey', 0.58), grey('car_black', 0.16), grey('car_white', 0.92),
          mat('car_blue', (0.16, 0.30, 0.62)), mat('car_red', (0.62, 0.12, 0.12))]

# ------------------------------------------------------------------ mesh helpers
MESH = {}
def prim(kind, m):
    key = (kind, m.name)
    if key in MESH:
        return MESH[key]
    bm = bmesh.new()
    if kind == 'cube':
        bmesh.ops.create_cube(bm, size=1.0)
    elif kind == 'cyl':
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.5, radius2=0.5, depth=1.0)
    elif kind == 'sph':
        bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=0.5)
    elif kind == 'limb':
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=0.5)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, -0.5))
    elif kind == 'ico':
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
    me = bpy.data.meshes.new(kind + '_' + m.name)
    bm.to_mesh(me); bm.free()
    me.materials.append(m)
    if kind in ('sph', 'limb'):
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    MESH[key] = me
    return me

def obj(kind, name, loc, scale, m, rot=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, prim(kind, m))
    col.objects.link(o)
    o.location = loc; o.scale = scale; o.rotation_euler = rot
    if parent is not None:
        o.parent = parent
    return o
def box(x0, x1, y0, y1, z0, z1, m, name='box', parent=None):
    return obj('cube', name, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
               (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), m, parent=parent)
def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    col.objects.link(e); e.location = loc
    if parent is not None:
        e.parent = parent
    return e
def tube(p0, p1, d, m, parent=None, name='tube', kind='cyl'):
    p0 = Vector(p0); p1 = Vector(p1); v = p1 - p0
    o = bpy.data.objects.new(name, prim(kind, m)); col.objects.link(o)
    o.location = (p0 + p1) / 2; o.scale = (d, d, v.length)
    o.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()
    if parent is not None:
        o.parent = parent
    return o
def quads(name, rects, m):
    """rects: list of 4-point lists -> one merged mesh object."""
    bm = bmesh.new()
    for r in rects:
        bm.faces.new([bm.verts.new(p) for p in r])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    return o
def flat(x0, x1, y0, y1, z):
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]

def billboard(name, center, w, h, normal, tex, frame=True):
    n = {'+x': Vector((1, 0, 0)), '-x': Vector((-1, 0, 0)), '+y': Vector((0, 1, 0)), '-y': Vector((0, -1, 0))}[normal]
    up = Vector((0, 0, 1)); right = up.cross(n); c = Vector(center)
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    pts = [(c - right * w / 2 - up * h / 2, (0, 0)), (c + right * w / 2 - up * h / 2, (1, 0)),
           (c + right * w / 2 + up * h / 2, (1, 1)), (c - right * w / 2 + up * h / 2, (0, 1))]
    f = bm.faces.new([bm.verts.new(p) for p, _ in pts])
    for loop, (_, t) in zip(f.loops, pts):
        loop[uv].uv = t
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(texmat(tex))
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    if frame:
        b = c - n * 0.18
        ex = abs(right.x) * (w + 0.5) + abs(n.x) * 0.3; ey = abs(right.y) * (w + 0.5) + abs(n.y) * 0.3
        box(b.x - ex / 2, b.x + ex / 2, b.y - ey / 2, b.y + ey / 2, b.z - h / 2 - 0.25, b.z + h / 2 + 0.25, DARK, name + '_frame')
    return o

def windows(name, origin, u, width, z0, z1, n, m=WINDOW, cw=1.7, ch=2.1, sx=3.3, sz=3.7, off=0.07, margin=1.2):
    origin = Vector(origin); u = Vector(u); n = Vector(n)
    nx = int((width - 2 * margin + (sx - cw)) // sx); nz = int((z1 - z0 - 1.0) // sz)
    if nx < 1 or nz < 1:
        return None
    start = (width - ((nx - 1) * sx + cw)) / 2
    rects = []
    for i in range(nx):
        for j in range(nz):
            a = start + i * sx; b = z0 + 0.9 + j * sz
            base = origin + n * off
            rects.append([base + u * a + Vector((0, 0, b)), base + u * (a + cw) + Vector((0, 0, b)),
                          base + u * (a + cw) + Vector((0, 0, b + ch)), base + u * a + Vector((0, 0, b + ch))])
    return quads(name, rects, m)

G = 0.15  # sidewalk / slab height

def building(x0, x1, y0, y1, h, m, faces=(), store=True, wz0=4.2):
    box(x0, x1, y0, y1, 0, h, m, 'bld')
    for f in faces:
        if f == 'W':
            o, u, n, w = (x0, y0, 0), (0, 1, 0), (-1, 0, 0), y1 - y0
        elif f == 'E':
            o, u, n, w = (x1, y0, 0), (0, 1, 0), (1, 0, 0), y1 - y0
        elif f == 'S':
            o, u, n, w = (x0, y0, 0), (1, 0, 0), (0, -1, 0), x1 - x0
        else:
            o, u, n, w = (x0, y1, 0), (1, 0, 0), (0, 1, 0), x1 - x0
        windows('win', o, u, w, wz0, h - 1.0, n)
        if store:
            ov, uv, nv = Vector(o), Vector(u), Vector(n)
            npan = max(1, int((w - 0.9) // 4.3)); pw = (w - 0.9) / npan; panels = []
            for i in range(npan):
                a = ov + uv * (0.9 + i * pw) + nv * 0.05; b = ov + uv * (0.9 + i * pw + pw - 0.9) + nv * 0.05
                panels.append([a + Vector((0, 0, G + 0.45)), b + Vector((0, 0, G + 0.45)), b + Vector((0, 0, 3.25)), a + Vector((0, 0, 3.25))])
            quads('store', panels, STORE)
            a2 = ov + nv * 0.09; b2 = ov + uv * w + nv * 0.09
            quads('band', [[a2 + Vector((0, 0, 3.55)), b2 + Vector((0, 0, 3.55)), b2 + Vector((0, 0, 4.0)), a2 + Vector((0, 0, 4.0))]], TRIM)

# ------------------------------------------------------------------ city grid
CX = [(-214, -186), (-114, -86), (-12, 12), (72, 100), (172, 200), (272, 300), (372, 400)]
CY = [(-162, -138), (-32, -8), (98, 122), (228, 252), (358, 382), (488, 512), (618, 642)]
BX = [(-286, -214)] + [(CX[i][1], CX[i + 1][0]) for i in range(len(CX) - 1)] + [(400, 472)]
BY = [(-268, -162)] + [(CY[j][1], CY[j + 1][0]) for j in range(len(CY) - 1)] + [(642, 748)]
HERO = ((12, 72), (-8, 98))

obj('cube', 'ground', (100, 250, -0.5), (1600, 1800, 1.0), ASPHALT)

def rand_height():
    r = random.random()
    if r < 0.55:
        return random.uniform(16, 42)
    if r < 0.88:
        return random.uniform(42, 90)
    return random.uniform(90, 150)

def generic_block(bx0, bx1, by0, by1, detail):
    xm = (bx0 + bx1) / 2 + random.uniform(-5, 5)
    for xa, xb, face in ((bx0, xm, 'W'), (xm, bx1, 'E')):
        y = by0
        while y < by1 - 0.01:
            d = random.uniform(15, 32)
            if by1 - (y + d) < 13:
                d = by1 - y
            h = rand_height(); m = random.choice(BM)
            faces = [face]
            if abs(y - by0) < 0.01:
                faces.append('S')
            if abs(y + d - by1) < 0.01:
                faces.append('N')
            building(xa, xb, y, y + d, h, m, faces if detail else ())
            if h > 55 and random.random() < 0.6:
                ins = random.uniform(3, 6); eh = random.uniform(8, 36)
                box(xa + ins, xb - ins, y + ins, y + d - ins, h, h + eh, random.choice(BM), 'tier')
            elif random.random() < 0.7:
                cx = random.uniform(xa + 4, xb - 4); cy = random.uniform(y + 4, y + d - 4)
                box(cx - 2, cx + 2, cy - 1.8, cy + 1.8, h, h + random.uniform(1.5, 3.5), random.choice(BM), 'roofbox')
                if random.random() < 0.4:
                    obj('cyl', 'tank', (cx + 4 if cx + 6 < xb else cx - 4, cy, h + 2.6), (2.6, 2.6, 3.4), WOOD)
            y += d

DETAIL = {((-86, -12), (-8, 98)), ((100, 172), (-8, 98)), ((100, 172), (122, 228)), ((100, 172), (252, 358)),
          ((12, 72), (122, 228)), ((12, 72), (252, 358)), ((-86, -12), (122, 228)), ((12, 72), (-138, -32))}
for bx in BX:
    for by in BY:
        box(bx[0] - 5, bx[1] + 5, by[0] - 5, by[1] + 5, 0, G, SIDEWALK, 'slab')
        if (bx, by) == HERO:
            continue
        generic_block(bx[0], bx[1], by[0], by[1], (bx, by) in DETAIL)

# hero block -------------------------------------------------------
building(12, 42, -8, 10, 28, BM[1], ('W', 'S'))
building(12, 42, 10, 30, 46, BM[0], ('W',))
building(12, 42, 30, 52, 34, BM[2], ('W',), wz0=18)
building(12, 42, 52, 78, 58, BM[1], ('W',))
building(42, 72, -8, 20, 70, BM[3], ('E', 'S'))
building(42, 72, 20, 48, 40, BM[1], ('E',))
building(42, 72, 48, 78, 52, BM[2], ('E',))
building(12, 40, 83, 98, 36, BM[3], ('W', 'N'))
building(40, 72, 83, 98, 62, BM[1], ('E', 'N'))
# alley (y 78..83, x 12..72)
box(12, 72, 78, 83, G, G + 0.02, ALLEYF, 'alley_floor')
windows('alley_win_s1', (12, 78, 0), (1, 0, 0), 30, 5.5, 50, (0, 1, 0), sx=5.2, sz=4.4, cw=1.4, ch=1.8)
windows('alley_win_s2', (42, 78, 0), (1, 0, 0), 30, 5.5, 46, (0, 1, 0), sx=5.2, sz=4.4, cw=1.4, ch=1.8)
windows('alley_win_n1', (12, 83, 0), (1, 0, 0), 28, 5.5, 32, (0, -1, 0), sx=5.2, sz=4.4, cw=1.4, ch=1.8)
windows('alley_win_n2', (40, 83, 0), (1, 0, 0), 32, 5.5, 56, (0, -1, 0), sx=5.2, sz=4.4, cw=1.4, ch=1.8)
box(20.0, 22.4, 81.6, 82.9, G, 1.45, GREEN, 'dumpster_green'); box(19.95, 22.45, 81.55, 82.95, 1.45, 1.52, DARK, 'dumpster_lid')
box(30.0, 32.4, 78.1, 79.35, G, 1.45, BLUE, 'dumpster_blue'); box(29.95, 32.45, 78.05, 79.4, 1.45, 1.52, DARK, 'dumpster_lid2')
for x, y, s in ((24.2, 82.4, 0.8), (25.0, 82.1, 0.65), (24.7, 82.75, 0.55), (33.3, 78.6, 0.7), (46.5, 82.5, 0.75), (63.0, 78.55, 0.7), (63.8, 78.8, 0.55)):
    obj('ico', 'trashbag', (x, y, G + s * 0.4), (s, s, s * 0.85), DARK)
for x, y, sx_, sy_, sz_ in ((44.0, 82.4, 1.2, 1.0, 0.9), (44.2, 82.45, 0.8, 0.8, 0.6), (57.5, 82.5, 1.0, 0.8, 0.7)):
    box(x - sx_ / 2, x + sx_ / 2, y - sy_ / 2, y + sy_ / 2, G if sz_ > 0.65 else G + 0.9, (G if sz_ > 0.65 else G + 0.9) + sz_, WOOD, 'crate')
quads('puddle', [flat(37.2, 41.0, 79.2, 82.0, G + 0.03)], DARK)
box(52.95, 54.0, 77.9, 78.08, G, 2.35, DARK, 'backdoor'); box(52.7, 54.25, 77.85, 78.3, 2.5, 2.62, METAL, 'door_canopy')
box(15.5, 16.5, 82.92, 83.1, G, 2.3, DARK, 'backdoor2')
def fire_escape(xa, xb, wall_y, sign):
    for z in (6.2, 9.9, 13.6, 17.3):
        box(xa, xb, wall_y, wall_y + sign * 1.1, z, z + 0.1, DARK, 'fe_platform')
        box(xa, xb, wall_y + sign * 1.05, wall_y + sign * 1.1, z + 0.1, z + 1.1, DARK, 'fe_rail')
        tube((xa + 0.5, wall_y + sign * 0.6, z - 3.6), (xb - 1.0, wall_y + sign * 0.6, z), 0.09, DARK, name='fe_stair')
    tube((xa + 0.4, wall_y + sign * 0.9, 2.6), (xa + 0.4, wall_y + sign * 0.9, 6.2), 0.09, DARK, name='fe_ladder')
fire_escape(26.0, 31.0, 83.0, -1); fire_escape(56.0, 61.0, 78.0, 1)
for x, wy, s in ((18.0, 78, 1), (36.0, 83, -1), (48.0, 83, -1), (66.0, 78, 1)):
    tube((x, wy + s * 0.12, G), (x, wy + s * 0.12, 30), 0.16, METAL, name='pipe')
for x, wy, s, z in ((35.0, 78, 1, 3.2), (47.0, 78, 1, 3.4), (22.0, 83, -1, 4.0), (60.0, 83, -1, 3.3), (67.0, 83, -1, 5.0)):
    box(x, x + 1.0, min(wy, wy + s * 0.6), max(wy, wy + s * 0.6), z, z + 0.7, METAL, 'ac_unit')

# ------------------------------------------------------------------ street dressing
def lamp(x, y, toward):
    tube((x, y, G), (x, y, 7.6), 0.18, METAL, name='lamp_pole')
    tube((x, y, 7.5), (x + toward * 2.2, y, 7.9), 0.12, METAL, name='lamp_arm')
    box(x + toward * 1.7, x + toward * 2.7, y - 0.2, y + 0.2, 7.75, 7.95, TRIM, 'lamp_head')
def tree(x, y, s=1.0):
    tube((x, y, G), (x, y, 3.6 * s), 0.3, METAL, name='tree_trunk')
    obj('ico', 'tree_crown', (x, y, 5.2 * s), (4.2 * s, 4.2 * s, 3.8 * s), TREE)
    obj('ico', 'tree_crown2', (x + 0.8 * s, y - 0.6 * s, 6.6 * s), (2.8 * s, 2.8 * s, 2.6 * s), TREE)
def ped(x, y, z=G, s=1.0):
    r = empty('ped', (x, y, z))
    obj('sph', 'ped_body', (0, 0, 0.82 * s), (0.44 * s, 0.32 * s, 1.5 * s), PED, parent=r)
    obj('sph', 'ped_head', (0, 0, 1.62 * s), (0.22 * s, 0.24 * s, 0.26 * s), PED, parent=r)
    return r
def traffic_light(x, y, ax, ay):
    tube((x, y, G), (x, y, 6.8), 0.2, METAL, name='tl_pole')
    tube((x, y, 6.6), (x + ax, y + ay, 6.6), 0.14, METAL, name='tl_arm')
    box(x + ax - 0.22, x + ax + 0.22, y + ay - 0.22, y + ay + 0.22, 5.5, 6.6, CAB, 'tl_signal')

CARMESH = {}
def car_mesh(m, taxi=False):
    key = (m.name, taxi)
    if key in CARMESH:
        return CARMESH[key]
    bm = bmesh.new()
    def add(sx, sy, sz, cx, cy, cz, mi):
        before = set(bm.faces)
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r['verts'])
        bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=r['verts'])
        for f in set(bm.faces) - before:
            f.material_index = mi
    add(1.84, 4.6, 0.62, 0, 0, 0.58, 0)
    add(1.6, 2.3, 0.52, 0, -0.25, 1.14, 1)
    add(1.5, 2.0, 0.06, 0, -0.25, 1.43, 0)
    for sx_ in (-0.86, 0.86):
        for sy_ in (-1.45, 1.45):
            add(0.24, 0.68, 0.68, sx_, sy_, 0.34, 2)
    if taxi:
        add(0.7, 0.28, 0.18, 0, -0.2, 1.55, 3)
    me = bpy.data.meshes.new('car_' + m.name); bm.to_mesh(me); bm.free()
    for mm in (m, GLASS, TIRE, PAINT):
        me.materials.append(mm)
    CARMESH[key] = me
    return me
def car(x, y, heading=0.0, m=None):
    m = m or random.choice(CARCOL)
    o = bpy.data.objects.new('car', car_mesh(m, m is CAB)); col.objects.link(o)
    o.location = (x, y, 0); o.rotation_euler = (0, 0, heading)
    return o

# road paint: lane dashes, crosswalks
dash, stripes, yellow = [], [], []
def in_cross(y):
    return any(c[0] - 1 < y < c[1] + 1 for c in CY)
for (x0, x1) in CX:
    r0, r1 = x0 + 5, x1 - 5
    if (x0, x1) == (-12, 12):
        for seg in [(BY[j][0] - 4, BY[j][1] + 4) for j in range(len(BY))]:
            yellow += [flat(-0.28, -0.12, seg[0], seg[1], 0.02), flat(0.12, 0.28, seg[0], seg[1], 0.02)]
        lanes_x = (-3.5, 3.5)
    else:
        lanes_x = [r0 + 4.5 * k for k in (1, 2, 3)]
    for lx in lanes_x:
        y = -260
        while y < 740:
            if not in_cross(y) and not in_cross(y + 3):
                dash.append(flat(lx - 0.08, lx + 0.08, y, y + 3, 0.02))
            y += 9
for (y0, y1) in CY:
    y = y0 + 12
    x = -280
    while x < 470:
        if not any(c[0] - 1 < x < c[1] + 1 for c in CX) and not any(c[0] - 1 < x + 3 < c[1] + 1 for c in CX):
            dash.append(flat(x, x + 3, y - 0.08, y + 0.08, 0.02))
        x += 9
for (x0, x1) in CX:
    for (y0, y1) in CY:
        if not (-130 < (x0 + x1) / 2 < 310 and -40 < (y0 + y1) / 2 < 520):
            continue
        x = x0 + 5.5
        while x < x1 - 5.9:
            stripes.append(flat(x, x + 0.6, y0 + 0.9, y0 + 3.9, 0.02)); stripes.append(flat(x, x + 0.6, y1 - 3.9, y1 - 0.9, 0.02))
            x += 1.2
        y = y0 + 5.5
        while y < y1 - 5.9:
            stripes.append(flat(x0 + 0.9, x0 + 3.9, y, y + 0.6, 0.02)); stripes.append(flat(x1 - 3.9, x1 - 0.9, y, y + 0.6, 0.02))
            y += 1.2
        traffic_light(x0 + 4.2, y0 + 4.2, 6.5, 0); traffic_light(x1 - 4.2, y1 - 4.2, -6.5, 0)
        traffic_light(x1 - 4.2, y0 + 4.2, 0, 5.5); traffic_light(x0 + 4.2, y1 - 4.2, 0, -5.5)
quads('lane_dashes', dash, PAINT); quads('crosswalks', stripes, PAINT); quads('center_lines', yellow, YELLOWL)

# Main St east sidewalk (camera run, x 7..12, y 0..77)
for y in (6, 34, 62, 92):
    lamp(7.55, y, -1)
for y in (-2, 30, 64, 96):
    lamp(-7.55, y, 1)
tree(7.9, 18); tree(7.9, 50, 0.9); tree(-8.0, 12); tree(-8.0, 44, 1.1); tree(-8.0, 78)
obj('cyl', 'hydrant', (7.6, 26, G + 0.4), (0.3, 0.3, 0.8), RED); obj('sph', 'hydrant_top', (7.6, 26, G + 0.82), (0.3, 0.3, 0.26), RED)
box(7.3, 7.9, 40.6, 41.4, G, G + 1.25, BLUE, 'mailbox'); obj('cyl', 'trashcan', (7.6, 57, G + 0.5), (0.6, 0.6, 1.0), METAL)
box(7.35, 7.85, 11.6, 12.1, G, G + 1.0, RED, 'newsbox'); box(7.35, 7.85, 12.3, 12.8, G, G + 1.0, BLUE, 'newsbox2')
for y0, y1, m in ((12, 20, RED), (54, 61, AWNG), (64, 72, NAVY)):
    o = box(10.5, 12.0, y0, y1, 3.0, 3.15, m, 'awning'); o.rotation_euler = (0, rad(-14), 0)
for y0, y1, m in ((2, 9, NAVY), (48, 56, RED)):
    o = box(-12.0, -10.5, y0, y1, 3.0, 3.15, m, 'awning_w'); o.rotation_euler = (0, rad(14), 0)
tube((11.2, 23.7, G), (11.2, 24.0, G + 1.0), 0.06, WOOD, name='aframe'); box(11.0, 11.4, 23.7, 24.3, G + 0.1, G + 1.0, PAINT, 'aframe_sign')
for y in (57.0, 59.2):
    obj('cyl', 'cafe_table', (11.2, y, G + 0.72), (0.7, 0.7, 0.05), METAL); tube((11.2, y, G), (11.2, y, G + 0.72), 0.08, METAL, name='table_leg')
billboard('bb_coffee', (11.8, 39.5, 11.5), 13, 6.5, '-x', 'coffee')
billboard('bb_deli_blade', (11.3, 27.0, 6.6), 0.01, 0.01, '-x', 'deli', frame=False)
box(10.3, 11.9, 26.85, 27.15, 4.6, 8.6, RED, 'deli_blade_body')
billboard('bb_deli_s', (11.1, 26.84, 6.6), 1.5, 3.8, '-y', 'deli', frame=False); billboard('bb_deli_n', (11.1, 27.16, 6.6), 1.5, 3.8, '+y', 'deli', frame=False)
billboard('bb_jazz', (11.93, 68.0, 2.3), 2.4, 3.2, '-x', 'jazz', frame=False)
billboard('bb_soda', (-11.8, 30, 13), 16, 8, '+x', 'soda')
billboard('bb_shapes', (-11.8, 62, 9), 12, 6, '+x', 'shapes')
billboard('bb_minute', (11.8, 60, 14), 6, 8, '-x', 'minute')
billboard('bb_sunny_top', (-30, 70.5, 40), 18, 9, '-y', 'sunny')
peds = [ped(11.0, 14.5), ped(10.9, 60.2), ped(11.3, 58.3), ped(-9.5, 22), ped(-10.2, 23), ped(-9.0, 52), ped(-9.8, 70), ped(10.6, 90)]
for y, m in ((3.5, CARCOL[3]), (10, CAB), (31, CARCOL[4]), (44, CARCOL[5]), (66, CARCOL[6])):
    car(5.3, y, 0, m)
for y, m in ((-4, CARCOL[5]), (8, CARCOL[7]), (26, CAB), (39, CARCOL[3]), (58, CARCOL[4]), (84, CAB)):
    car(-5.3, y, math.pi, m)

# Avenue B (x 72..100, road 77..95), one-way north
AVB = (79.25, 83.75, 88.25, 92.75)
for y in range(-4, 360, 26):
    if not in_cross(y):
        lamp(76.4, y, 1); lamp(95.6, y + 13, -1)
for y in (40, 68, 132, 160, 190, 262, 300):
    tree(75.6, y, 0.9)
for y in (20, 52, 142, 176, 206, 280, 330):
    tree(96.4, y)
billboard('bb_pizza', (72.2 + 0.0, 134, 15), 16, 8, '+x', 'pizza')
billboard('bb_open24', (99.8, 160, 18), 18, 9, '-x', 'open24')
billboard('bb_taxi', (99.8, 60, 12), 14, 7, '-x', 'taxi')
billboard('bb_sunny', (72.2, 190, 22), 16, 8, '+x', 'sunny')
billboard('bb_soda2', (99.8, 205, 12), 12, 6, '-x', 'soda')
billboard('bb_coffee2', (72.2, 36, 14), 12, 6, '+x', 'coffee')
billboard('bb_minute_roof', (56, 150, 60), 14, 18, '+y', 'minute')
billboard('bb_shapes2', (86, 121.6, 9), 0.01, 0.01, '-y', 'shapes', frame=False)
for y0, y1, m in ((126, 134, RED), (144, 152, NAVY), (170, 178, AWNG), (30, 38, RED), (58, 66, NAVY)):
    o = box(72.0, 73.5, y0, y1, 3.0, 3.15, m, 'awning_b'); o.rotation_euler = (0, rad(14), 0)
for y0, y1, m in ((128, 137, AWNG), (150, 158, RED), (186, 194, NAVY), (44, 52, AWNG)):
    o = box(98.5, 100.0, y0, y1, 3.0, 3.15, m, 'awning_e'); o.rotation_euler = (0, rad(-14), 0)
for x, y in ((74.5, 88), (74.0, 91), (73.6, 96.5), (74.8, 97.5), (97.5, 99), (98.2, 97.2), (74.2, 124), (75.0, 126.5), (97.3, 126),
             (98.0, 141), (74.3, 150), (97.6, 166), (74.6, 181), (98.1, 196), (74.0, 61), (97.8, 72), (74.4, 212), (97.4, 222)):
    peds.append(ped(x, y))
box(77.4, 80.4, 52, 64, 0.35, 3.3, grey('bus', 0.93), 'bus'); box(77.38, 80.42, 52.4, 63.6, 1.5, 2.6, GLASS, 'bus_glass')
# stopped cross traffic at the y=110 intersection
for x, m in ((63, CAB), (56, CARCOL[4]), (48, CARCOL[5])):
    car(x, 106.5, -math.pi / 2, m)
for x, m in ((106, CARCOL[3]), (113, CAB), (121, CARCOL[6])):
    car(x, 113.5, math.pi / 2, m)

# scattered static traffic everywhere else (aerial read)
for (x0, x1) in CX:
    r0 = x0 + 5
    hero_b = (x0, x1) == (72, 100); main = (x0, x1) == (-12, 12)
    lanes = (-5.3, -1.75, 1.75, 5.3) if main else [r0 + 2.25 + 4.5 * k for k in range(4)]
    for li, lx in enumerate(lanes):
        y = -250 + random.uniform(0, 20)
        while y < 730:
            skip = in_cross(y - 3) or in_cross(y + 3)
            if main and -12 < y < 100:
                skip = True
            if hero_b and 40 < y < 330:
                skip = True
            if not skip:
                car(lx, y, math.pi if (main and li < 2) else 0)
            y += random.uniform(9, 42)
for (y0, y1) in CY:
    for li, ly in enumerate((y0 + 8.5, y1 - 8.5)):
        x = -270 + random.uniform(0, 20)
        while x < 460:
            near = (95 < y0 + 12 < 125) and (40 < x < 130)
            if not any(c[0] - 4 < x < c[1] + 4 for c in CX) and not near:
                car(x, ly, -math.pi / 2 if li == 0 else math.pi / 2)
            x += random.uniform(10, 45)

# ------------------------------------------------------------------ cast proxies
def mannequin(name, m=MANN, h=1.75):
    root = empty(name); s = h / 1.75; P = {}
    P['pelvis'] = obj('sph', name + '_pelvis', (0, 0, 0.98 * s), (0.42 * s, 0.30 * s, 0.40 * s), m, parent=root)
    P['torso'] = obj('sph', name + '_torso', (0, 0, 1.27 * s), (0.50 * s, 0.32 * s, 0.68 * s), m, parent=root)
    P['head'] = obj('sph', name + '_head', (0, 0, 1.64 * s), (0.21 * s, 0.23 * s, 0.26 * s), m, parent=root)
    for side, sx in (('L', -1), ('R', 1)):
        P['leg' + side] = obj('limb', name + '_leg' + side, (sx * 0.10 * s, 0, 0.98 * s), (0.21 * s, 0.21 * s, 0.98 * s), m, parent=root)
        P['arm' + side] = obj('limb', name + '_arm' + side, (sx * 0.29 * s, 0, 1.50 * s), (0.14 * s, 0.14 * s, 0.68 * s), m, parent=root)
    return root, P

# 1. woman (walks south along the sidewalk toward camera)
woman, WP = mannequin('woman')
obj('sph', 'woman_hair', (0, -0.06, 1.66), (0.40, 0.38, 0.40), MANN, parent=woman)
WP['armR'].rotation_euler = (rad(62), 0, 0)
obj('cyl', 'woman_cup', (0.29, 0.62, 1.20), (0.085, 0.085, 0.13), CUP, parent=woman)
woman.rotation_euler = (0, 0, math.pi)
def woman_y(t):
    return 46.0 - 1.4 * t
WOMAN_X = 10.1

# 2. saxophonist at the alley mouth
sax, SP = mannequin('sax', h=1.86)
sax.location = (10.2, 75.0, G); sax.rotation_euler = (0, 0, rad(150))
SP['armL'].rotation_euler = (rad(48), 0, rad(-20)); SP['armR'].rotation_euler = (rad(58), 0, rad(22))
tube((0.0, 0.18, 1.62), (0.05, 0.30, 1.05), 0.07, BRASS, parent=sax, name='sax_body')
tube((0.05, 0.30, 1.05), (0.05, 0.48, 0.98), 0.09, BRASS, parent=sax, name='sax_bow')
o = tube((0.05, 0.48, 0.98), (0.05, 0.56, 1.22), 0.2, BRASS, parent=sax, name='sax_bell')
obj('sph', 'sax_beanie', (0, 0, 1.86), (0.25, 0.26, 0.16), BRASS, parent=sax)

# 3. dalmatian (alley)
dog = empty('dog'); dog.scale = (1.2, 1.2, 1.2); DP = {}
obj('sph', 'dog_body', (0, 0, 0), (0.30, 0.86, 0.34), MANN, parent=dog)
obj('sph', 'dog_chest', (0, 0.22, 0.02), (0.32, 0.42, 0.38), MANN, parent=dog)
obj('sph', 'dog_head', (0, 0.52, 0.20), (0.21, 0.30, 0.22), MANN, parent=dog)
obj('sph', 'dog_snout', (0, 0.70, 0.15), (0.12, 0.22, 0.12), MANN, parent=dog)
for sx in (-1, 1):
    obj('sph', 'dog_ear', (sx * 0.10, 0.46, 0.29), (0.07, 0.14, 0.16), DARK, parent=dog)
tube((0, -0.40, 0.08), (0, -0.74, 0.30), 0.06, MANN, parent=dog, name='dog_tail')
for nm, (lx, ly) in {'FL': (-0.11, 0.28), 'FR': (0.11, 0.28), 'BL': (-0.11, -0.28), 'BR': (0.11, -0.28)}.items():
    DP[nm] = obj('limb', 'dog_leg' + nm, (lx, ly, -0.04), (0.09, 0.09, 0.43), MANN, parent=dog)
for (px, py, pz, ps) in ((0.13, 0.08, 0.10, 0.11), (-0.12, -0.2, 0.11, 0.13), (0.14, -0.30, 0.03, 0.10), (-0.14, 0.26, 0.06, 0.10),
                         (0.02, -0.05, 0.165, 0.12), (0.05, 0.36, 0.20, 0.08), (-0.06, -0.33, 0.14, 0.09)):
    obj('sph', 'dog_spot', (px, py, pz), (ps, ps, ps * 0.5), DARK, parent=dog)
DOG_T0, DOG_T1, DOG_X0, DOG_X1 = 11.15, 12.25, 36.0, 30.8
def dog_state(t):
    if t < DOG_T0:
        return Vector((DOG_X0 + 7.8 * (DOG_T0 - t), 80.55, G + 0.56 + 0.05 * abs(math.sin(t * 20)))), 0.0, None
    if t < DOG_T1:
        s = (t - DOG_T0) / (DOG_T1 - DOG_T0)
        return Vector((DOG_X0 + (DOG_X1 - DOG_X0) * s, 80.55, G + 0.56 + 0.15 + 1.5 * 4 * s * (1 - s))), rad(28 - 52 * s), s
    return Vector((DOG_X1 - 7.8 * (t - DOG_T1), 80.55, G + 0.56 + 0.05 * abs(math.sin(t * 20)))), 0.0, None

# 4. chef on a break by the back door
chef, CP = mannequin('chef', h=1.78)
chef.location = (52.2, 78.52, G); chef.rotation_euler = (rad(-5), 0, rad(-25))
CP['armR'].rotation_euler = (rad(78), 0, rad(18)); CP['armL'].rotation_euler = (rad(20), 0, rad(-30))
box(0.16, 0.24, 0.40, 0.44, 1.52, 1.68, DARK, 'chef_phone', parent=chef)
box(-0.2, 0.2, 0.13, 0.17, 0.6, 1.36, grey('apron', 0.62), 'chef_apron', parent=chef)

# 5 + 6. driver in the turquoise convertible
carroot = empty('convertible')
def cb(x0, x1, y0, y1, z0, z1, m, n='conv'):
    return box(x0, x1, y0, y1, z0, z1, m, n, parent=carroot)
cb(-0.98, 0.98, -2.7, 2.7, 0.28, 0.55, TURQ); cb(-0.98, 0.98, 1.05, 2.7, 0.55, 0.98, TURQ, 'hood'); cb(-0.98, 0.98, -2.7, -1.35, 0.55, 0.95, TURQ, 'trunk')
cb(-0.98, -0.86, -1.35, 1.05, 0.55, 0.95, TURQ, 'doorL'); cb(0.86, 0.98, -1.35, 1.05, 0.55, 0.95, TURQ, 'doorR')
cb(-0.86, 0.86, 0.78, 1.05, 0.55, 1.0, INTERIOR, 'dash'); cb(-0.86, 0.86, -0.42, 0.38, 0.55, 0.70, INTERIOR, 'seat_f')
cb(-0.86, 0.86, -0.54, -0.36, 0.55, 1.10, INTERIOR, 'seatback_f'); cb(-0.86, 0.86, -1.3, -0.75, 0.55, 0.70, INTERIOR, 'seat_r')
cb(-0.86, 0.86, -1.36, -1.2, 0.55, 1.05, INTERIOR, 'seatback_r')
cb(-1.02, 1.02, 2.7, 2.84, 0.34, 0.56, CHROME, 'bumper_f'); cb(-1.02, 1.02, -2.84, -2.7, 0.34, 0.56, CHROME, 'bumper_r')
cb(-0.99, -0.8, -2.72, -2.0, 0.95, 1.08, TURQ, 'finL'); cb(0.8, 0.99, -2.72, -2.0, 0.95, 1.08, TURQ, 'finR')
for a, b_ in (((-0.9, 1.05, 0.98), (-0.86, 0.82, 1.42)), ((0.9, 1.05, 0.98), (0.86, 0.82, 1.42)), ((-0.86, 0.82, 1.42), (0.86, 0.82, 1.42))):
    tube(a, b_, 0.05, CHROME, parent=carroot, name='windshield_frame')
sw = obj('cyl', 'steering', (-0.45, 0.64, 1.02), (0.40, 0.40, 0.035), DARK, rot=(rad(68), 0, 0), parent=carroot)
tube((-0.45, 0.66, 1.0), (-0.45, 0.85, 0.9), 0.07, DARK, parent=carroot, name='steer_col')
for sx in (-0.9, 0.9):
    for sy in (-1.7, 1.7):
        obj('cyl', 'wheel', (sx, sy, 0.34), (0.68, 0.68, 0.24), TIRE, rot=(0, rad(90), 0), parent=carroot)
        obj('cyl', 'hub', (sx * 1.1, sy, 0.34), (0.36, 0.36, 0.08), CHROME, rot=(0, rad(90), 0), parent=carroot)
DRV = Vector((-0.45, -0.12, 0))
obj('sph', 'driver_pelvis', DRV + Vector((0, 0.02, 0.82)), (0.40, 0.34, 0.30), MANN, parent=carroot)
obj('sph', 'driver_torso', DRV + Vector((0, -0.04, 1.08)), (0.46, 0.30, 0.62), MANN, parent=carroot)
drv_head = obj('sph', 'driver_head', DRV + Vector((0, 0.0, 1.42)), (0.22, 0.24, 0.27), MANN, parent=carroot)
obj('sph', 'driver_beard', DRV + Vector((0, 0.10, 1.31)), (0.20, 0.16, 0.20), MANN, parent=carroot)
for sx in (-1, 1):
    tube(DRV + Vector((sx * 0.22, 0.0, 1.24)), DRV + Vector((sx * 0.26, 0.42, 1.02)), 0.11, MANN, parent=carroot, name='driver_uarm', kind='sph')
    tube(DRV + Vector((sx * 0.26, 0.42, 1.02)), Vector((-0.45 + sx * 0.17, 0.62, 1.06)), 0.10, MANN, parent=carroot, name='driver_farm', kind='sph')
    tube(DRV + Vector((sx * 0.11, 0.05, 0.80)), DRV + Vector((sx * 0.14, 0.62, 0.82)), 0.16, MANN, parent=carroot, name='driver_thigh', kind='sph')
CAR_X = 83.75
def car_y(t):
    return 80.5 + 11.0 * (t - 17.2)

# moving traffic: (object, x, y at t=0, speed)
MOVERS = []
def mover(x, y_at, t_at, v, m=None, heading=0.0):
    o = car(x, 0, heading, m); MOVERS.append((o, x, y_at - v * t_at, v)); return o
mover(1.75, 6, 0, 8.6, CAB); mover(1.75, -22, 0, 9.4, CARCOL[4]); mover(-1.75, 70, 0, -8.0, CAB, math.pi); mover(-1.75, 112, 0, -8.8, CARCOL[5], math.pi)
mover(1.75, -55, 0, 9.0, CARCOL[6]); mover(-1.75, 150, 0, -8.4, CAB, math.pi)
mover(AVB[2], 104, 18.5, 8.0, CAB); mover(AVB[0], 121, 18.5, 7.4, CAB); mover(AVB[3], 136, 18.5, 7.0, CARCOL[5]); mover(AVB[2], 139, 18.5, 8.2, CARCOL[4])
mover(AVB[0], 150, 18.5, 7.8, CARCOL[3]); mover(AVB[3], 166, 18.5, 7.6, CAB); mover(AVB[2], 171, 18.5, 8.6, CAB); mover(AVB[0], 186, 18.5, 8.0, CARCOL[7])
mover(AVB[1], 152, 18.5, 11.0, CAB); mover(AVB[3], 204, 18.5, 8.2, CARCOL[6]); mover(AVB[2], 214, 18.5, 9.0, CAB); mover(AVB[0], 226, 18.5, 8.5, CAB)
mover(AVB[1], 196, 18.5, 11.0, CARCOL[5]); mover(AVB[3], 252, 18.5, 8.8, CAB); mover(AVB[2], 268, 18.5, 9.2, CARCOL[3]); mover(AVB[0], 282, 18.5, 8.9, CAB)
mover(AVB[1], 250, 18.5, 11.0, CAB); mover(AVB[0], 84, 18.5, 7.0, CARCOL[4]); mover(AVB[3], 96, 18.5, 7.2, CAB); mover(AVB[2], 70, 18.5, 8.4, CARCOL[6])
truck = empty('truck'); box(-1.2, 1.2, -4.2, 2.0, 0.5, 3.4, grey('truck_box', 0.94), 'truck_box', parent=truck); box(-1.1, 1.1, 2.0, 3.8, 0.4, 2.3, CARCOL[6], 'truck_cab', parent=truck)
MOVERS.append((truck, AVB[3], 118 - 6.8 * 18.5, 6.8))
WALKERS = [(peds[0], Vector((11.0, 14.5, G)), Vector((0, 1.2, 0))), (peds[3], Vector((-9.5, 22, G)), Vector((0, -1.1, 0))),
           (peds[8], Vector((74.5, 88, G)), Vector((0, 1.2, 0))), (peds[14], Vector((74.2, 124, G)), Vector((0, -1.2, 0)))]

# ------------------------------------------------------------------ camera path
def smooth(a, b, t):
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)
def bump(t, a, b, c, d):
    return smooth(a, b, t) * (1 - smooth(c, d, t))
def carp(t, x, y, z):
    return (t, Vector((CAR_X + x, car_y(t) + y, z)))
KEYS = [(t, Vector(p)) for t, p in [
    (-0.6, (9.5, -5.2, 0.47)), (0.0, (9.5, 0.0, 0.47)), (1.2, (9.4, 10.4, 0.45)), (2.4, (9.2, 20.8, 0.45)),
    (3.3, (8.9, 28.6, 0.44)), (4.1, (8.7, 34.4, 0.42)), (4.9, (8.75, 39.1, 0.46)), (5.6, (9.15, 44.4, 0.78)),
    (6.4, (9.4, 52.6, 1.2)), (7.2, (9.2, 61.8, 1.5)), (7.9, (8.95, 68.9, 1.6)), (8.5, (9.0, 74.0, 1.55)),
    (9.0, (9.7, 78.3, 1.3)), (9.5, (13.0, 80.4, 0.92)),
    (10.2, (19.8, 80.6, 0.55)), (10.9, (26.6, 80.45, 0.48)), (11.5, (30.6, 80.5, 0.47)), (12.2, (32.6, 80.5, 0.5)),
    (12.9, (37.0, 80.6, 0.72)), (13.6, (43.5, 80.8, 1.2)), (14.2, (48.8, 81.0, 1.55)), (14.8, (53.4, 81.1, 1.6)),
    (15.5, (59.2, 80.7, 1.3)), (16.2, (65.2, 80.5, 0.9)), (17.0, (71.6, 80.5, 0.72)), (17.6, (76.3, 81.6, 0.6)), (18.2, (80.6, 85.8, 0.45))]]
KEYS += [carp(18.9, -0.6, -7.4, 0.42), carp(20.0, 0.0, -6.2, 0.42), carp(21.0, 0.0, -4.4, 0.5), carp(21.7, 0.15, -3.2, 1.05),
         carp(22.3, 0.35, -1.85, 1.58), carp(22.9, 0.5, -0.72, 1.42), carp(23.5, 0.32, 0.22, 1.34), carp(24.1, 0.4, 0.55, 1.66),
         carp(24.6, 0.2, 1.4, 1.9), carp(25.1, 0.0, 2.9, 1.46), carp(25.6, 0.0, 5.2, 1.75)]
KEYS += [(t, Vector(p)) for t, p in [(26.5, (84.3, 191.0, 9.0)), (27.5, (85.0, 204.0, 31.0)), (28.5, (86.0, 215.0, 70.0)),
                                      (30.0, (86.5, 229.0, 135.0)), (30.7, (86.6, 235.0, 165.0))]]
KT = [k[0] for k in KEYS]
def tangent(k):
    n = len(KEYS)
    if k == 0:
        return (KEYS[1][1] - KEYS[0][1]) / (KEYS[1][0] - KEYS[0][0])
    if k == n - 1:
        return (KEYS[-1][1] - KEYS[-2][1]) / (KEYS[-1][0] - KEYS[-2][0])
    ta, pa = KEYS[k - 1]; tb, pb = KEYS[k]; tc, pc = KEYS[k + 1]
    d1 = (pb - pa) / (tb - ta); d2 = (pc - pb) / (tc - tb)
    return (d1 * (tc - tb) + d2 * (tb - ta)) / (tc - ta)
TAN = [tangent(k) for k in range(len(KEYS))]
def cam_pos(t):
    t = min(max(t, KT[0]), KT[-1] - 1e-6)
    i = max(0, min(len(KEYS) - 2, bisect.bisect_right(KT, t) - 1))
    t0, p0 = KEYS[i]; t1, p1 = KEYS[i + 1]; h = t1 - t0; s = (t - t0) / h
    return ((2 * s ** 3 - 3 * s ** 2 + 1) * p0 + (s ** 3 - 2 * s ** 2 + s) * h * TAN[i]
            + (-2 * s ** 3 + 3 * s ** 2) * p1 + (s ** 3 - s ** 2) * h * TAN[i + 1])

ROLL = [(0, 0), (2.6, 0), (3.9, -7), (4.9, -13), (5.8, 0), (7.4, 5), (8.8, -13), (10.0, 0), (11.3, 4), (12.0, 9), (12.7, 0),
        (14.5, -6), (15.6, 0), (17.3, 9), (18.3, 15), (19.6, 0), (22.0, 0), (23.5, 7), (24.7, 0), (30.1, 0)]
def roll_at(t):
    for (ta, ra), (tb, rb) in zip(ROLL, ROLL[1:]):
        if ta <= t <= tb:
            return ra + (rb - ra) * smooth(ta, tb, t)
    return 0.0

def cam_state(t):
    P = cam_pos(t)
    f = (cam_pos(t + 0.5) - P)
    f = f.normalized() if f.length > 1e-6 else Vector((0, 1, 0))
    acc = f.copy()
    def track(target, w):
        nonlocal acc
        if w < 1e-4:
            return
        d = (Vector(target) - P).normalized(); k = d.dot(f)
        if k < 0.12:
            d = (d + f * (0.12 - k)).normalized()
        acc += d * w
    W = 8.0
    track((WOMAN_X, woman_y(t), G + 1.55), W * bump(t, 2.3, 3.3, 4.8, 5.5))
    track((10.2, 75.0, G + 1.6), W * bump(t, 6.0, 7.0, 8.45, 9.0))
    dpos, _, _ = dog_state(t)
    track(dpos + Vector((0, 0, 0.05)), W * bump(t, 10.1, 10.9, 12.02, 12.3))
    track((52.2, 78.6, G + 1.5), W * bump(t, 13.0, 13.8, 14.6, 15.2))
    cpos = Vector((CAR_X, car_y(t), 0))
    track(cpos + Vector((0, 0, 0.8)), W * bump(t, 17.5, 18.3, 21.5, 22.3))
    track(cpos + DRV + Vector((0, 0.05, 1.38)), W * bump(t, 22.1, 22.8, 23.95, 24.6))
    d = acc.normalized()
    g = smooth(25.7, 29.7, t)
    if t > 25.2:
        pitch = rad(-3 - 79 * (g ** 0.85)); yaw = rad(24 * g)
        fin = Vector((math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
        d = d.lerp(fin, smooth(25.2, 26.3, t)).normalized()
    q = d.to_track_quat('-Z', 'Y') @ Quaternion((0, 0, 1), rad(roll_at(t)))
    return P, q

camd = bpy.data.cameras.new('cam'); camd.lens = 15; camd.sensor_width = 36; camd.clip_start = 0.04; camd.clip_end = 4000
cam = bpy.data.objects.new('camera', camd); col.objects.link(cam); scene.camera = cam
cam.rotation_mode = 'QUATERNION'

ANIM = [cam, woman, dog, carroot, sax, drv_head] + [WP[k] for k in ('legL', 'legR', 'armL')] + list(DP.values()) \
       + [m[0] for m in MOVERS] + [w[0] for w in WALKERS]
_prevq = [None]
def apply(t):
    P, q = cam_state(t)
    if _prevq[0] is not None and q.dot(_prevq[0]) < 0:
        q.negate()
    _prevq[0] = q.copy()
    cam.location = P; cam.rotation_quaternion = q
    ph = 2 * math.pi * 0.95 * t
    woman.location = (WOMAN_X, woman_y(t), G + 0.02 * abs(math.sin(ph)))
    WP['legL'].rotation_euler = (rad(26) * math.sin(ph), 0, 0); WP['legR'].rotation_euler = (-rad(26) * math.sin(ph), 0, 0)
    WP['armL'].rotation_euler = (-rad(20) * math.sin(ph), 0, 0)
    dpos, dpitch, s = dog_state(t)
    dog.location = dpos; dog.rotation_euler = (dpitch, 0, math.pi / 2)
    if s is None:
        g = 2 * math.pi * 3.0 * t
        for nm in ('FL', 'FR'):
            DP[nm].rotation_euler = (0.85 * math.sin(g + (0.4 if nm == 'FR' else 0)), 0, 0)
        for nm in ('BL', 'BR'):
            DP[nm].rotation_euler = (0.85 * math.sin(g + 2.2 + (0.4 if nm == 'BR' else 0)), 0, 0)
    else:
        for nm in ('FL', 'FR'):
            DP[nm].rotation_euler = (1.25 - 0.5 * s, 0, 0)
        for nm in ('BL', 'BR'):
            DP[nm].rotation_euler = (-1.2 + 0.4 * s, 0, 0)
    carroot.location = (CAR_X, car_y(t), 0)
    sax.rotation_euler = (rad(3) * math.sin(t * 2.2), 0, rad(150) + rad(5) * math.sin(t * 1.3))
    drv_head.rotation_euler = (0, 0, rad(-28) * bump(t, 23.0, 23.6, 24.2, 24.8))
    for o, x, y0, v in MOVERS:
        o.location = (x, y0 + v * t, 0)
    for o, p0, v in WALKERS:
        o.location = p0 + v * t

# ------------------------------------------------------------------ render setup
world = bpy.data.worlds.new('world'); world.color = (lin(0.84), lin(0.85), lin(0.86)); scene.world = world
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_shadows = False; sh.show_cavity = False
sh.show_object_outline = False; sh.show_specular_highlight = False
try:
    sh.use_world_space_lighting = False
except Exception:
    pass
scene.display.render_aa = arg('--aa', '8')
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x = RX; scene.render.resolution_y = RY; scene.render.resolution_percentage = 100
scene.render.fps = FPS; scene.frame_start = 0; scene.frame_end = NF - 1
scene.render.image_settings.file_format = 'JPEG'; scene.render.image_settings.quality = 92
os.makedirs(OUT, exist_ok=True)
print('objects:', len(bpy.data.objects), flush=True)

def render_frame(f, path):
    apply(f / FPS)
    scene.frame_set(f)
    apply(f / FPS)
    bpy.context.view_layer.update()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

if MODE == 'stills':
    for ts in arg('--times', '0').split(','):
        t = float(ts)
        render_frame(int(round(t * FPS)), os.path.join(OUT, 's_%05.2f.jpg' % t))
elif MODE == 'anim':
    import time
    a = int(arg('--start', '0')); b = int(arg('--end', str(NF - 1))); t0 = time.time()
    for f in range(a, b + 1):
        p = os.path.join(OUT, 'f_%04d.jpg' % f)
        if os.path.exists(p):
            continue
        render_frame(f, p)
        if (f - a) % 25 == 0:
            print('frame', f, round(time.time() - t0, 1), 's', flush=True)
elif MODE == 'blend':
    for f in range(0, NF):
        apply(f / FPS)
        for o in ANIM:
            o.keyframe_insert('location', frame=f)
            o.keyframe_insert('rotation_quaternion' if o.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=f)
    scene.frame_set(0)
    for img in bpy.data.images:
        try:
            img.pack()
        except Exception:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'onetake.blend'))
    print('saved blend', flush=True)
