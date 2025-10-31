import random, heapq, pygame, math
import os

# tamaño del tile
TILE = 16
# dimensiones del mapa
MAP_W, MAP_H = 200, 150

# tipos de celda
EMPTY, WALL, FOREST, MINE, WATER, GRANARY, HOME, FARM = range(8)
TOWER, WALL_DEF, DOOR, HOSPITAL = 8, 9, 10, 11


TREE_IMG = None
MINE_IMG = None
TOWER_IMG = None
HOSPITAL_IMG = None
WALL_IMG = None
PONCHO_IMGS = [] 
BOSS_IMGS = []


def load_tree_sprite():
    global TREE_IMG
    base_path = os.path.dirname(__file__)
    sprites_path = os.path.join(base_path, "sprites")
    img_path = os.path.join(sprites_path, "tree.png")
    if os.path.exists(img_path):
        TREE_IMG = pygame.image.load(img_path).convert_alpha()
        factor = 1.3
        TREE_IMG = pygame.transform.scale(TREE_IMG, (int(TILE*factor), int(TILE*factor)))
    else:
        TREE_IMG = None

def load_mine_sprite():
    global MINE_IMG
    base_path = os.path.dirname(__file__)
    sprites_path = os.path.join(base_path, "sprites")
    img_path = os.path.join(sprites_path, "mineral.png")
    if os.path.exists(img_path):
        MINE_IMG = pygame.image.load(img_path).convert_alpha()
        factor = 1.6
        MINE_IMG = pygame.transform.scale(MINE_IMG, (int(TILE*factor), int(TILE*factor)))
    else:
        MINE_IMG = None

def load_tower_sprite():
    global TOWER_IMG
    base_path = os.path.dirname(__file__)
    sprites_path = os.path.join(base_path, "sprites")
    img_path = os.path.join(sprites_path, "cholet.png")
    if os.path.exists(img_path):
        TOWER_IMG = pygame.image.load(img_path).convert_alpha()
        TOWER_IMG = pygame.transform.scale(TOWER_IMG, (int(TILE*4), int(TILE*4)))
    else:
        TOWER_IMG = None

def load_hospital_sprite():
    global HOSPITAL_IMG
    base_path = os.path.dirname(__file__)
    sprites_path = os.path.join(base_path, "sprites")
    img_path = os.path.join(sprites_path, "cholet2.png")
    if os.path.exists(img_path):
        HOSPITAL_IMG = pygame.image.load(img_path).convert_alpha()
        HOSPITAL_IMG = pygame.transform.scale(HOSPITAL_IMG, (int(TILE*4), int(TILE*4)))
    else:
        HOSPITAL_IMG = None

def load_boss_sprites():
    #cargar sprites boss, circulo si no funciona
    global BOSS_IMGS
    BOSS_IMGS = []

    base_path = os.path.dirname(__file__)
    sprites_path = os.path.join(base_path, "sprites")

    file_names = ["boss1.png", "boss2.png"]

    factor = 2.2  # jefe más grande

    print("=== [load_boss_sprites] ===")
    print("Buscando sprites del jefe en:", sprites_path)

    for name in file_names:
        img_path = os.path.join(sprites_path, name)
        print("  Intentando cargar:", img_path)

        if not os.path.exists(img_path):
            print(" NO EXISTE:", img_path)
            continue

        try:
            img = pygame.image.load(img_path).convert_alpha()
            w = int(TILE * factor)
            h = int(TILE * factor)
            img = pygame.transform.scale(img, (w, h))
            BOSS_IMGS.append(img)
            print(f"Cargado {name} ({w}x{h})")
        except Exception as e:
            print(" Error cargando", name, "->", e)

    print("Total frames jefe cargados:", len(BOSS_IMGS))
    print("============================")
def load_wall_sprite():
    global WALL_IMG
    base_path = os.path.dirname(__file__)
    sprites_path = os.path.join(base_path, "sprites")
    img_path = os.path.join(sprites_path, "wall.png")
    if os.path.exists(img_path):
        WALL_IMG = pygame.image.load(img_path).convert_alpha()
        factor = 1.6 
        WALL_IMG = pygame.transform.scale(WALL_IMG, (int(TILE*factor), int(TILE*factor)))
    else:
        WALL_IMG = None
        print("Warning: wall.png sprite not found.")

# paleta
COLORS = {
    EMPTY:   (130, 200, 140),
    WALL:    (80,  85,  95),
    FOREST:  (40,  180, 50),
    MINE:    (160, 130, 90),
    WATER:   (60,  120, 220),
    GRANARY: (230, 210, 100),
    HOME:    (130, 160, 255),
    FARM:    (200, 150, 70),
    TOWER:   (255, 240, 100),
    WALL_DEF:(180, 180, 180),
    DOOR:    (200, 160, 110),
    HOSPITAL:(255, 130, 180),
}

