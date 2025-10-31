import pygame
from world import TILE
import random
from collections import deque
import os

# tiempos
WORK_TIMES = {
    "wood":         18,
    "mine":         22,
    "farm":         18,
    "build":        24,
    "defend":       10,
    "hunt":         18,
    "build_at":     28,
    "heal":         18,
}

DWARF_NAMES = ["Edman","Huanca","Choque","Mamani","Wanka","Morales","Condori","Condorcanqui","Pumari"]
DWARF_LASTNAMES = ["Huanca","Choque","Mamani","Wanka","Morales","Condori","Condorcanqui","Pumari"]

OFFICES = ["Leñador","Minero","Cazador","Constructor","Granjero","Guardia"]
COLOR_OFICIO = {
    "Leñador":    (230,180, 60),
    "Minero":     (100,100,100),
    "Cazador":    (200, 70, 70),
    "Constructor":( 80,160,200),
    "Granjero":   (160,120, 60),
    "Guardia":    (100,180,255),
}

SUIT_MAP = {
    "Leñador":    {"wood"},
    "Minero":     {"mine"},
    "Granjero":   {}, 
    "Constructor":{"build","build_at"},
    "Cazador":    {"hunt"},
    "Guardia":    {"defend"},
}

SPEED_MULT = {"match": 0.55, "neutral": 0.9, "mismatch": 1.1}

def suitability(oficio: str, task: str) -> int:
    if task in SUIT_MAP.get(oficio, set()):
        return 3
    return 2

class DwarfBase:
    idle_img = None
    walk_imgs = []
    dead_img = None

    @classmethod
    def load_images(cls):
        base_path = os.path.dirname(__file__)
        sprites_path = os.path.join(base_path, "sprites")

        idle = os.path.join(sprites_path, "dwarf_idle.png")
        w1   = os.path.join(sprites_path, "dwarf_walk1.png")
        w2   = os.path.join(sprites_path, "dwarf_walk2.png")
        dead = os.path.join(sprites_path, "dwarf_dead.png")

        cls.idle_img = pygame.image.load(idle).convert_alpha()
        w1img = pygame.image.load(w1).convert_alpha()
        w2img = pygame.image.load(w2).convert_alpha()
        deadimg = pygame.image.load(dead).convert_alpha()

        factor = 2
        cls.idle_img = pygame.transform.scale(cls.idle_img, (int(TILE*factor), int(TILE*factor)))
        cls.walk_imgs = [
            pygame.transform.scale(w1img, (int(TILE*factor), int(TILE*factor))),
            pygame.transform.scale(w2img, (int(TILE*factor), int(TILE*factor))),
        ]
        cls.dead_img = pygame.transform.scale(deadimg, (int(TILE*factor), int(TILE*factor)))

    def __init__(self, x, y):
        self.name   = f"{random.choice(DWARF_NAMES)} {random.choice(DWARF_LASTNAMES)}"
        self.oficio = random.choice(OFFICES)
        self.color  = COLOR_OFICIO[self.oficio]
        self.x, self.y = x, y
        self.sx, self.sy = x*TILE, y*TILE
        if self.oficio == "Guardia":
            self.energy = 150 #vida guard
        else:
            self.energy = 100
        self.state  = "Idle"
        self.task   = "idle"
        self.timer  = 0
        self.path   = deque()
        self.order_priority = 0
        self.meta = {}
        self.manual_hold = False 

    def current_work_time(self):
        base = WORK_TIMES.get(self.task, 12)
        if self.task in SUIT_MAP.get(self.oficio, set()):
            mult = SPEED_MULT["match"]
        else:
            mult = SPEED_MULT["mismatch"]
        return int(max(6, base * mult))

    def assign_task(self, task, path, priority=1, meta=None):
        if self.state == "Muerto":
            return
        if priority >= self.order_priority:
            self.task = task
            self.path = deque(path)
            self.state = "Yendo" if path else "Trabajando"
            self.timer = 0
            self.order_priority = priority
            self.meta = meta or {}

    def cancel_task(self):
        self.task = "idle"
        self.path.clear()
        self.state = "Idle"
        self.timer = 0
        self.order_priority = 0
        self.meta = {}
        # manual

    def move(self):
        if self.state in ("Muerto", "Idle"):
            return

        if self.state == "Yendo" and self.path:
            nx, ny = self.path[0]
            if nx is None or ny is None:
                self.cancel_task()
                return

            if self.x < nx: self.x += 1
            elif self.x > nx: self.x -= 1
            if self.y < ny: self.y += 1
            elif self.y > ny: self.y -= 1

            if int(self.x) == nx and int(self.y) == ny:
                try:
                    self.path.popleft()
                except IndexError:
                    pass

            if not self.path:
                self.state = "Trabajando"
                self.timer = 0

        elif self.state == "Trabajando":
            self.timer += 1
            if self.timer >= self.current_work_time():
                self.state = "Idle"
                self.task = "idle"
                self.timer = 0
                self.order_priority = 0
                # manual_hold no se toca
                self.meta = {}

    def defend(self):
        self.state = "Defendiendo"
        self.timer = 8

    def tick_stats(self, world):
        if self.state == "Trabajando":
            self.energy = max(0, self.energy - 0.015)
        elif self.state == "Idle":
            self.energy = min(100, self.energy + 0.07)
        elif self.state == "Defendiendo":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "Idle"

    def die(self):
        self.state = "Muerto"
        self.energy = 0
        self.task = "none"
        self.path.clear()
        self.timer = 0
        self.order_priority = -1
        self.meta = {}
        # manual no importa


