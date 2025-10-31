import random
from actors import PonchoRojo, PonchoJefe
from world import WATER

class EventManager:
    def __init__(self, planner, game, enabled=True, view_w=50, view_h=36): 
        self.planner = planner
        self.game = game
        self.enabled = enabled
        self.timer = 0
        self.view_w = view_w 
        self.view_h = view_h 

        self.wave_timer = 1000
        self.wave_number = 0
        self.active_wave = False

    def update(self):
        if not self.enabled:
            return
        self.timer += 1

        # no oleada activa
        if not self.active_wave:
            self.wave_timer -= 1
            if self.wave_timer <= 0:
                self.spawn_wave()


        #oleada activa
        else:
            #acaba si no hay ponchos
            if not self.game.ponchos:
                print(f"✅ ¡Oleada #{self.wave_number} superada!")
                self.active_wave = False
                # reset timer
                self.wave_timer = 1000

        if self.timer > 420:
            self.random_event()
            self.timer = 0

    def random_event(self):
        task = random.choice(["wood","mine","farm"])
        self.planner.push_action(task, base_priority=2)

    def spawn_wave(self):
            self.wave_number += 1

            current_hp = 500 + (self.wave_number * 25)
            
            count = min(4 + self.wave_number * 2, 60)
            ponchos = []
            
            # actual camara
            cam_x = self.game.cam_x
            cam_y = self.game.cam_y
            
            # asegurar que no salio de mapa
            max_x = min(cam_x + self.view_w - 1, self.game.map.w - 1)
            max_y = min(cam_y + self.view_h - 1, self.game.map.h - 1)

            for _ in range(count):
                
                # encontrar lugar poncho 
                spawned = False
                for _ in range(10): 
                    x = random.randint(cam_x, max_x)
                    y = random.randint(cam_y, max_y)

                    # valido?
                    if self.game.map.in_bounds(x, y) and self.game.map.grid[y][x] != WATER:
                        ponchos.append(PonchoRojo(x, y, self.game.map, hp=current_hp))
                        spawned = True
                        break 
                
                if not spawned:
                    print(f"Nos estamos inundando :(.")


            self.game.ponchos.extend(ponchos)

            # jefe 10 oleada
            if self.wave_number % 10 == 0:
                current_boss_hp = 3000 + (self.wave_number * 125)
                spawned = False
                for _ in range(10):
                    bx = random.randint(cam_x, max_x)
                    by = random.randint(cam_y, max_y)
                    if self.game.map.in_bounds(bx, by) and self.game.map.grid[by][bx] != WATER:
                        boss = PonchoJefe(bx, by, self.game.map, hp=current_boss_hp)
                        self.game.ponchos.append(boss)
                        print("💀 ¡JEFE aparece en pantalla!")
                        spawned = True
                        break
                
                if not spawned:
                    print(f" No se encontró lugar para el JEFE.")

            print(f"Oleada #{self.wave_number} — {count} Ponchos Rojos")
            self.active_wave = True
