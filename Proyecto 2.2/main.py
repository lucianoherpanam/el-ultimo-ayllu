import pygame, math, random
import world
from world import (
    MapGrid, TILE, load_tree_sprite, load_mine_sprite, load_tower_sprite, load_hospital_sprite, 
    load_wall_sprite, load_boss_sprites,
    EMPTY, WALL, FOREST, MINE, WATER, FARM,
    TOWER, WALL_DEF, HOSPITAL, HOME, GRANARY, COLORS,
    BOSS_IMGS
)
from actors import DwarfBase, PonchoRojo, PonchoJefe, Llama
from planner import Planner
from events import EventManager

FPS = 60
STEP_DELAY = 10
INFO_WIDTH = 360
DEFAULT_ORDER_AMOUNT = 1

VIEW_W_TILES = 50
VIEW_H_TILES = 36

PANEL_BG = (22, 22, 26)
PANEL_ACCENT = (255, 220, 90)
TEXT_DIM = (200, 200, 200)

def lerp(a,b,t): return a + (b-a)*t
def clamp(x,a,b): return a if x<a else b if x>b else x

BUILD_NONE, BUILD_WALL, BUILD_TOWER, BUILD_HOSP = range(4)

class Projectile:
    def __init__(self, x_px, y_px, target, T=28, g=0.45):
        self.x = x_px
        self.y = y_px
        self.target = target
        self.g = g
        self.life = T + 10
        tx = (target.x) * TILE + TILE*0.5
        ty = (target.y) * TILE + TILE*0.5
        dx = tx - self.x
        dy = ty - self.y
        self.vx = dx / T
        self.vy = (dy - 0.5 * g * T * T) / T

    def update(self):
        if self.life <= 0:
            return False
        self.x += self.vx
        self.y += self.vy
        self.vy += self.g
        self.life -= 1

        if self.target and self.target.hp > 0:
            tx = self.target.x * TILE + TILE * 0.5
            ty = self.target.y * TILE + TILE * 0.5
            close = (abs(self.x - tx) < 10 and abs(self.y - ty) < 10)
            if close or self.life <= 0:
                damage = random.randint(40, 70)
                self.target.hp -= damage
                if self.target.hp <= 0:
                    self.target.hp = 0
                    print("poncho Rojo eliminado")
                return False
        return True

    def draw(self, surf, camx, camy):
        px = int(self.x - camx*TILE)
        py = int(self.y - camy*TILE)
        pygame.draw.circle(surf, (210,210,210), (px,py), 3)

class Particle:
    def __init__(self, x_px, y_px, text="+1", color=(255, 255, 255), lifetime=30, speed=-0.8):
        self.x = x_px
        self.y = y_px
        self.text = text
        self.color = color
        self.lifetime = lifetime
        self.speed = speed
        self.alpha = 255

    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0:
            return False
        self.y += self.speed
        self.alpha = max(0, int(255 * (self.lifetime / 30)))
        return True

    def draw(self, surf, camx, camy, font):
        if self.lifetime <= 0:
            return
        px = int(self.x - camx*TILE)
        py = int(self.y - camy*TILE)
        text_surf = font.render(self.text, True, self.color)
        text_surf.set_alpha(self.alpha)
        surf.blit(text_surf, (px, py))

