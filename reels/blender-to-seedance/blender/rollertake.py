# Roller one-take (grey-box previz) for a "Blender -> Seedance" reel: Tel Aviv seafront, morning to sunset.
# Builds the scene procedurally and renders it with Blender's Workbench (solid viewport) engine.
#   python rollertake.py -- --mode stills --times 0,7.25,17.4 --res 640x360 --out out/stills
#   python rollertake.py -- --mode anim --start 0 --end 899 --out out/frames      (resumable)
#   python rollertake.py -- --mode blend --out out                                  (bakes keyframes, saves rollertake.blend)
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

def ped(x, y, z=G, s=1.0):
    r = empty('ped', (x, y, z))
    obj('sph', 'ped_body', (0, 0, 0.82 * s), (0.44 * s, 0.32 * s, 1.5 * s), PED, parent=r)
    obj('sph', 'ped_head', (0, 0, 1.62 * s), (0.22 * s, 0.24 * s, 0.26 * s), PED, parent=r)
    return r
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


# ===================================================================== ROLLER ONE-TAKE
# Tel Aviv seafront, morning -> sunset: top view -> floor chase -> street -> supermarket -> SHOTCALLER garage -> sunset.
SEA = mat('sea', (0.45, 0.72, 0.86)); SAND = mat('sand', (0.92, 0.86, 0.72)); PROM = grey('prom', 0.76); PROM2 = grey('prom2', 0.86)
ROADM = grey('road', 0.47); WALK = grey('walk', 0.70); WHITE = grey('white', 0.97); REDC = mat('curb_red', (0.82, 0.16, 0.14))
PINK = mat('top_pink', (0.92, 0.16, 0.46)); HOLO = mat('holo', (0.80, 0.72, 0.96)); HAIR = mat('hair', (0.36, 0.20, 0.12)); SKIN = grey('skin', 0.90)
PURPLE = mat('car_purple', (0.45, 0.20, 0.68)); TEALM = mat('teal', (0.15, 0.78, 0.74)); ORANGE = mat('orange', (0.97, 0.56, 0.10))
SUNM = mat('sun', (1.0, 0.74, 0.32)); SHELF = grey('shelf', 0.82); FLOORM = grey('floor', 0.88); YARD = grey('yard', 0.60)
PALMG = mat('palm', (0.42, 0.60, 0.40)); HEADL = mat('headlight', (1.0, 0.93, 0.62))
PROD = [mat('p_red', (0.86, 0.2, 0.2)), mat('p_yel', (0.96, 0.82, 0.2)), mat('p_blu', (0.2, 0.45, 0.86)), mat('p_grn', (0.25, 0.7, 0.36)),
        mat('p_pnk', (0.96, 0.5, 0.72)), mat('p_wht', (0.96, 0.96, 0.96)), mat('p_org', (0.96, 0.56, 0.15))]
UMB = [PINK, mat('umb_yel', (0.98, 0.84, 0.25)), WHITE, TEALM, mat('umb_org', (0.98, 0.55, 0.2))]
random.seed(11)

def smooth(a, b, t):
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)
def bump(t, a, b, c, d):
    return smooth(a, b, t) * (1 - smooth(c, d, t))

class Spline:
    """Cubic Hermite through timed keys (finite-difference tangents, linear precision)."""
    def __init__(self, keys):
        self.K = [(t, Vector(p)) for t, p in keys]; self.T = [k[0] for k in self.K]
        self.M = [self._tan(i) for i in range(len(self.K))]
    def _tan(self, k):
        K = self.K; n = len(K)
        if k == 0:
            return (K[1][1] - K[0][1]) / (K[1][0] - K[0][0])
        if k == n - 1:
            return (K[-1][1] - K[-2][1]) / (K[-1][0] - K[-2][0])
        (ta, pa), (tb, pb), (tc, pc) = K[k - 1], K[k], K[k + 1]
        return ((pb - pa) / (tb - ta) * (tc - tb) + (pc - pb) / (tc - tb) * (tb - ta)) / (tc - ta)
    def __call__(self, t):
        t = min(max(t, self.T[0]), self.T[-1] - 1e-6)
        i = max(0, min(len(self.K) - 2, bisect.bisect_right(self.T, t) - 1))
        (t0, p0), (t1, p1) = self.K[i], self.K[i + 1]; h = t1 - t0; s = (t - t0) / h
        return ((2 * s ** 3 - 3 * s ** 2 + 1) * p0 + (s ** 3 - 2 * s ** 2 + s) * h * self.M[i]
                + (-2 * s ** 3 + 3 * s ** 2) * p1 + (s ** 3 - s ** 2) * h * self.M[i + 1])

# ------------------------------------------------------------------ ground, sea, promenade
obj('cube', 'ground', (0, 60, -0.5), (1500, 1700, 1.0), ROADM)
box(-750, -20, -760, 880, 0, 0.03, SEA, 'sea'); box(-20, -8, -760, 880, 0, 0.07, SAND, 'beach')
box(-8, 6, -760, 880, 0, G, PROM, 'promenade'); box(20, 25, -760, 880, 0, 0.04, WALK, 'east_walk')
box(25, 68, 4, 32, 0, 0.03, YARD, 'yard'); box(34, 68, 30, 74, 0, 0.035, FLOORM, 'super_floor')
quads('prom_bands', [flat(-7.6, 5.6, y, y + 1.3, G + 0.01) for y in range(-150, 260, 6)], PROM2)
for i, y in enumerate(range(-90, 190)):
    box(5.82, 6.12, y, y + 1.0, 0, G + 0.03, REDC if i % 2 == 0 else WHITE, 'curb')