class PonchoRojo:
    idle_img = None
    walk_imgs = []

    @classmethod
    def load_images(cls):
        base_path = os.path.dirname(__file__)
        sprites_path = os.path.join(base_path, "sprites")
        idle = os.path.join(sprites_path, "poncho_idle.png")
        w1 = os.path.join(sprites_path, "poncho_walk1.png")
        w2 = os.path.join(sprites_path, "poncho_walk2.png")

        cls.idle_img = pygame.image.load(idle).convert_alpha()
        cls.walk_imgs = [pygame.image.load(w1).convert_alpha(), pygame.image.load(w2).convert_alpha()]

        factor = 1.8
        cls.idle_img = pygame.transform.scale(cls.idle_img, (int(TILE*factor), int(TILE*factor)))
        cls.walk_imgs = [pygame.transform.scale(i, (int(TILE*factor), int(TILE*factor))) for i in cls.walk_imgs]
    def __init__(self, x, y, world_map=None, hp=500):
        # posición en grid
        self.x = float(x)
        self.y = float(y)
        self.state = "Idle"
        self.hp = hp    
        self.max_hp = hp 
        self.target = None
        self.speed = 0.12
        self.timer = 0
        self.lifetime = None
        self.is_boss = False
        self.map = world_map
        self.path = deque()
        self.repath_cd = 0

    def _pick_target(self, dwarves):
        vivos = [d for d in dwarves if d.state != "Muerto"]
        if not vivos:
            self.target = None
            return
        self.target = min(
            vivos,
            key=lambda d: abs(int(d.x) - int(self.x)) + abs(int(d.y) - int(self.y))
        )

    def _repath(self):
        if not self.map or not self.target:
            return
        start = (int(round(self.x)), int(round(self.y)))
        goal  = (int(self.target.x), int(self.target.y))
        path = self.map.astar(start, goal)
        if path:
            self.path = deque(path)
        else:
            self.path = deque()

    def _step_along_path(self):
        if not self.path:
            self.state = "Idle"
            return

        nx, ny = self.path[0]
        dx = nx - self.x
        dy = ny - self.y

        moved = False
        if abs(dx) > 0.05:
            self.x += self.speed * (1 if dx > 0 else -1)
            moved = True
        if abs(dy) > 0.05:
            self.y += self.speed * (1 if dy > 0 else -1)
            moved = True

        if abs(self.x - nx) < 0.1 and abs(self.y - ny) < 0.1:
            self.x = nx
            self.y = ny
            try:
                self.path.popleft()
            except IndexError:
                pass

        self.state = "Walk" if moved else "Idle"

    def attack(self, target):
        self.state = "Attack"
        target.energy -= 0.25
        if target.energy <= 0 and target.state != "Muerto":
            target.die()

    def update(self, dwarves, world_map):
        # asegurar referencia al mapa
        if not self.map:
            self.map = world_map

        # vida 
        if self.hp <= 0:
            return

        # elegir enano para atacar
        if (not self.target) or (self.target.state == "Muerto"):
            self._pick_target(dwarves)

        if self.target:
            tx = int(self.target.x)
            ty = int(self.target.y)
            dist = abs(tx - int(self.x)) + abs(ty - int(self.y))

            if dist <= 1:
                # pegar
                self.attack(self.target)
                self.state = "Attack"
                return

            # acercar
            self.repath_cd -= 1
            if self.repath_cd <= 0 or not self.path:
                self._repath()
                self.repath_cd = 30

            self._step_along_path()
        else:
            self.state = "Idle"


