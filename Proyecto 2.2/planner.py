import heapq
from world import FOREST, MINE, FARM, GRANARY, HOME
from actors import SUIT_MAP

PRIORITIES = {
    "idle":        0,
    "wood":        2,
    "mine":        2,
    "farm":        2,
    "build":       2,
    "hunt":        2,
    "defend":      3,
    "build_at":    3,
    "heal":        4,
}

TASK_TO_TILE = {
    "wood":   FOREST,
    "mine":   MINE,
    "farm":   FARM,
    "build":  GRANARY,
    "defend": HOME,
}

class HeapPriority:
    def __init__(self):
        self.data = []
    def __len__(self):
        return len(self.data)

class Planner:
    def __init__(self, game):
        self.game = game
        self.heap = HeapPriority()
        # romper empates hear
        self._ticket = 0

    def _push_heapitem(self, priority, task, payload):
        #priority más grande=más important
        self._ticket += 1
        # heapq es min-heap
        heapq.heappush(
            self.heap.data,
            (-priority, self._ticket, task, payload or {})
        )

    def push_action(self, task, amount=1, base_priority=None, payload=None):
        pr = PRIORITIES.get(task, 1)
        if base_priority is not None:
            pr = base_priority
        for _ in range(amount):
            self._push_heapitem(pr, task, payload)

        #defensa es inmediata
        if task == "defend":
            for d in self.game.dwarves:
                if d.state != "Muerto":
                    d.cancel_task()
                    d.defend()
            self._assign_until_blocked()

    def _assign_until_blocked(self):

        assigned_something = True

        while assigned_something and self.heap.data:
            assigned_something = False
            new_buffer = []

            round_items = []
            while self.heap.data:
                round_items.append(heapq.heappop(self.heap.data))

            for pr_neg, ticket, task, payload in round_items:
                payload = payload or {}
                force = payload.get("force", False)

                if getattr(self.game, "defense_mode", False):
                    if task not in ("defend", "heal"):
                        new_buffer.append((pr_neg, ticket, task, payload))
                        continue


                raw_idle = [
                    d for d in self.game.dwarves
                    if d.task == "idle" and d.state != "Muerto" and d.energy > 0
                ]
                
                if task in ("defend", "heal") or force:
                    idle_dwarves = raw_idle[:]
                else:
                    idle_dwarves = [d for d in raw_idle if not d.manual_hold]

                if not idle_dwarves:
                    new_buffer.append((pr_neg, ticket, task, payload))
                    continue

                specialists = []
                generalists = []
                for d in idle_dwarves:
                    if task in SUIT_MAP.get(d.oficio, set()):
                        specialists.append(d)
                    else:
                        generalists.append(d)
                

                specialists.sort(key=lambda d: d.energy, reverse=True)
                generalists.sort(key=lambda d: d.energy, reverse=True)

                best_dwarf_assigned = None
                if task in ("build_at", "heal"):
                    pos = payload.get("pos")
                    if not pos:
                        new_buffer.append((pr_neg, ticket, task, payload)); continue

                    # primero especialist
                    for d in specialists + generalists:
                        path = self.game.map.astar((d.x, d.y), pos)
                        if path:
                            best_dwarf_assigned = d
                            best_dwarf_assigned.assign_task(task, path, priority=PRIORITIES.get(task, 1), meta=payload)
                            break
                
                # cazar
                elif task == "hunt":
                    live_llamas = [llama for llama in self.game.llamas if llama.hp > 0]
                    if not live_llamas:
                        new_buffer.append((pr_neg, ticket, task, payload)); continue

                    #cercana
                    best_target, best_path, best_score = None, [], 10**9
                    
                    #prim caz
                    for d in specialists:
                        for llama in live_llamas:
                            path = self.game.map.astar((d.x, d.y), (int(llama.x), int(llama.y)))
                            if path and len(path) < best_score:
                                best_dwarf_assigned = d
                                best_target = llama
                                best_path = path
                                best_score = len(path)
                    
                    # gen
                    if best_dwarf_assigned is None:
                         for d in generalists:
                            for llama in live_llamas:
                                path = self.game.map.astar((d.x, d.y), (int(llama.x), int(llama.y)))
                                if path and len(path) < best_score:
                                    best_dwarf_assigned = d
                                    best_target = llama
                                    best_path = path
                                    best_score = len(path)

                    if best_dwarf_assigned:
                        best_dwarf_assigned.assign_task(task, best_path, priority=PRIORITIES.get(task, 1), meta={"target": best_target})
                
                # Tareas
                elif TASK_TO_TILE.get(task):
                    tile = TASK_TO_TILE.get(task)
                    
                    #prim especialistas luego vida
                    for d in specialists:
                        goal, path = self.game.find_nearest(d, tile)
                        if path and goal:
                            best_dwarf_assigned = d
                            best_dwarf_assigned.assign_task(task, path, priority=PRIORITIES.get(task, 1))
                            break
                    
                    # gen
                    if best_dwarf_assigned is None:
                        for d in generalists:
                            goal, path = self.game.find_nearest(d, tile)
                            if path and goal:
                                best_dwarf_assigned = d
                                best_dwarf_assigned.assign_task(task, path, priority=PRIORITIES.get(task, 1))
                                break 

                

                if best_dwarf_assigned:
                    best_dwarf_assigned.manual_hold = False
                    assigned_something = True
                else:
                    #nadie -> cola
                    new_buffer.append((pr_neg, ticket, task, payload))

            # re encolar
            for item in new_buffer:
                heapq.heappush(self.heap.data, item)

    def update(self):
        if self.heap.data:
            self._assign_until_blocked()