tube((-8, -150, 1.05), (-8, 260, 1.05), 0.08, METAL, name='rail')
for y in range(-150, 261, 4):
    tube((-8, y, G), (-8, y, 1.05), 0.07, METAL, name='rail_post')
def palm(x, y, h=9.0):
    tube((x, y, 0), (x + 0.3, y, h), 0.38, WOOD, name='palm_trunk')
    for k in range(7):
        a = k * 2 * math.pi / 7 + x + y
        o = obj('sph', 'palm_frond', (x + 0.3 + math.cos(a) * 1.7, y + math.sin(a) * 1.7, h - 0.35), (3.8, 0.75, 0.16), PALMG)
        o.rotation_euler = (0, rad(18), a)
for y in range(-140, 250, 15):
    palm(-6.4, y + 4, 9.5); palm(4.7, y - 3, 8.5)
for y in range(-50, 170, 22):
    box(-7.6, -6.9, y, y + 2.0, G, G + 0.45, WOOD, 'bench')
for _ in range(34):
    x, y, m = random.uniform(-19, -10.5), random.uniform(-90, 190), random.choice(UMB)
    tube((x, y, 0), (x, y, 2.1), 0.06, METAL, name='umb_pole'); obj('sph', 'umbrella', (x, y, 2.15), (2.7, 2.7, 0.55), m)
    box(x + 0.5, x + 1.2, y - 1.0, y + 0.9, 0.07, 0.36, WHITE, 'sunbed')
box(-16.5, -13.5, 57.5, 60.5, 2.3, 4.6, WHITE, 'lifeguard_hut'); box(-16.9, -13.1, 57.1, 60.9, 4.6, 4.8, TEALM, 'lifeguard_roof')
for dx in (-16.2, -13.8):
    for dy in (57.8, 60.2):
        tube((dx, dy, 0), (dx, dy, 2.3), 0.12, WOOD, name='hut_leg')
box(3.6, 4.6, 29.4, 31.0, G, G + 1.1, PINK, 'icecream_cart'); obj('sph', 'cart_umbrella', (4.1, 30.2, G + 2.3), (2.2, 2.2, 0.45), WHITE)
tube((4.1, 30.2, G + 1.1), (4.1, 30.2, G + 2.3), 0.05, METAL, name='cart_pole')

# coastal road paint + traffic
paint = [flat(12.92, 13.08, y, y + 3, 0.02) for y in range(-300, 420, 9) if not (55 < y < 64 or 6 < y < 17)]
for zy0, zy1 in ((58, 62), (10.5, 14.5)):
    x = 6.7
    while x < 19.3:
        paint.append(flat(x, x + 0.6, zy0, zy1, 0.02)); x += 1.2
quads('road_paint', paint, PAINT)
for y in range(-140, 300, 7):
    if not (0 <= y <= 36 or 54 <= y <= 88) and random.random() > 0.25:
        car(18.7, y, 0)
    if not (0 <= y <= 26 or 40 <= y <= 74) and random.random() > 0.4:
        car(7.35, y, math.pi)
MOVERS = []
def mover(x, y_at, t_at, v, m=None):
    o = car(x, 0, 0 if v > 0 else math.pi, m); MOVERS.append((o, x, y_at - v * t_at, v))
mover(9.8, 70, 4.0, -9.0, CAB); mover(9.8, 140, 8.0, -9.0); mover(16.2, 40, 7.0, 9.0, CARCOL[5]); mover(16.2, 12, 24.6, 9.0, CAB)
mover(9.8, 13, 28.9, -9.0, CARCOL[6]); mover(16.2, -60, 12.0, 9.0); mover(9.8, 200, 20.0, -9.0, CAB); mover(16.2, 90, 2.0, 9.0, CARCOL[3])

def ped_at(x, y, z=0.0):
    return ped(x, y, z)
for x, y in ((-6.2, 22), (-6.7, 23), (4.6, 36), (-5.9, 58), (4.5, 70), (-6.4, -6), (4.6, 2), (-6.0, 90), (4.4, 104), (-6.6, 44)):
    ped_at(x, y, G)
for x, y in ((-14, 12), (-12, 40), (-17, 76), (-11, 96), (-15, -20)):
    ped_at(x, y, 0.07)