class PonchoJefe(PonchoRojo):
    def __init__(self, x, y, world_map=None, hp=3000):
        super().__init__(x, y, world_map, hp=hp)
        self.speed = 0.06
        self.is_boss = True
        self.lifetime = None 
        
        self.anim_timer = random.randint(0, 15) 
        self.frame_idx = 0

    def update(self, dwarves, world_map):
        #anum jefe
        self.anim_timer += 1
        if self.anim_timer >= 15: #vel anim
            self.frame_idx = (self.frame_idx + 1) % 2 #0 o 1
            self.anim_timer = 0
        
        # update
        super().update(dwarves, world_map)

class Llama:
    idle_img = None
    walk_imgs = []

    @classmethod
    def load_images(cls):
        try:
            base_path = os.path.dirname(__file__)
            sprites_path = os.path.join(base_path, "sprites")
            idle = os.path.join(sprites_path, "llama_idle.png")
            w1   = os.path.join(sprites_path, "llama_walk1.png")
            w2   = os.path.join(sprites_path, "llama_walk2.png")

            cls.idle_img = pygame.image.load(idle).convert_alpha()
            cls.walk_imgs = [pygame.image.load(w1).convert_alpha(), pygame.image.load(w2).convert_alpha()]

            factor = 1.6
            cls.idle_img = pygame.transform.scale(cls.idle_img, (int(TILE*factor), int(TILE*factor)))
            cls.walk_imgs = [pygame.transform.scale(i, (int(TILE*factor), int(TILE*factor))) for i in cls.walk_imgs]
        except Exception as e:
            print(f"Warning: No se pudieron cargar los sprites de Llama: {e}")
            # --- FALLBACK MEJORADO ---
            fallback_img = pygame.Surface((int(TILE*1.4), int(TILE*1.4)), pygame.SRCALPHA)
            fallback_img.fill((220, 220, 200))
            cls.idle_img = fallback_img
            cls.walk_imgs = [fallback_img, fallback_img]

    def __init__(self, x, y, world_map):
        self.x, self.y = float(x), float(y) # mov suave
        self.sx, self.sy = x * TILE, y * TILE
        self.state = "Idle"
        self.map = world_map
        self.path = deque()
        self.timer = random.randint(60, 180)
        self.speed = 0.04
        self.hp = 100 # vida llama

    def die(self):
        self.state = "Muerto"
        self.hp = 0
        self.path.clear()

    def update(self):
        if self.hp <= 0 or self.state == "Muerto":
            return # si esta mierta
        
        self.timer -= 1
        if self.state == "Idle" and self.timer <= 0:
            tx, ty = self.x, self.y
            for _ in range(5):
                tx = random.randint(int(self.x) - 10, int(self.x) + 10)
                ty = random.randint(int(self.y) - 10, int(self.y) + 10)
                if self.map.is_empty(tx, ty):
                    break
            path = self.map.astar((int(self.x), int(self.y)), (tx, ty))
            if path:
                self.path = deque(path)
                self.state = "Walk"

        elif self.state == "Walk":
            if not self.path:
                self.state = "Idle"
                self.timer = random.randint(120, 300)
                return

            nx, ny = self.path[0]
            dx = nx - self.x
            dy = ny - self.y

            if abs(dx) > 0.1: self.x += self.speed * (1 if dx > 0 else -1)
            if abs(dy) > 0.1: self.y += self.speed * (1 if dy > 0 else -1)

            if abs(self.x - nx) < 0.1 and abs(self.y - ny) < 0.1:
                self.x, self.y = nx, ny
                try: self.path.popleft()
                except IndexError: pass

    def draw(self, surf, camx, camy, tick):
        if self.state == "Muerto":
            return # No dibujar si esta muerta

        cx = int((self.x - camx) * TILE) + TILE//2
        cy = int((self.y - camy) * TILE) + TILE//2

        pygame.draw.ellipse(surf, (0,0,0,60), (cx-5, cy+5, 10, 5))

        if self.state == "Walk":
            img = self.walk_imgs[(tick // 15) % 2]
        else:
            img = self.idle_img

        rect = img.get_rect(center=(cx, cy))
        surf.blit(img, rect)