class Game:
    def __init__(self):
        world.load_boss_sprites()
        print("DEBUG post-load: frames jefe =", len(world.BOSS_IMGS))
        pygame.init()
        # tamaño juego
        self.GAME_WIDTH = VIEW_W_TILES*TILE + INFO_WIDTH
        self.GAME_HEIGHT = VIEW_H_TILES*TILE

        #título
        pygame.display.set_caption("Proyecto DwarF: Visual Deluxe")
        #SCALED
        self.screen = pygame.display.set_mode(
            (self.GAME_WIDTH, self.GAME_HEIGHT), 
            pygame.FULLSCREEN | pygame.SCALED
        )
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = True

        DwarfBase.load_images()
        PonchoRojo.load_images()
        Llama.load_images()
        load_tree_sprite()
        load_mine_sprite()
        load_tower_sprite()
        load_hospital_sprite()
        load_wall_sprite()
        load_boss_sprites()

        self.map = MapGrid()
        self.font = pygame.font.SysFont("consolas", 18, bold=True)
        self.small = pygame.font.SysFont("consolas", 12)
        self.cam_x, self.cam_y = 0, 0
        self.ticks = 0

        self.dwarves = self._spawn_dwarves(4)
        for d in self.dwarves:
            d.sx = (d.x - self.cam_x)*TILE + TILE//2
            d.sy = (d.y - self.cam_y)*TILE + TILE//2

        self.llamas = []
        for _ in range(5):
            hx, hy = self.map.home
            lx = random.randint(hx, hx + 10)
            ly = random.randint(hy, hy + 10)
            if self.map.in_bounds(lx, ly) and self.map.grid[ly][lx] != WATER:
                self.llamas.append(Llama(lx, ly, self.map))

        self.resources = {"wood": 0, "stone": 0, "food": 0}
        self.towers = []
        self.projectiles = []
        self.particles = []

        self.planner = Planner(self)
        self.events = EventManager(self.planner, self, enabled=True, view_w=VIEW_W_TILES, view_h=VIEW_H_TILES)
        self.ponchos = []

        hx, hy = self.map.home
        self.center_camera(hx, hy)

        self.step_counter = 0

        self.cost_tower = {"wood": 5, "stone": 3}
        self.cost_wall  = {"stone": 2}
        self.cost_hosp  = {"wood": 4, "stone": 4}

        self.tower_range = 7
        self.tower_cooldown = 26

        self.build_mode = BUILD_NONE
        self.heal_rate = 0.6
        self.selected_dwarf = None
        self.defense_mode = False
        self.panel_scroll_y = 0       
        self.panel_content_height = 0 

    # cámara
    def _snap_smooth_positions(self):
        for d in self.dwarves:
            d.sx = (d.x - self.cam_x)*TILE + TILE//2
            d.sy = (d.y - self.cam_y)*TILE + TILE//2

    def center_camera(self, tx, ty):
        self.cam_x = max(0, min(tx - VIEW_W_TILES//2, self.map.w - VIEW_W_TILES))
        self.cam_y = max(0, min(ty - VIEW_H_TILES//2, self.map.h - VIEW_H_TILES))
        self._snap_smooth_positions()

    # spawn 
    def _spawn_dwarves(self, n):
        hx,hy = self.map.home
        candidates=[]
        for dy in range(-2,3):
            for dx in range(-2,3):
                x,y = hx+dx, hy+dy
                if 0<=x<self.map.w and 0<=y<self.map.h and self.map.grid[y][x] != 1:
                    candidates.append((x,y))
        candidates = sorted({c for c in candidates}, key=lambda p: abs(p[0]-hx)+abs(p[1]-hy))
        dwarves=[]; used=set()
        for pos in candidates:
            if len(dwarves)>=n: break
            if pos not in used:
                dwarves.append(DwarfBase(*pos)); used.add(pos)
        while len(dwarves)<n:
            dwarves.append(DwarfBase(hx, hy))
        return dwarves

    # recursos 
    def _can_pay(self, cost: dict) -> bool:
        return all(self.resources.get(k,0) >= v for k,v in cost.items())
    def _pay(self, cost: dict):
        for k,v in cost.items():
            self.resources[k] = max(0, self.resources.get(k,0) - v)

    def _screen_to_grid(self, mx, my):
        gx = mx // TILE + self.cam_x
        gy = my // TILE + self.cam_y
        return int(gx), int(gy)

    def _enqueue_build(self, grid_pos, kind, cost):
        x,y = grid_pos
        if not self.map.is_buildable(x,y):
            print(" No se puede construir aquí.")
            return
        if not self._can_pay(cost):
            print("Recursos insuficientes.")
            return
        self._pay(cost)
        self.planner.push_action("build_at", payload={"pos": (x,y), "kind": kind})

    def _spawn_particle(self, x_grid, y_grid, text, color):
        px = (x_grid + 0.5) * TILE
        py = (y_grid + 0.5) * TILE
        self.particles.append(Particle(px, py, text, color, lifetime=35, speed=-0.7))

    # movimiento enanos
    def dwarf_at_screenpos(self, mx, my):
        for d in self.dwarves:
            if d.state == "Muerto":
                continue
            dx = abs(d.sx - mx)
            dy = abs(d.sy - my)
            if dx < 10 and dy < 10:
                return d
        return None

    def command_move_dwarf(self, dwarf, gx, gy):
        if dwarf.state == "Muerto":
            return
        path = self.map.astar((dwarf.x, dwarf.y), (gx, gy))
        if path:
            dwarf.assign_task("idle", path, priority=999, meta={"manual": True})
            dwarf.task = "idle"
            dwarf.manual_hold = True  # se queda quieto luego

    # loop principal
    def run(self):
        while self.running:
            self.handle_events()
            self.planner.update()
            self.events.update()
            if not self.paused:
                self.update()
            self.draw()

            if self.events.active_wave:
                font = pygame.font.SysFont("consolas", 22, bold=True)
                text = font.render("OLEADA EN CURSO", True, (255, 80, 80))
                rect = text.get_rect(center=(VIEW_W_TILES * TILE // 2, 20))
                self.screen.blit(text, rect)

            pygame.display.flip()
            self.clock.tick(FPS)
            self.ticks += 1
        pygame.quit()

    # input
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running=False
            elif e.type == pygame.KEYDOWN:
                if   e.key==pygame.K_ESCAPE: self.running=False
                elif e.key==pygame.K_p:      self.paused = not self.paused
                elif e.key==pygame.K_LEFT:   self.cam_x = max(0, self.cam_x-4); self._snap_smooth_positions()
                elif e.key==pygame.K_RIGHT:  self.cam_x = min(self.map.w - VIEW_W_TILES, self.cam_x+4); self._snap_smooth_positions()
                elif e.key==pygame.K_UP:     self.cam_y = max(0, self.cam_y-4); self._snap_smooth_positions()
                elif e.key==pygame.K_DOWN:   self.cam_y = min(self.map.h - VIEW_H_TILES, self.cam_y+4); self._snap_smooth_positions()

                # payload={"force": True} para romper manual_hold si tú pides algo
                elif e.key==pygame.K_f: self.planner.push_action("wood",   DEFAULT_ORDER_AMOUNT, payload={"force": True})
                elif e.key==pygame.K_m: self.planner.push_action("mine",   DEFAULT_ORDER_AMOUNT, payload={"force": True})
                elif e.key==pygame.K_g: self.planner.push_action("farm",   DEFAULT_ORDER_AMOUNT, payload={"force": True})
                elif e.key==pygame.K_b:
                    costo_enano = {"food": 6} 
                    if self._can_pay(costo_enano):
                        self._pay(costo_enano)
                        self.dwarves.extend(self._spawn_dwarves(1))
                        print("Nuevo enano reclutado (Costo: 6 Papa)")
                    else:
                        print("No hay suficiente Papa para un nuevo BOLIVIANITO.")
                elif e.key==pygame.K_h: self.planner.push_action("hunt",   DEFAULT_ORDER_AMOUNT, payload={"force": True})

                elif e.key==pygame.K_d:
                    self.defense_mode = not getattr(self, "defense_mode", False)
                    if self.defense_mode:
                        print("Modo defensa ACTIVADO")
                        for d in self.dwarves:
                            if d.state != "Muerto":
                                d.cancel_task()
                                d.defend()
                        for tw in self.towers:
                            if "militia" not in tw:
                                tw["militia"] = 0
                            while self.resources.get("food",0) >= 2 and tw["militia"] < 3:
                                self.resources["food"] -= 2
                                tw["militia"] += 1
                        print("Milicia desplegada en torres")
                    else:
                        print("Modo defensa DESACTIVADO")
                        for d in self.dwarves:
                            if d.state != "Muerto" and d.state == "Defendiendo":
                                d.state = "Idle"
                                d.task  = "idle"
                                d.order_priority = 0

                elif e.key==pygame.K_n:
                    self.dwarves.extend(self._spawn_dwarves(1))
                    print("uevo enano reclutado")

                elif e.key==pygame.K_l:
                    hx, hy = self.map.home
                    lx = hx + random.randint(-3,3)
                    ly = hy + random.randint(-3,3)
                    if self.map.in_bounds(lx,ly) and self.map.grid[ly][lx] != WATER:
                        self.llamas.append(Llama(lx,ly,self.map))
                        print("llama agregada")

                elif e.key==pygame.K_o:
                    self.events.spawn_wave()
                    print("Oleada forzada")

                elif e.key==pygame.K_j:
                    bx = random.choice([0, self.map.w - 1])
                    by = random.randint(0, self.map.h - 1)
                    self.ponchos.append(PonchoJefe(bx, by, self.map))
                    print("Jefe de prueba generado")

                elif e.key==pygame.K_q: self.build_mode = BUILD_NONE
                elif e.key==pygame.K_1: self.build_mode = BUILD_WALL
                elif e.key==pygame.K_2: self.build_mode = BUILD_TOWER
                elif e.key==pygame.K_3: self.build_mode = BUILD_HOSP    

            #para clicks
            elif e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                panel_x = VIEW_W_TILES * TILE

                #scroll
                if e.button == 4 or e.button == 5:
                    if mx >= panel_x: # Mouse está sobre el panel
                        scroll_speed = 30
                        panel_view_height = VIEW_H_TILES * TILE 
                        
                        if e.button == 4: #abajo
                            self.panel_scroll_y = max(0, self.panel_scroll_y - scroll_speed)
                        
                        elif e.button == 5:
                            max_scroll = max(0, self.panel_content_height - panel_view_height)
                            self.panel_scroll_y = min(max_scroll, self.panel_scroll_y + scroll_speed)

                #para construir
                elif e.button == 1:
                    if self.build_mode != BUILD_NONE:
                        if mx < panel_x: # Click en el mundo del juego
                            gx, gy = self._screen_to_grid(mx, my)
                            if self.build_mode == BUILD_WALL:
                                self._enqueue_build((gx,gy), WALL_DEF, self.cost_wall)
                            elif self.build_mode == BUILD_TOWER:
                                self._enqueue_build((gx,gy), TOWER, self.cost_tower)
                            elif self.build_mode == BUILD_HOSP:
                                self._enqueue_build((gx,gy), HOSPITAL, self.cost_hosp)

                elif e.button == 3:
                    if mx < panel_x: 
                        dw = self.dwarf_at_screenpos(mx, my)
                        if dw:
                            self.selected_dwarf = dw
                            print(f"Seleccionado: {dw.name}")
                        else:
                            if self.selected_dwarf:
                                gx, gy = self._screen_to_grid(mx, my)
                                
                                if 0 <= gx < self.map.w and 0 <= gy < self.map.h:
                                    tile_kind = self.map.grid[gy][gx]
                                    if tile_kind in (FOREST, MINE, FARM):
                                        print("No puedes mandar al enano directo a taladrar recurso.")
                                    else:
                                        self.command_move_dwarf(self.selected_dwarf, gx, gy)
                                        print(f"Moviendo a {gx},{gy}")

    def update(self):
        self.step_counter += 1

        if self.step_counter % STEP_DELAY == 0:
            hospital_positions = list(self.map.positions_for(HOSPITAL))
            for d in self.dwarves:
                if d.state != "Muerto" and d.task == "idle" and d.energy < 18 and hospital_positions:
                    hx,hy = min(hospital_positions, key=lambda p: abs(p[0]-d.x)+abs(p[1]-d.y))
                    self.planner.push_action("heal", payload={"pos": (hx,hy)})

            for d in self.dwarves:
                before = (d.x,d.y, d.state, d.task, d.timer, d.meta)
                d.move()
                d.tick_stats(self.map)

                if getattr(self, "defense_mode", False):
                    for p in list(self.ponchos):
                        if abs(int(p.x) - d.x) + abs(int(p.y) - d.y) <= 1 and p.hp > 0 and d.state != "Muerto":
                            damage = 150 if d.oficio == "Guardia" else 80
                            p.hp -= damage
                            if p.hp <= 0:
                                self.ponchos.remove(p)
                                self._spawn_particle(int(p.x), int(p.y),"💥", (255,100,100))

                if before[2]=="Trabajando" and d.state=="Idle":
                    task = before[3]
                    bx, by = before[0], before[1]
                    meta = before[5] or {}

                    # recoeltar
                    if task in ("wood", "mine", "farm"):
                        if task == "wood":
                            self.resources["wood"] += 1
                            gain_texts = [("+1 Madera", (230, 200, 150))]
                        elif task == "mine":
                            self.resources["stone"] += 1
                            gain_texts = [("+1 Piedra", (200, 200, 210))]
                        elif task == "hunt":
                            gain_texts = []
                            llama = meta.get("target")
                            if llama and llama.hp > 0:
                                llama.die()
                                self.resources["food"] += 5 #comida
                                self._spawn_particle(int(llama.x), int(llama.y), "+5 carne", (255,100,100))
                        else:  # farm
                            self.resources["food"] += 1
                            gain_texts = [
                                ("+1 Papa", (255,230,100)),
                                ("+1 Coca", (100,255,100))
                            ]

                        for txt, col in gain_texts:
                            self._spawn_particle(bx, by, txt, col)

                        # eliminar tile
                        if (bx,by) in self.map.resource_amount:
                            del self.map.resource_amount[(bx,by)]

                        kind_here = self.map.grid[by][bx]
                        if kind_here in (FOREST, MINE, FARM):
                            if kind_here in self.map.idx and (bx,by) in self.map.idx[kind_here]:
                                self.map.idx[kind_here].discard((bx,by))
                            self.map.grid[by][bx] = EMPTY
                    
                    elif task == "hunt": 
                        llama = meta.get("target")
                        if llama and llama.hp > 0:
                            llama.die() 
                            self.resources["food"] += 5 
                            self._spawn_particle(int(llama.x), int(llama.y), "+5 Papa", (255,100,100))

                    elif task == "build_at":
                        kind = meta.get("kind")
                        px, py = meta.get("pos", (bx,by))
                        if self.map.is_buildable(px,py):
                            self.map.set_tile(px,py, kind)
                            if kind == TOWER:
                                self.towers.append({"x":px, "y":py, "cd":0, "militia":0})
                        else:
                            # reembolso min (no lo veo necesario)
                            self.resources["wood"] += 1
                            self.resources["stone"] += 1

        # mov suave
        for d in self.dwarves:
            tx = (d.x - self.cam_x)*TILE + TILE//2
            ty = (d.y - self.cam_y)*TILE + TILE//2
            d.sx = lerp(d.sx, tx, 0.28)
            d.sy = lerp(d.sy, ty, 0.28)

        # enemigos
        for p in list(self.ponchos):
            p.update(self.dwarves, self.map)
            if p.hp <= 0:
                self.ponchos.remove(p)

        # curacion
        hosp_positions = list(self.map.positions_for(HOSPITAL))
        for d in self.dwarves:
            if d.state != "Muerto" and d.task == "idle" and d.energy < 100:
                for (hx, hy) in hosp_positions:
                    dist = abs(hx - d.x) + abs(hy - d.y)
                    if dist <= 7:
                        d.energy = min(100, d.energy + self.heal_rate)
                        break

        # torres 
        if self.towers and self.ponchos:
            for tw in self.towers:
                if tw.get("cd",0) > 0:
                    tw["cd"] -= 1
                else:
                    tx, ty = tw["x"], tw["y"]
                    target = None
                    best_d = 999999
                    for p in self.ponchos:
                        dman = abs(int(p.x) - tx) + abs(int(p.y) - ty)
                        if dman <= self.tower_range and dman < best_d and p.hp > 0:
                            best_d = dman
                            target = p
                    if target:
                        sx = tx*TILE + TILE*0.5
                        sy = ty*TILE + TILE*0.2
                        self.projectiles.append(Projectile(sx, sy, target))
                        tw["cd"] = self.tower_cooldown

        # milicia (incompleto )
        for tw in self.towers:
            militia = tw.get("militia", 0)
            if militia <= 0:
                continue
            tx, ty = tw["x"], tw["y"]
            for p in list(self.ponchos):
                dist = abs(int(p.x) - tx) + abs(int(p.y) - ty)
                if dist <= 2 and p.hp > 0:
                    p.hp -= 60 * militia
                    if p.hp <= 0:
                        self.ponchos.remove(p)
                        self._spawn_particle(int(p.x), int(p.y), "💥", (255,180,60))

        for llama in self.llamas:
            llama.update()

        self.llamas = [llama for llama in self.llamas if llama.hp > 0]
        
        self.projectiles = [pr for pr in self.projectiles if pr.update()]
        self.particles = [p for p in self.particles if p.update()]

    #render 
    def draw(self):
        self.map.draw(self.screen, camx=self.cam_x, camy=self.cam_y,
                      view_w=VIEW_W_TILES, view_h=VIEW_H_TILES, tick=self.ticks)

        if self.build_mode != BUILD_NONE:
            mx, my = pygame.mouse.get_pos()
            if mx < VIEW_W_TILES*TILE:
                gx, gy = self._screen_to_grid(mx, my)
                px, py = (gx - self.cam_x) * TILE, (gy - self.cam_y) * TILE
                ghost_surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                color = (255,255,255)
                if self.build_mode == BUILD_WALL:    color = COLORS[WALL_DEF]
                elif self.build_mode == BUILD_TOWER: color = COLORS[TOWER]
                elif self.build_mode == BUILD_HOSP:  color = COLORS[HOSPITAL]

                can_build = self.map.is_buildable(gx, gy)
                final_color = (*color, 120) if can_build else (255, 0, 0, 100)
                pygame.draw.rect(ghost_surf, final_color, (0,0,TILE,TILE), border_radius=3)
                self.screen.blit(ghost_surf, (px, py))

        for pr in self.projectiles:
            pr.draw(self.screen, self.cam_x, self.cam_y)
        for p in self.particles:
            p.draw(self.screen, self.cam_x, self.cam_y, self.small)

        day = (math.sin(self.ticks*0.001)+1)/2
        night_alpha = int(clamp(180*(1-day), 0, 140))
        if night_alpha>0:
            overlay = pygame.Surface((VIEW_W_TILES*TILE, VIEW_H_TILES*TILE), pygame.SRCALPHA)
            overlay.fill((20,25,40, night_alpha))
            self.screen.blit(overlay, (0,0))

        #enanos
        for d in self.dwarves:
            cx = int(d.sx); cy = int(d.sy)
            pygame.draw.ellipse(self.screen, (0,0,0,80), (cx-6, cy+4, 12, 6))
            if d.state == "Trabajando":
                r = 10 + int(2 * math.sin(self.ticks * 0.2))
                pygame.draw.circle(self.screen, (255,230,140,90), (cx,cy), r, 2)

            if d.state == "Muerto":
                img = DwarfBase.dead_img
            elif d.state == "Idle":
                img = DwarfBase.idle_img
            elif d.state == "Defendiendo":
                img = DwarfBase.walk_imgs[(self.ticks // 5) % 2]
            else:
                img = DwarfBase.walk_imgs[(self.ticks // 10) % 2]

            rect = img.get_rect(center=(cx, cy))
            self.screen.blit(img, rect)

            label = f"{d.name[0]}{d.oficio[0]}"
            txt = self.small.render(label, True, (0,0,0))
            self.screen.blit(txt, (cx-6, cy-16))

            if d.state == "Trabajando":
                total = max(1, d.current_work_time())
                prog = clamp(d.timer / total, 0, 1)
                pygame.draw.rect(self.screen, (35,35,35), (cx-8, cy+10, 16, 4), border_radius=2)
                pygame.draw.rect(self.screen, (100,255,120), (cx-8, cy+10, int(16*prog), 4), border_radius=2)

        
           #ponchos y jefe
        for p in self.ponchos:
            cx = int((p.x - self.cam_x) * TILE) + TILE//2
            cy = int((p.y - self.cam_y) * TILE) + TILE//2
            p_pos = (cx, cy)

            img = None

            if getattr(p, "is_boss", False):
                # DEBUG)
                print("[DRAW JEFE] frame_idx=", getattr(p, "frame_idx", None),
                      "len(world.BOSS_IMGS)=", len(world.BOSS_IMGS))

                # (por si no carga imagen)
                if len(world.BOSS_IMGS) > 0:
                    fi = getattr(p, "frame_idx", 0) % len(world.BOSS_IMGS)
                    img = world.BOSS_IMGS[fi]

                # circulo horrible
                if img is None:
                    pygame.draw.circle(self.screen, (200, 50, 50), p_pos, 14)
                    pygame.draw.circle(self.screen, (255, 200, 200), p_pos, 14, 2)

            else:
                # poncho normal
                if p.state == "Idle":
                    img = PonchoRojo.idle_img
                else:
                    img = PonchoRojo.walk_imgs[(self.ticks // 10) % 2]

            # dibujar sprite
            if img is not None:
                rect = img.get_rect(center=p_pos)
                self.screen.blit(img, rect)

            # barra de vida
            bar_w = 24 if getattr(p, "is_boss", False) else 20
            max_hp = getattr(p, "max_hp", 500) or 500
            hp_ratio = max(0, min(1, p.hp / max_hp))

            pygame.draw.rect(self.screen, (60, 0, 0), (cx - bar_w // 2, cy - 20, bar_w, 3), border_radius=2)
            pygame.draw.rect(self.screen, (200, 0, 0), (cx - bar_w // 2, cy - 20, int(bar_w * hp_ratio), 3), border_radius=2)

            # etiqueta jefe
            if getattr(p, "is_boss", False):
                boss_tag = self.small.render("JEFE", True, (255, 80, 80))
                self.screen.blit(boss_tag, (cx - 12, cy - 32))

        # llamas
        for llama in self.llamas:
            llama.draw(self.screen, self.cam_x, self.cam_y, self.ticks)

        panel_x = VIEW_W_TILES*TILE
        panel_view_height = VIEW_H_TILES*TILE 
        
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, 0, INFO_WIDTH, panel_view_height))
        

        clip_rect = pygame.Rect(panel_x, 0, INFO_WIDTH, panel_view_height)
        self.screen.set_clip(clip_rect)

        
        y = 8 
        
        self.screen.blit(self.font.render("Colonia", True, PANEL_ACCENT), (panel_x+12, y - self.panel_scroll_y)); 
        y += 22

        status = "PAUSADO" if self.paused else "Corriendo"
        self.screen.blit(self.small.render(f"Estado: {status}", True, TEXT_DIM), (panel_x+12, y - self.panel_scroll_y)); 
        y += 16

        res_line = f"Madera: {self.resources['wood']}  Piedra: {self.resources['stone']}  Comida: {self.resources['food']}"
        self.screen.blit(self.small.render(res_line, True, (230,230,230)), (panel_x+12, y - self.panel_scroll_y)); 
        y += 20

        # hud
        self.screen.blit(self.small.render("Ciclo solar", True, TEXT_DIM),(panel_x+240, 8 - self.panel_scroll_y)) # y=8
        ang = (self.ticks*0.001) % (2*math.pi)
        cx_orbit = panel_x + 300
        cy_orbit = 40 - self.panel_scroll_y
        r_orbit = 20
        sx = int(cx_orbit + math.cos(ang) * r_orbit)
        sy = int(cy_orbit - math.sin(ang) * r_orbit) # cy_orbit ya tiene el scroll aplicado
        pygame.draw.circle(self.screen, (80,80,90), (cx_orbit, cy_orbit), r_orbit, 1)
        pygame.draw.circle(self.screen, (255,220,100), (sx,sy), 6)
        y = 78
        self.screen.blit(self.small.render("Construcción:", True, PANEL_ACCENT), (panel_x+12, y - self.panel_scroll_y)); 
        y += 16
        
        build_lines = [
            f"[1] Muro     (Piedra x{self.cost_wall['stone']})",
            f"[2] Torre    (Madera x{self.cost_tower['wood']}  Piedra x{self.cost_tower['stone']})",
            f"[3] Hospital (Madera x{self.cost_hosp['wood']}  Piedra x{self.cost_hosp['stone']})",
            "Click: colocar | Q: salir modo"
        ]
        for line in build_lines:
            self.screen.blit(self.small.render(line, True, (210,210,210)), (panel_x+12, y - self.panel_scroll_y))
            y += 14

        y += 8
        self.screen.blit(self.small.render("Tareas:", True, PANEL_ACCENT), (panel_x+12, y - self.panel_scroll_y)); 
        y += 16
        
        ctrl_lines = [
            "F: Leña   M: Mina   G: Granja",
            "B: Generar enano.   H: Cazar",
            "D: Defensa",
            "N: Nuevo enano   L: Llama",
            "O: Oleada        J: Jefe",
            "Click derecho: seleccionar / mover enano"
        ]
        for line in ctrl_lines:
            self.screen.blit(self.small.render(line, True, TEXT_DIM), (panel_x+12, y - self.panel_scroll_y))
            y += 14

        y += 8
        self.screen.blit(self.font.render("Bolivianitos", True, PANEL_ACCENT), (panel_x+12, y - self.panel_scroll_y)); 
        y += 22

        # lista enanos
        for d in self.dwarves:
            name = f"{d.name.split()[0]} ({d.oficio})"
            self.screen.blit(self.small.render(name, True, (230,230,230)), (panel_x+12, y - self.panel_scroll_y)); 
            y += 14

            self.screen.blit(self.small.render(f"{d.state}", True, (180,180,180)), (panel_x+12, y - self.panel_scroll_y)); 
            y += 10

            bar_w, bar_h = 120, 6
            # vida guard
            max_energy = 150 if d.oficio == "Guardia" else 100
            energy_clamped = max(0, min(max_energy, d.energy))
            pfill = energy_clamped / max_energy # Dividir por 150 o 100
            
            filled = int(bar_w * pfill)
            color = (0,200,90) if pfill>0.5 else (255,200,50) if pfill>0.25 else (220,60,60)
            
            # Posición de la barra
            bar_y = y - self.panel_scroll_y
            pygame.draw.rect(self.screen, (45,45,48), (panel_x+12, bar_y, bar_w, bar_h), border_radius=2)
            pygame.draw.rect(self.screen, color, (panel_x+12, bar_y, filled, bar_h), border_radius=2)
            pygame.draw.rect(self.screen, (10,10,12), (panel_x+12, bar_y, bar_w, bar_h), 1)
            y += 14

        # minimapa
        y += 10
        self._draw_minimap(panel_x+12, y - self.panel_scroll_y) 
        y += 80 + 6

        heap_size = len(self.planner.heap.data)
        self.screen.blit(self.font.render(f"Heap: {heap_size}", True, PANEL_ACCENT),(panel_x+12, y - self.panel_scroll_y))
        y += 30 

        # Guardar la altura total
        self.panel_content_height = y

        #quitar corte 
        self.screen.set_clip(None)

        # Dibujar el borde que separa el panel
        pygame.draw.line(self.screen, (60,60,65), (panel_x,0), (panel_x, panel_view_height), 2)

        #Dibujar scroll
        content_h = self.panel_content_height
        view_h = panel_view_height
        
        if content_h > view_h:
            # dibujar la barra
            scrollbar_x = panel_x + INFO_WIDTH - 8 
            track_y = 8
            track_h = view_h - 16 # 
            thumb_h = max(30, track_h * (view_h / content_h))
            
            # Posición y 
            scroll_range = max(1, content_h - view_h)
            thumb_range = max(1, track_h - thumb_h)
            
            scroll_ratio = self.panel_scroll_y / scroll_range
            thumb_y = track_y + scroll_ratio * thumb_range
            pygame.draw.rect(self.screen, (10, 10, 12), (scrollbar_x, track_y, 6, track_h), border_radius=2)
            pygame.draw.rect(self.screen, (80, 80, 85), (scrollbar_x, thumb_y, 6, thumb_h), border_radius=3)

    def _draw_minimap(self, px, py):
        mw, mh = 120, 80
        mm = pygame.Surface((mw, mh))
        sx = max(1, self.map.w // mw)
        sy = max(1, self.map.h // mh)
        for y in range(0, self.map.h, sy):
            ry = (y//sy)
            if ry>=mh: break
            for x in range(0, self.map.w, sx):
                rx = (x//sx)
                if rx>=mw: break
                kind = self.map.grid[y][x]
                mm.set_at((rx,ry), pygame.Color(*self._mini_color(kind)))
        vx = int(self.cam_x / max(1,self.map.w) * mw)
        vy = int(self.cam_y / max(1,self.map.h) * mh)
        vw = max(2, int(VIEW_W_TILES / max(1,self.map.w) * mw))
        vh = max(2, int(VIEW_H_TILES / max(1,self.map.h) * mh))
        pygame.draw.rect(mm, (255,255,255), (vx,vy,vw,vh), 1)

        self.screen.blit(self.small.render("Minimapa", True, TEXT_DIM), (px, py-14))
        self.screen.blit(mm, (px, py))

    def _mini_color(self, kind):
        if kind==FOREST:  return (40,160,60)
        if kind==MINE:    return (160,120,70)
        if kind==FARM:    return (200,150,80)
        if kind==WATER:   return (60,100,180)
        if kind==HOME:    return (120,140,255)
        if kind==GRANARY: return (220,200,90)
        if kind==WALL_DEF:return (160,160,160)
        if kind==TOWER:   return (230,215,90)
        if kind==HOSPITAL:return (210,120,160)
        if kind==WALL:    return (70,70,80)
        return (120,180,130)

    # usado por planner
    def find_nearest(self, dw, tile_type):
        positions = list(self.map.positions_for(tile_type))
        if not positions:
            return None, []
        sx, sy = dw.x, dw.y
        positions.sort(key=lambda p: abs(p[0]-sx)+abs(p[1]-sy))
        TRIES = min(20, len(positions))
        for i in range(TRIES):
            goal = positions[i]
            path = self.map.astar((sx,sy), goal)
            if path:
                return goal, path
        goal = positions[0]
        path = self.map.astar((sx,sy), goal)
        return goal, path or []

if __name__ == "__main__":
    Game().run()