# ------------------------------------------------------------------ buildings
def balconies(x0, x1, y0, y1, h, faces, fl=3.4):
    for k in range(1, int(h // fl)):
        z = k * fl
        for f in faces:
            if f == 'W':
                box(x0 - 1.1, x0, y0 + 0.5, y1 - 0.5, z - 0.1, z + 0.08, WHITE, 'balcony'); box(x0 - 1.1, x0 - 1.0, y0 + 0.5, y1 - 0.5, z, z + 0.95, WHITE, 'parapet')
            elif f == 'N':
                box(x0 + 0.5, x1 - 0.5, y1, y1 + 1.1, z - 0.1, z + 0.08, WHITE, 'balcony'); box(x0 + 0.5, x1 - 0.5, y1 + 1.0, y1 + 1.1, z, z + 0.95, WHITE, 'parapet')
            elif f == 'S':
                box(x0 + 0.5, x1 - 0.5, y0 - 1.1, y0, z - 0.1, z + 0.08, WHITE, 'balcony'); box(x0 + 0.5, x1 - 0.5, y0 - 1.1, y0 - 1.0, z, z + 0.95, WHITE, 'parapet')
def round_corner(cx, cy, h, r=3.6, fl=3.4):
    obj('cyl', 'bauhaus_corner', (cx, cy, h / 2), (2 * r, 2 * r, h), WHITE)
    for k in range(1, int(h // fl)):
        obj('cyl', 'bauhaus_ring', (cx, cy, k * fl + 0.43), (2 * r + 2.2, 2 * r + 2.2, 0.95), WHITE)
building(25, 34, 32, 74, 14, BM[0], ('W', 'N')); balconies(25, 34, 32, 74, 14, ('W', 'N')); round_corner(27.7, 71.3, 14)
building(25, 58, 86, 120, 17, BM[0], ('W', 'S')); balconies(25, 58, 86, 120, 17, ('W', 'S')); round_corner(27.7, 88.7, 17)
building(58, 110, 86, 120, 12, BM[1], ('S',)); building(68, 110, 30, 74, 15, BM[1], ('N',))
building(25, 62, -46, 4, 16, BM[0], ('W', 'N')); balconies(25, 62, -46, 4, 16, ('W',)); round_corner(27.7, 1.3, 16)
building(62, 110, -46, 4, 11, BM[2], ('N',)); box(84, 110, 4, 30, 0, 9, BM[1], 'bld')
for y0, y1 in ((126, 160), (170, 205), (215, 250), (260, 300), (310, 350), (360, 400), (-90, -56), (-132, -100), (-176, -142), (-222, -186), (-270, -232)):
    hh = random.uniform(14, 52); building(25, random.uniform(55, 72), y0, y1, hh, random.choice(BM[:3]), ('W',)); balconies(25, 60, y0, y1, min(hh, 24), ('W',))
for x0, x1 in ((76, 112), (122, 170), (180, 230), (240, 292)):
    for y0 in range(-270, 400, 50):
        if x0 < 112 and -50 < y0 < 124:
            continue
        box(x0, x1, y0, y0 + 40, 0, random.uniform(9, 27), random.choice(BM), 'bld_far')
billboard('bb_sunny', (25 - 0.2, 104, 12.5), 10, 5, '-x', 'sunny'); billboard('bb_soda', (69, 86 - 0.2, 8.5), 9, 4.5, '-y', 'soda')

# side-street cafe + slalom planters
for x in (30, 33.2, 36.4, 39.6, 42.8, 46):
    obj('cyl', 'cafe_table', (x, 84.5, 0.74), (0.8, 0.8, 0.05), METAL); tube((x, 84.5, 0), (x, 84.5, 0.74), 0.08, METAL, name='table_leg')
    if int(x) % 2 == 0:
        ped_at(x + 0.9, 84.7)
for x, y in ((37.0, 80.0), (40.1, 80.4), (43.2, 79.9), (46.3, 80.4)):
    obj('cyl', 'planter', (x, y, 0.35), (0.9, 0.9, 0.7), WHITE); obj('ico', 'planter_bush', (x, y, 1.05), (1.15, 1.15, 1.0), PALMG)
for x, y in ((36, 76.0), (44, 76.2), (56, 84.8), (60, 76.0)):
    ped_at(x, y)
for y0, y1, m in ((40, 48, PINK), (54, 62, TEALM)):
    o = box(23.6, 25.0, y0, y1, 3.0, 3.15, m, 'awning'); o.rotation_euler = (0, rad(14), 0)

# ------------------------------------------------------------------ supermarket (x 34..68, y 30..74)
SH = 6.5
box(34, 48.6, 73.85, 74.15, 0, SH, BM[1], 'super_wall_n1'); box(51.4, 68, 73.85, 74.15, 0, SH, BM[1], 'super_wall_n2'); box(48.6, 51.4, 73.85, 74.15, 3.0, SH, BM[1], 'super_lintel')
box(34, 48, 29.85, 30.15, 0, SH, BM[1], 'super_wall_s1'); box(52, 68, 29.85, 30.15, 0, SH, BM[1], 'super_wall_s2'); box(48, 52, 29.85, 30.15, 3.4, SH, BM[1], 'super_lintel_s')
box(33.85, 34.15, 30, 74, 0, SH, BM[1], 'super_wall_w'); box(67.85, 68.15, 30, 74, 0, SH, BM[1], 'super_wall_e'); box(33.8, 68.2, 29.8, 74.2, SH, SH + 0.3, BM[2], 'super_roof')
quads('super_glass', [[(36, 74.17, 0.4), (47.6, 74.17, 0.4), (47.6, 74.17, 2.9), (36, 74.17, 2.9)], [(52.4, 74.17, 0.4), (66, 74.17, 0.4), (66, 74.17, 2.9), (52.4, 74.17, 2.9)]], GLASS)
billboard('super_sign', (50, 74.3, 4.75), 13, 2.5, '+y', 'super', frame=False)
door_l = box(48.6, 50.0, 73.95, 74.05, 0.03, 3.0, GLASS, 'door_l'); door_r = box(50.0, 51.4, 73.95, 74.05, 0.03, 3.0, GLASS, 'door_r')
box(48, 52, 29.9, 30.1, 1.5, 3.4, METAL, 'back_shutter')
SHELVES = [(38.8, 40.0), (43.0, 44.2), (47.2, 48.4), (51.6, 52.8), (55.8, 57.0), (60.0, 61.2), (64.2, 65.4)]
prod_rects = {m.name: [] for m in PROD}
for xa, xb in SHELVES:
    box(xa, xb, 36, 66, 0.03, 2.1, SHELF, 'shelf')
    for xf, nx_ in ((xa - 0.02, -1), (xb + 0.02, 1)):
        for zl in (0.32, 0.92, 1.52):
            y = 36.2
            while y < 65.6:
                w = random.uniform(0.35, 0.8)
                prod_rects[random.choice(PROD).name].append([(xf, y, zl), (xf, y + w - 0.06, zl), (xf, y + w - 0.06, zl + 0.46), (xf, y, zl + 0.46)])
                y += w
for m in PROD:
    quads('products_' + m.name, prod_rects[m.name], m)
for x in (41.5, 45.6, 54.2, 58.4, 62.6):
    box(x - 0.1, x + 0.1, 37, 65, 6.25, 6.32, WHITE, 'ceiling_light')
box(49.9, 50.1, 34, 70, 6.25, 6.32, WHITE, 'ceiling_light_c')
for xa, xb in ((38, 41), (43, 46), (54, 57), (59, 62)):
    box(xa, xb, 69.6, 70.6, 0.03, 0.95, SHELF, 'checkout'); ped_at(xa + 0.6, 71.3)
for x, y in ((41.6, 60), (45.6, 50), (58.4, 56), (62.6, 44), (54.3, 62)):
    ped_at(x, y)
cart = empty('cart', (54.2, 67.6, 0)); box(-0.3, 0.3, -0.5, 0.5, 0.45, 1.0, METAL, 'cart_basket', parent=cart); box(-0.3, 0.3, -0.5, 0.5, 0.12, 0.2, METAL, 'cart_base', parent=cart)
# orange pyramid she clips on the way in
box(51.2, 52.4, 65.9, 67.1, 0.03, 0.75, WOOD, 'orange_table')
ORANGES = []
for lvl, n in enumerate((4, 3, 2, 1)):
    for i in range(n):
        for j in range(n):
            p0 = Vector((51.8 + (i - (n - 1) / 2) * 0.24, 66.5 + (j - (n - 1) / 2) * 0.24, 0.75 + 0.12 + lvl * 0.2))
            o = obj('sph', 'orange', p0, (0.23, 0.23, 0.23), ORANGE)
            ORANGES.append((o, p0, Vector((random.uniform(-2.2, 0.3), random.uniform(-7.5, -3.0), random.uniform(0.4, 2.6))), (3 - lvl) * 0.06 + random.uniform(0, 0.12)))
T_ORANGE = 14.85
# boxes that rain off the top shelves in her wake
FALLERS = []
for k in range(23):
    for xs, sgn in ((48.05, 1), (51.95, -1)):
        y = 64.0 - k * 1.2 + random.uniform(-0.25, 0.25)
        o = obj('cube', 'falling_box', (xs, y, 2.38), (0.42, 0.3, 0.56), random.choice(PROD))
        FALLERS.append([o, Vector((xs, y, 2.38)), Vector((sgn * random.uniform(0.7, 1.7), random.uniform(-1.8, 0.2), random.uniform(0.3, 1.4))),
                        Vector((random.uniform(-7, 7), random.uniform(-7, 7), random.uniform(-4, 4))), 0.0])

# ------------------------------------------------------------------ SHOTCALLER garage (x 84..100, y 6..24) + yard
_before = set(bpy.data.objects)
box(99.8, 100.1, 6, 24, 0, 5.5, BM[2], 'garage_back'); box(84, 100, 5.85, 6.15, 0, 5.5, BM[2], 'garage_s'); box(84, 100, 23.85, 24.15, 0, 5.5, BM[2], 'garage_n')
box(83.85, 84.15, 6, 9.5, 0, 5.5, BM[2], 'garage_w1'); box(83.85, 84.15, 20.5, 24, 0, 5.5, BM[2], 'garage_w2'); box(83.85, 84.15, 9.5, 20.5, 3.7, 5.5, BM[2], 'garage_lintel')
box(83.8, 100.2, 5.8, 24.2, 5.5, 5.75, BM[3], 'garage_roof'); box(83.6, 84.0, 9.5, 20.5, 3.45, 3.75, METAL, 'shutter_roll')
billboard('shotcaller_sign', (83.55, 15, 4.55), 9.6, 1.4, '-x', 'shotcaller', frame=False); box(83.6, 83.85, 10.0, 20.0, 3.8, 5.3, DARK, 'sign_box')
tube((83.8, 15, 5.6), (82.9, 15, 5.9), 0.07, DARK, name='gooseneck'); obj('sph', 'lamp_shade', (82.8, 15, 5.75), (0.7, 0.7, 0.3), DARK)
box(98.6, 99.7, 9, 21, 0.03, 0.95, RED, 'workbench'); box(98.8, 99.5, 14.2, 15.8, 0.95, 1.45, METAL, 'boombox')
for by in (14.55, 15.45):
    obj('cyl', 'speaker', (98.78, by, 1.2), (0.38, 0.38, 0.05), DARK, rot=(0, rad(90), 0))
quads('tool_wall', [[(99.75, 10, 1.4), (99.75, 20, 1.4), (99.75, 20, 3.0), (99.75, 10, 3.0)]], DARK)
box(92, 92.1, 11, 19, 5.3, 5.38, WHITE, 'garage_tube_light'); box(83.2, 83.85, 21.2, 22.6, 2.6, 3.4, WHITE, 'ac_unit')
quads('barred_window', [[(83.83, 6.6, 1.4), (83.83, 8.6, 1.4), (83.83, 8.6, 2.9), (83.83, 6.6, 2.9)]], WINDOW)
for x, y in ((80.5, 7.5), (81.4, 8.2)):
    obj('cyl', 'tyre', (x, y, 0.14), (0.7, 0.7, 0.24), TIRE)
obj('cyl', 'oil_drum', (82.2, 22.8, 0.48), (0.6, 0.6, 0.9), TEALM); palm(86.5, 27.0, 8.0); ped_at(81.5, 21.2)
for _o in set(bpy.data.objects) - _before:
    if _o.parent is None:
        _o.location.x -= 16.0
# metallic purple 80s sedan
pcar = empty('purple_car')
def pb(x0, x1, y0, y1, z0, z1, m, n='pc'):
    return box(x0, x1, y0, y1, z0, z1, m, n, parent=pcar)
pb(-0.86, 0.86, -2.25, 2.25, 0.30, 0.86, PURPLE, 'pc_body'); pb(-0.78, 0.78, -1.25, 0.55, 0.86, 1.30, GLASS, 'pc_glass'); pb(-0.77, 0.77, -1.15, 0.45, 1.30, 1.37, PURPLE, 'pc_roof')
pb(-0.9, 0.9, 2.25, 2.36, 0.30, 0.50, DARK, 'pc_bumper_f'); pb(-0.9, 0.9, -2.36, -2.25, 0.30, 0.50, DARK, 'pc_bumper_r'); pb(-0.38, 0.38, 2.25, 2.28, 0.55, 0.76, DARK, 'pc_grille')
for sx in (-1, 1):
    pb(sx * 0.42, sx * 0.82, 2.25, 2.30, 0.55, 0.76, HEADL, 'pc_headlight'); pb(sx * 0.862, sx * 0.875, -2.2, 2.2, 0.50, 0.54, TEALM, 'pc_stripe_teal'); pb(sx * 0.862, sx * 0.875, -2.2, 2.2, 0.56, 0.60, PINK, 'pc_stripe_pink')
    for sy in (-1.4, 1.4):
        obj('cyl', 'pc_wheel', (sx * 0.8, sy, 0.32), (0.64, 0.64, 0.22), TIRE, rot=(0, rad(90), 0), parent=pcar); obj('cyl', 'pc_hub', (sx * 0.9, sy, 0.32), (0.36, 0.36, 0.06), CHROME, rot=(0, rad(90), 0), parent=pcar)
pcar.rotation_euler = (0, 0, math.pi / 2)
def car_x(t):
    if t < 15.9:
        return 74.0
    if t < 21.9:
        return 74.0 - 4.0 * (t - 15.9)
    tau = t - 21.9
    if tau < 3.5:
        return 50.0 - 4.0 * tau - 0.6 * tau * tau
    tb = min(tau - 3.5, 1.43)
    return 28.65 - 8.2 * tb + 0.5 * 5.75 * tb * tb
sun = obj('sph', 'sun', (-900, 40, -300), (95, 95, 95), SUNM)

# ------------------------------------------------------------------ the skater (hot-pink crop top, holographic cargos, long brown hair)
sk = empty('skater'); body = empty('sk_body', (0, 0, 1.0), parent=sk)
obj('sph', 'sk_pelvis', (0, 0, 0.02), (0.42, 0.30, 0.34), HOLO, parent=body)
torso = empty('sk_torso', (0, 0, 0.10), parent=body)
obj('sph', 'sk_waist', (0, 0, 0.20), (0.33, 0.24, 0.34), SKIN, parent=torso); obj('sph', 'sk_chest', (0, 0, 0.44), (0.42, 0.28, 0.42), PINK, parent=torso)
head = empty('sk_head', (0, 0, 0.76), parent=torso)
obj('sph', 'sk_face', (0, 0, 0.06), (0.21, 0.23, 0.26), SKIN, parent=head); obj('sph', 'sk_haircap', (0, -0.03, 0.10), (0.25, 0.25, 0.23), HAIR, parent=head)
hairj = empty('sk_hairj', (0, -0.08, 0.14), parent=head); obj('limb', 'sk_hair', (0, -0.04, 0.04), (0.32, 0.13, 0.80), HAIR, parent=hairj)
J = {}
for side, sx in (('L', -1), ('R', 1)):
    hip = empty('sk_hip' + side, (sx * 0.12, 0, 0.0), parent=body); obj('limb', 'sk_thigh' + side, (0, 0, 0.04), (0.23, 0.24, 0.50), HOLO, parent=hip)
    knee = empty('sk_knee' + side, (0, 0, -0.44), parent=hip); obj('limb', 'sk_shin' + side, (0, 0, 0.03), (0.22, 0.23, 0.46), HOLO, parent=knee)
    box(-0.06, 0.06, -0.11, 0.19, -0.50, -0.38, WHITE, 'sk_boot' + side, parent=knee)
    for wy in (-0.09, 0.0, 0.09, 0.18):
        obj('cyl', 'sk_wheel', (0, wy, -0.53), (0.085, 0.085, 0.035), DARK, rot=(0, rad(90), 0), parent=knee)
    sh = empty('sk_sh' + side, (sx * 0.26, 0, 0.58), parent=torso); obj('limb', 'sk_uarm' + side, (0, 0, 0.03), (0.11, 0.11, 0.33), SKIN, parent=sh)
    el = empty('sk_el' + side, (0, 0, -0.29), parent=sh); obj('limb', 'sk_farm' + side, (0, 0, 0.02), (0.10, 0.10, 0.32), SKIN, parent=el)
    J.update({'hip' + side: hip, 'knee' + side: knee, 'sh' + side: sh, 'el' + side: el})

SP = Spline([(t, (x, y, 0)) for t, x, y in [
    (-0.6, -3.6, 4.4), (0.0, -2.5, 8.0), (1.0, 0.5, 14.0), (2.0, -3.0, 20.5), (3.0, 0.5, 27.0), (4.0, -2.5, 33.5), (5.0, 0.0, 40.0), (6.0, 2.5, 46.5),
    (6.8, 5.0, 51.5), (7.0, 6.0, 52.9), (7.6, 8.8, 57.0), (8.4, 11.5, 62.5), (9.2, 15.5, 68.5), (10.0, 20.5, 75.0), (10.8, 26.5, 80.0),
    (11.5, 32.5, 80.6), (12.0, 37.0, 81.3), (12.4, 40.1, 79.2), (12.8, 43.2, 81.1), (13.2, 46.3, 79.2), (13.8, 49.3, 76.3), (14.3, 50.0, 72.6),
    (15.0, 50.2, 67.0), (15.8, 50.0, 60.5), (16.6, 50.0, 53.5), (17.4, 50.0, 46.5), (18.2, 50.0, 39.5), (18.9, 50.0, 34.0), (19.5, 50.0, 29.5),
    (20.1, 50.0, 25.0), (20.8, 50.0, 19.6), (21.1, 50.0, 17.6), (21.5, 50.0, 15.0), (21.9, 50.0, 12.4), (22.6, 46.5, 9.8), (23.4, 41.0, 9.5),
    (24.2, 35.0, 10.0), (25.0, 28.5, 10.8), (25.8, 22.0, 11.6), (26.6, 15.5, 12.4), (27.4, 9.5, 13.2), (27.9, 6.2, 13.8), (28.6, 2.0, 14.6),
    (29.3, -1.5, 15.2), (30.0, -3.0, 15.5), (30.8, -3.2, 15.55)]])
JUMPS = [(6.9, 7.6, 1.15), (21.1, 21.9, 1.55), (27.75, 28.3, 0.6)]
def ground(x):
    return G * (1 - smooth(5.6, 6.4, x))
def sk_heading(t):
    tt = min(max(t, 0.0), 29.2)
    v = SP(tt + 0.12) - SP(tt - 0.12)
    return v.normalized() if v.length > 1e-6 else Vector((0, 1, 0))
def zjump(t):
    for a, b, apex in JUMPS:
        if a < t < b:
            s = (t - a) / (b - a); return apex * 4 * s * (1 - s)
    return 0.0
POINT = dict(sRx=rad(170), eR=rad(5), sRy=rad(10), lean=rad(4))
TUCK = dict(hLx=rad(80), hRx=rad(80), kL=rad(-110), kR=rad(-110), sLx=rad(45), sRx=rad(45), eL=rad(70), eR=rad(70), lean=rad(24), hLy=rad(8), hRy=rad(8))
SPINP = dict(sLy=rad(80), sRy=rad(80), sLx=0.0, sRx=0.0, eL=rad(5), eR=rad(5), hLx=rad(4), hRx=rad(4), kL=rad(-8), kR=rad(-8), lean=rad(2), hair=rad(-70))
DUCK = dict(zoff=-0.70, hLx=rad(100), kL=rad(-152), hRx=rad(86), kR=rad(-4), lean=rad(36), sLx=rad(75), sRx=rad(75), eL=rad(10), eR=rad(10), hLy=rad(6), hRy=rad(4))
STAG = dict(hLx=rad(82), kL=rad(-25), hRx=rad(-38), kR=rad(-75), sLx=rad(155), sRx=rad(150), eL=rad(10), eR=rad(10), lean=rad(6), sLy=rad(15), sRy=rad(15))
STOP = dict(hLx=rad(4), hRx=rad(4), hLy=rad(20), hRy=rad(20), kL=rad(-8), kR=rad(-8), sLx=rad(172), sRx=rad(172), sLy=rad(22), sRy=rad(22), eL=rad(4), eR=rad(4), lean=rad(-3), hair=rad(-6))
def pose(t):
    s_ = math.sin(2 * math.pi * 1.3 * t)
    d = dict(zoff=0.0, lean=rad(14), hLx=rad(6 + 26 * s_), hRx=rad(6 - 26 * s_), hLy=rad(5 + 7 * max(0, -s_)), hRy=rad(5 + 7 * max(0, s_)),
             kL=rad(-24 - 16 * max(0, -s_)), kR=rad(-24 - 16 * max(0, s_)), sLx=rad(-30 * s_), sRx=rad(30 * s_), sLy=rad(8), sRy=rad(8),
             eL=rad(40), eR=rad(40), hair=rad(-28))
    for target, w in ((POINT, bump(t, 2.5, 2.9, 3.7, 4.2)), (TUCK, bump(t, 6.8, 7.05, 7.45, 7.7)), (SPINP, bump(t, 10.8, 11.0, 11.8, 12.0)),
                      (DUCK, bump(t, 18.5, 18.9, 19.8, 20.3)), (STAG, bump(t, 21.0, 21.25, 21.75, 22.0)), (TUCK, 0.7 * bump(t, 27.65, 27.85, 28.2, 28.4)),
                      (STOP, smooth(29.0, 29.6, t))):
        if w > 1e-4:
            for k, v in target.items():
                d[k] = d[k] * (1 - w) + v * w
    return d

# ------------------------------------------------------------------ camera: keys relative to the skater ('s': ahead, right, up) or world ('w')
CK = [(-0.5, 's', 0.5, 0, 15), (0.0, 's', 0.5, 0, 14.5), (1.2, 's', 0.5, 0.3, 12.5), (2.4, 's', 0.2, 1.0, 9.5), (3.4, 's', -2.2, 1.8, 6.5), (4.2, 's', -5.0, 1.0, 3.8),
      (4.9, 's', -4.6, 0.2, 1.8), (5.6, 's', -2.8, 0, 0.55), (6.3, 's', -2.1, 0.1, 0.42), (6.9, 's', -1.3, 0.5, 0.34), (7.25, 's', 0.0, 0.8, 0.30),
      (7.6, 's', 1.5, 0.65, 0.45), (8.2, 's', 3.2, 0.3, 0.9), (9.0, 's', 3.4, 1.6, 1.3), (10.0, 's', 1.0, 3.4, 1.4), (10.8, 's', 2.6, -2.4, 1.2),
      (11.6, 's', 3.2, 0, 1.0), (12.4, 'w', 41.0, 82.6, 1.1), (12.9, 'w', 44.6, 82.5, 1.2), (13.4, 'w', 48.0, 81.3, 1.25), (13.8, 's', -3.2, 0, 1.0), (14.3, 's', -3.0, 0, 0.7),
      (15.0, 's', -2.6, -0.3, 0.5), (15.8, 's', -3.0, 0, 0.45), (16.4, 's', -2.6, 0, 2.2), (17.0, 's', -0.8, 0, 5.2), (17.7, 's', 0.8, 0, 5.4),
      (18.3, 's', 3.4, 0, 3.0), (18.9, 's', 4.0, 0.2, 0.8), (19.5, 's', 3.3, 0.3, 0.5), (20.1, 's', 2.6, 1.8, 0.9), (20.8, 's', 0.6, 4.2, 1.0),
      (21.5, 'w', 44.5, 15.6, 4.4), (21.9, 'w', 45.0, 12.5, 2.2), (22.6, 's', 4.0, 0.3, 1.2), (23.4, 's', 3.4, -1.6, 1.0), (24.2, 's', 0.5, -3.2, 1.2),
      (25.0, 's', -3.4, -1.0, 1.5), (25.8, 's', -3.0, 0, 0.6), (26.6, 's', -2.5, 0, 0.45), (27.4, 's', -2.2, 0.2, 0.45), (28.0, 's', -2.0, 0.3, 0.5),
      (28.5, 's', -2.8, 0, 1.6), (29.0, 's', -3.2, 0, 4.2), (29.5, 's', -2.2, 0, 8.0), (30.0, 's', -0.8, 0, 12.0), (30.6, 's', 0.0, 0, 15.5)]
def resolve(k):
    t, mode, a, b, c = k
    if mode == 'w':
        return (t, (a, b, c))
    h = sk_heading(t); r = Vector((h.y, -h.x, 0)); p = SP(t) + h * a + r * b
    return (t, (p.x, p.y, ground(p.x) + c))
CP = Spline([resolve(k) for k in CK])
def hv(deg):
    return Vector((math.sin(rad(deg)), math.cos(rad(deg)), 0))
ROLL = [(0, 0), (4.6, 0), (5.6, -6), (7.25, 10), (8.2, 0), (10.2, -8), (11.2, 6), (12.6, 0), (14.0, 8), (15.0, 0), (20.4, 0), (21.5, -8), (22.6, 0),
        (24.2, 7), (25.4, 0), (30.1, 0)]
def roll_at(t):
    for (ta, ra), (tb, rb) in zip(ROLL, ROLL[1:]):
        if ta <= t <= tb:
            return ra + (rb - ra) * smooth(ta, tb, t)
    return 0.0
def cam_state(t):
    P = CP(t)
    d0 = pose(t)
    S = SP(t); target = Vector((S.x, S.y, ground(S.x) + zjump(t) + 1.0 + d0['zoff'] + 0.28))
    v = target - P; vh = Vector((v.x, v.y, 0)); hd = vh.normalized() if vh.length > 1e-4 else Vector((0, 1, 0))
    for w, deg in ((1 - smooth(2.6, 4.4, t), -100 + 100 * smooth(0, 4.2, t)), (bump(t, 16.5, 17.0, 17.8, 18.3), 180 + 180 * smooth(16.7, 18.2, t)),
                   (smooth(29.0, 29.7, t), 270 - 22 * smooth(29.0, 30.0, t))):
        if w > 1e-4:
            hd = (hd * (1 - w) + hv(deg) * w); hd = hd.normalized() if hd.length > 1e-4 else hv(deg)
    p = math.atan2(v.z, max(vh.length, 1e-4))
    d = hd * math.cos(p) + Vector((0, 0, math.sin(p))); up = -hd * math.sin(p) + Vector((0, 0, math.cos(p)))
    q0 = Quaternion(d, rad(roll_at(t))); up = q0 @ up
    right = d.cross(up)
    from mathutils import Matrix
    M = Matrix((right, up, -d)).transposed()
    return P, M.to_quaternion()

camd = bpy.data.cameras.new('cam'); camd.lens = 15; camd.sensor_width = 36; camd.clip_start = 0.04; camd.clip_end = 5000
cam = bpy.data.objects.new('camera', camd); col.objects.link(cam); scene.camera = cam; cam.rotation_mode = 'QUATERNION'
world = bpy.data.worlds.new('world'); scene.world = world
SKY = [(0, (0.86, 0.92, 0.98)), (9, (0.80, 0.89, 0.98)), (17, (0.97, 0.90, 0.76)), (22, (0.99, 0.80, 0.60)), (26, (0.98, 0.66, 0.58)), (30.1, (0.86, 0.56, 0.80))]
SEAC = [(0, (0.45, 0.72, 0.86)), (17, (0.48, 0.70, 0.82)), (24, (0.80, 0.66, 0.62)), (30.1, (0.78, 0.52, 0.70))]
def ramp(keys, t):
    for (ta, ca), (tb, cb) in zip(keys, keys[1:]):
        if ta <= t <= tb:
            s = (t - ta) / (tb - ta); return tuple(lin(ca[i] + (cb[i] - ca[i]) * s) for i in range(3))
    return tuple(lin(c) for c in keys[-1][1])

# precompute when she passes each falling box
for f in FALLERS:
    tt = 14.3
    while tt < 19.5 and SP(tt).y > f[1].y:
        tt += 0.02
    f[4] = tt + random.uniform(0.05, 0.4)

ANIM = [cam, sk, body, torso, hairj, pcar, sun, door_l, door_r] + list(J.values()) + [o[0] for o in ORANGES] + [f[0] for f in FALLERS] + [m[0] for m in MOVERS]
_prevq = [None]
def apply(t):
    P, q = cam_state(t)
    if _prevq[0] is not None and q.dot(_prevq[0]) < 0:
        q.negate()
    _prevq[0] = q.copy(); cam.location = P; cam.rotation_quaternion = q
    camd.lens = 22 - 7 * smooth(1.5, 4.5, t)
    S = SP(t); h = sk_heading(t); d = pose(t)
    yaw = math.atan2(-h.x, h.y) + 2 * math.pi * smooth(10.9, 11.9, t)
    sk.location = (S.x, S.y, ground(S.x) + zjump(t)); sk.rotation_euler = (0, 0, yaw)
    body.location = (0, 0, 1.0 + d['zoff']); torso.rotation_euler = (-d['lean'], 0, 0); hairj.rotation_euler = (d['hair'], 0, 0)
    J['hipL'].rotation_euler = (d['hLx'], d['hLy'], 0); J['hipR'].rotation_euler = (d['hRx'], -d['hRy'], 0)
    J['kneeL'].rotation_euler = (d['kL'], 0, 0); J['kneeR'].rotation_euler = (d['kR'], 0, 0)
    J['shL'].rotation_euler = (d['sLx'], d['sLy'], 0); J['shR'].rotation_euler = (d['sRx'], -d['sRy'], 0)
    J['elL'].rotation_euler = (d['eL'], 0, 0); J['elR'].rotation_euler = (d['eR'], 0, 0)
    op = bump(t, 13.5, 14.0, 15.2, 15.8) * 1.35
    door_l.location.x = 49.3 - op; door_r.location.x = 50.7 + op
    for o, p0, v, dl in ORANGES:
        tau = t - T_ORANGE - dl
        if tau <= 0:
            o.location = p0; continue
        r = 0.115; tf = (v.z + math.sqrt(v.z * v.z + 19.6 * (p0.z - r))) / 9.8
        if tau < tf:
            o.location = (p0.x + v.x * tau, p0.y + v.y * tau, p0.z + v.z * tau - 4.9 * tau * tau)
        else:
            e = (1 - math.exp(-0.45 * (tau - tf))) / 0.45
            o.location = (min(51.3, max(48.7, p0.x + v.x * tf + v.x * 0.4 * e)), p0.y + v.y * tf + v.y * 0.85 * e, r + 0.035)
    for o, p0, v, wv, t0 in FALLERS:
        tau = t - t0
        if tau <= 0:
            o.location = p0; o.rotation_euler = (0, 0, 0); continue
        tf = (v.z + math.sqrt(v.z * v.z + 19.6 * (p0.z - 0.16))) / 9.8; tc = min(tau, tf)
        o.location = (p0.x + v.x * tc, p0.y + v.y * tc, max(0.16, p0.z + v.z * tc - 4.9 * tc * tc))
        o.rotation_euler = (wv.x * tc, wv.y * tc, wv.z * tc) if tau < tf else (math.pi / 2, 0, wv.z * tf)
    pcar.location = (car_x(t), 15.0, 0)
    sun.location = (-900, 40, -300 if t < 17.5 else 345 - (t - 17.5) * 25.6)
    for o, x, y0, v in MOVERS:
        o.location = (x, y0 + v * t, 0)
    world.color = ramp(SKY, t); SEA.diffuse_color = ramp(SEAC, t) + (1.0,)

# ------------------------------------------------------------------ render setup
scene.render.engine = 'BLENDER_WORKBENCH'
shd = scene.display.shading
shd.light = 'STUDIO'; shd.color_type = 'TEXTURE'; shd.show_shadows = False; shd.show_cavity = False
shd.show_object_outline = False; shd.show_specular_highlight = False
try:
    shd.use_world_space_lighting = False
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
    apply(f / FPS); scene.frame_set(f); apply(f / FPS)
    bpy.context.view_layer.update()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

if MODE == 'stills':
    for ts in arg('--times', '0').split(','):
        render_frame(int(round(float(ts) * FPS)), os.path.join(OUT, 's_%05.2f.jpg' % float(ts)))
elif MODE == 'anim':
    a = int(arg('--start', '0')); b = int(arg('--end', str(NF - 1)))
    for f in range(a, b + 1):
        p = os.path.join(OUT, 'f_%04d.jpg' % f)
        if not os.path.exists(p):
            render_frame(f, p)
elif MODE == 'blend':
    for f in range(0, NF):
        apply(f / FPS)
        for o in ANIM:
            o.keyframe_insert('location', frame=f)
            o.keyframe_insert('rotation_quaternion' if o.rotation_mode == 'QUATERNION' else 'rotation_euler', frame=f)
        world.keyframe_insert('color', frame=f); SEA.keyframe_insert('diffuse_color', frame=f); camd.keyframe_insert('lens', frame=f)
    scene.frame_set(0)
    for img in bpy.data.images:
        try:
            img.pack()
        except Exception:
            pass
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'rollertake.blend'))
    print('saved blend', flush=True)