def shade(c, k):
    r,g,b = c
    return (max(0,min(255,int(r*k))),
            max(0,min(255,int(g*k))),
            max(0,min(255,int(b*k))))

def manhattan(a,b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

class MapGrid:
    def __init__(self, w=MAP_W, h=MAP_H):
        self.w, self.h = w, h
        self.grid = [[EMPTY for _ in range(w)] for _ in range(h)]
        self.resource_amount = {}
        self.idx = {FOREST:set(), MINE:set(), FARM:set(), HOSPITAL:set()}
        self._generate()

    def _place(self, kind, count, lo=0, hi=0):
        placed = 0
        while placed < count:
            x,y = random.randint(1,self.w-2), random.randint(1,self.h-2)
            if self.grid[y][x]==EMPTY:
                self.grid[y][x] = kind
                if kind in (FOREST, MINE, FARM):
                    self.resource_amount[(x,y)] = random.randint(lo,hi)
                    self.idx[kind].add((x,y))
                placed += 1

    def _stamp_water_ellipse(self, cx, cy, rx, ry, rough=0.0):
        for y in range(cy - ry, cy + ry + 1):
            if y <= 0 or y >= self.h-1: continue
            for x in range(cx - rx, cx + rx + 1):
                if x <= 0 or x >= self.w-1: continue
                nx = (x - cx) / max(1, rx)
                ny = (y - cy) / max(1, ry)
                inside = (nx*nx + ny*ny) <= 1.0 + (random.random()-0.5)*rough
                if inside and self.grid[y][x] != WALL:
                    self.grid[y][x] = WATER

    def _carve_river(self, a, b, width=2):
        (x0, y0), (x1, y1) = a, b
        steps = max(abs(x1-x0), abs(y1-y0))
        if steps == 0: return
        for i in range(1, steps+1):
            t = i/steps
            x = int(round(x0 + (x1-x0)*t + random.randint(-1,1)))
            y = int(round(y0 + (y1-y0)*t + random.randint(-1,1)))
            for oy in range(-width, width+1):
                for ox in range(-width, width+1):
                    xx, yy = x+ox, y+oy
                    if 1 <= xx < self.w-1 and 1 <= yy < self.h-1:
                        if self.grid[yy][xx] != WALL:
                            self.grid[yy][xx] = WATER

    def _place_water_blobs(self, lakes=12, rmin=4, rmax=9, connect_prob=0.55):
        lake_centers = []
        for _ in range(lakes):
            cx = random.randint(3, self.w-4)
            cy = random.randint(3, self.h-4)
            rx = random.randint(rmin, rmax)
            ry = random.randint(max(3, rmin-1), rmax)
            self._stamp_water_ellipse(cx, cy, rx, ry, rough=0.25)
            lake_centers.append((cx, cy))
        random.shuffle(lake_centers)
        for i in range(len(lake_centers)-1):
            if random.random() < connect_prob:
                self._carve_river(lake_centers[i], lake_centers[i+1], width=1)

    def _generate(self):
        for x in range(self.w):
            self.grid[0][x] = self.grid[self.h-1][x] = WALL
        for y in range(self.h):
            self.grid[y][0] = self.grid[y][self.w-1] = WALL

        area = self.w * self.h
        self._place(FOREST, int(area*0.10), 4, 8)
        self._place(MINE,   int(area*0.06), 3, 6)
        self._place(FARM,   int(area*0.05), 5,10)
        self._place_water_blobs(lakes=12, rmin=4, rmax=9, connect_prob=0.55)

        self.home    = (2,2)
        self.granary = (self.w-3, self.h-3)
        self.grid[self.home[1]][self.home[0]]       = HOME
        self.grid[self.granary[1]][self.granary[0]] = GRANARY

    def in_bounds(self, x, y): return 0 <= x < self.w and 0 <= y < self.h

    def is_empty(self, x, y):
        return self.in_bounds(x,y) and self.grid[y][x] == EMPTY

    def is_buildable(self, x, y):
        if not self.in_bounds(x,y): return False
        k = self.grid[y][x]
        if k in (WALL, WATER, HOME, GRANARY): return False
        if (x,y) in self.resource_amount: return False
        return k == EMPTY

    def set_tile(self, x, y, kind):
        if self.in_bounds(x,y):
            self.grid[y][x] = kind
            if kind == HOSPITAL:
                self.idx[HOSPITAL].add((x,y))

    def neighbors(self,x,y):
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny = x+dx, y+dy
            if 0<=nx<self.w and 0<=ny<self.h:
                if self.grid[ny][nx] in (WALL, WALL_DEF, TOWER, WATER):
                    continue
                yield nx,ny

    def astar(self, start, goal):
        if not goal or start == goal:
            return []
        sx,sy = start; gx,gy = goal
        if not self.in_bounds(gx,gy):
            return []
        openh=[]; heapq.heappush(openh,(0,start))
        came={start:None}; g={start:0}
        while openh:
            _,cur = heapq.heappop(openh)
            if cur==goal: break
            for nx,ny in self.neighbors(*cur):
                ng=g[cur]+1
                if (nx,ny) not in g or ng<g[(nx,ny)]:
                    g[(nx,ny)]=ng
                    f=ng+abs(nx-gx)+abs(ny-gy)
                    heapq.heappush(openh,(f,(nx,ny)))
                    came[(nx,ny)]=cur
        if goal not in came:
            return []
        path=[]; cur=goal
        while cur and cur!=start:
            path.append(cur); cur=came[cur]
        path.reverse()
        return path

    def consume_resource(self, x, y):
        if (x,y) in self.resource_amount:
            self.resource_amount[(x,y)] -= 1
            if self.resource_amount[(x,y)] <= 0:
                del self.resource_amount[(x,y)]
                kind = self.grid[y][x]
                if kind in self.idx and (x,y) in self.idx[kind]:
                    self.idx[kind].remove((x,y))
                self.grid[y][x] = EMPTY

    def positions_for(self, tile_type):
        if tile_type in self.idx:
            return self.idx[tile_type]
        if tile_type == HOME:
            return {self.home}
        if tile_type == GRANARY:
            return {self.granary}
        out=set()
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x]==tile_type:
                    out.add((x,y))
        return out

    # dibujo
    def _draw_beveled(self, surf, x, y, base):
        rect = pygame.Rect(x, y, TILE, TILE)
        pygame.draw.rect(surf, base, rect, border_radius=3)
        pygame.draw.rect(surf, shade(base, 0.75), (x, y+TILE-4, TILE, 4), border_radius=2)
        pygame.draw.rect(surf, shade(base, 1.12), (x, y, TILE, 3), border_radius=2)

    def _draw_detail(self, surf, x, y, kind, tick):
        if (x//TILE, y//TILE) in self.resource_amount:
            v = self.resource_amount[(x//TILE, y//TILE)]
            dots = min(3, v)
            for i in range(dots):
                ox = 2 + (i*4 + (tick//6)%3) % (TILE-6)
                oy = TILE-6 - (i*2)
                pygame.draw.rect(surf, (255, 180, 80), (x+ox, y+oy, 3, 3))

        if kind == MINE and MINE_IMG:
            offset = int(1.0 * math.sin((x + y + tick) * 0.04))
            rect = MINE_IMG.get_rect(center=(x + TILE // 2, y + TILE // 2 + offset))
            surf.blit(MINE_IMG, rect)
        elif kind == FOREST and TREE_IMG:
            offset = int(1.5 * math.sin((x + y + tick) * 0.05))
            surf.blit(TREE_IMG, (x, y + offset))
        elif kind == WATER:
            k = 1.0 + 0.08*math.sin((x*0.4+y*0.3+tick)*0.08)
            pygame.draw.rect(surf, shade(COLORS[WATER], k), (x+2, y+2, TILE-4, TILE-6), border_radius=3)
        elif kind == WALL_DEF:
                    if WALL_IMG:
                        rect = WALL_IMG.get_rect(center=(x + TILE // 2, y + TILE // 2))
                        surf.blit(WALL_IMG, rect)
                    else:
                        pygame.draw.rect(surf, shade(COLORS[WALL_DEF], 0.9), (x+2, y+6, TILE-4, TILE-6), border_radius=2)
        elif kind == DOOR:
            pygame.draw.rect(surf, shade(COLORS[DOOR], 1.0), (x+2, y+6, TILE-4, TILE-6), border_radius=2)
            pygame.draw.rect(surf, shade(COLORS[DOOR], 1.2), (x+6, y+4, TILE-12, TILE-4), border_radius=2)

    def draw(self, surf, camx=0, camy=0, view_w=50, view_h=36, tick=0):
        for vy in range(view_h):
            y = camy + vy
            if y < 0 or y >= self.h:
                continue
            for vx in range(view_w):
                x = camx + vx
                if x < 0 or x >= self.w:
                    continue
                kind = self.grid[y][x]
                base = COLORS[kind]
                px, py = vx * TILE, vy * TILE
                self._draw_beveled(surf, px, py, base)
                self._draw_detail(surf, px, py, kind, tick)

        if 'TOWER_IMG' in globals() and TOWER_IMG:
            for (x, y) in self.positions_for(TOWER):
                px = (x - camx) * TILE
                py = (y - camy) * TILE
                rect = TOWER_IMG.get_rect(midbottom=(px + TILE/2, py + TILE + 2))
                surf.blit(TOWER_IMG, rect)

        if 'HOSPITAL_IMG' in globals() and HOSPITAL_IMG:
            for (x, y) in self.positions_for(HOSPITAL):
                px = (x - camx) * TILE
                py = (y - camy) * TILE
                rect = HOSPITAL_IMG.get_rect(midbottom=(px + TILE/2, py + TILE + 2))
                surf.blit(HOSPITAL_IMG, rect)
