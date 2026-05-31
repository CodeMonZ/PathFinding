# ============================================================
# enemy.py - Enemigo con inteligencia evolutiva
# ============================================================
#
# COMPORTAMIENTO POR ALGORITMO:
#
#   DFS:      Exploracion ciega ciclica con stack.
#             No sabe donde esta el jugador.
#
#   Dijkstra: Exploracion ciega ciclica con min-heap.
#             No sabe donde esta el jugador.
#
#   A*:       Persecucion informada con heuristica.
#             Si sabe donde esta el jugador y calcula el camino optimo.
#
# ============================================================

import heapq

from constants import (
    ASTAR_COLOR,
    ASTAR_RECALC_STEPS,
    DFS_COLOR,
    DIJKSTRA_COLOR,
    ENEMY_SPEEDS,
    ENTITY_LERP_SPEED,
    MIN_ENEMY_DELAY,
    PLAYER_SIZE,
)
from pathfinding import astar


VISION_RADIUS = 4

MOVE_DIRECTIONS = [
    (-1, 0, "arriba"),
    (0, 1, "derecha"),
    (1, 0, "abajo"),
    (0, -1, "izquierda"),
]


class Enemy:
    """Enemigo que busca o persigue segun el algoritmo seleccionado."""

    def __init__(self, row, col, algorithm="dfs"):
        self.row = row
        self.col = col
        self.algorithm = algorithm
        self.speed_multiplier = 1.0
        self.move_timer = 0

        self.visual_row = float(row)
        self.visual_col = float(col)

        # DFS y Dijkstra son ciegos: solo escanean una zona local.
        self.scan_cells = []
        self.visited = {(row, col)}
        self.visit_counts = {(row, col): 1}
        self.backtrack_stack = []
        self.previous_pos = None
        self.last_player_visible = False
        self.last_direction = "inicio"
        self.last_decision = "Escanea periferia"

        # Camino calculado solo para A*.
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

        self.is_alerted = False
        self.explored = [(row, col)]
        self.last_result = None

    def set_algorithm(self, algorithm):
        self.algorithm = algorithm
        self.path = []
        self.path_index = 0
        self.steps_taken = 0
        self.is_alerted = False
        self.explored = [(self.row, self.col)]
        self.scan_cells = []
        self.visited = {(self.row, self.col)}
        self.visit_counts = {(self.row, self.col): 1}
        self.backtrack_stack = []
        self.previous_pos = None
        self.last_player_visible = False
        self.last_direction = "inicio"
        self.last_decision = "Escanea periferia"
        self.last_result = None

    def get_color(self):
        colors = {"dfs": DFS_COLOR, "dijkstra": DIJKSTRA_COLOR, "astar": ASTAR_COLOR}
        return colors.get(self.algorithm, DFS_COLOR)

    def get_move_delay(self):
        base_delay = ENEMY_SPEEDS.get(self.algorithm, 200)
        return max(MIN_ENEMY_DELAY, int(base_delay / self.speed_multiplier))

    def get_algorithm_name(self):
        names = {"dfs": "DFS", "dijkstra": "Dijkstra", "astar": "A*"}
        return names.get(self.algorithm, "???")

    def _needs_recalculate_astar(self):
        if not self.path:
            return True
        if self.path_index >= len(self.path) - 1:
            return True
        if self.steps_taken >= ASTAR_RECALC_STEPS:
            return True
        return False

    def update(self, grid, player_pos, dt, occupied=None):
        """
        Mueve al enemigo un paso.
        DFS/Dijkstra son ciegos: no reciben player_pos para decidir el camino.
        A* sigue siendo informado porque su gracia es usar una meta.
        """
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        if occupied is None:
            occupied = set()

        if self.algorithm in ("dfs", "dijkstra"):
            self.is_alerted = False
            self.path = []
            self.path_index = 0
            self.steps_taken = 0
            self._update_blind(grid, player_pos, occupied)
        else:
            self.is_alerted = True
            self._update_astar(grid, player_pos, occupied)

        self.move_timer = self.get_move_delay()

    def _update_blind(self, grid, player_pos, occupied):
        """Exploracion ciega local: escanea radio 4, luego avanza 1 paso."""
        self.scan_cells = self._scan_periphery(grid)
        player_cells = set(grid.entity_cells(*player_pos, PLAYER_SIZE))
        player_visible = bool(player_cells.intersection(self.scan_cells))
        if self.last_player_visible and not player_visible:
            self._reset_blind_search()
        self.is_alerted = player_visible
        self.last_player_visible = player_visible

        if player_visible:
            if self.algorithm == "dijkstra":
                next_cell, direction = self._choose_dijkstra_step(grid, occupied, player_cells)
            else:
                next_cell, direction = self._choose_dfs_visible_step(grid, occupied, player_cells)
        elif self.algorithm == "dfs":
            next_cell, direction = self._choose_dfs_step(grid, occupied)
        else:
            next_cell, direction = self._choose_dijkstra_step(grid, occupied, player_cells)

        self._move_one_cell(next_cell, direction)

    def _reset_blind_search(self):
        current = self.get_pos()
        self.visited = {current}
        self.backtrack_stack = []
        self.previous_pos = None
        self.path = []
        self.last_decision = "Reinicia busqueda ciega"

    def _scan_periphery(self, grid):
        return [cell for cell in self._local_area(grid) if cell != self.get_pos()]

    def _valid_moves(self, grid, occupied):
        moves = []
        for index, (dr, dc, name) in enumerate(MOVE_DIRECTIONS):
            row = self.row + dr
            col = self.col + dc
            pos = (row, col)
            if grid.can_move_entity(self.row, self.col, dr, dc, 1) and pos not in occupied:
                moves.append((index, pos, name))
        return moves

    def _choose_dfs_step(self, grid, occupied):
        current = self.get_pos()
        moves = self._valid_moves(grid, occupied)
        ranked_moves = sorted(moves, key=self._blind_move_rank)
        unvisited = [(i, pos, name) for i, pos, name in ranked_moves if pos not in self.visited]

        if unvisited:
            _, pos, name = unvisited[0]
            self.backtrack_stack.append(current)
            self.last_decision = "DFS explora periferia"
            return pos, name

        while self.backtrack_stack:
            pos = self.backtrack_stack.pop()
            if pos in [move_pos for _, move_pos, _ in ranked_moves]:
                direction = self._direction_to(pos)
                self.last_decision = "DFS retrocede"
                return pos, direction

        if ranked_moves:
            _, pos, name = ranked_moves[0]
            self.last_decision = "DFS reinicia ciclo local"
            return pos, name

        self.last_decision = "Sin salida"
        return None, "quieto"

    def _choose_dfs_visible_step(self, grid, occupied, player_cells):
        result = self._run_local_dfs(grid, self._local_area(grid), player_cells, occupied)
        self.scan_cells = result["explored"]
        if len(result["path"]) > 1:
            self.path = result["path"]
            self.last_decision = "DFS encontro jugador"
            next_cell = result["path"][1]
            return next_cell, self._direction_to(next_cell)

        self.last_decision = "DFS rodea obstaculo"
        return self._choose_dfs_step(grid, occupied)

    def _choose_dijkstra_step(self, grid, occupied, player_cells=None):
        local_area = self._local_area(grid)
        if player_cells and player_cells.intersection(local_area):
            targets = sorted(
                [cell for cell in player_cells if cell in local_area],
                key=lambda cell: self._distance_from_start(cell),
            )
            mode = "Dijkstra encontro jugador"
        else:
            targets = sorted(
                [
                    cell for cell in self._local_border(local_area)
                    if cell != self.get_pos()
                ],
                key=self._blind_target_rank,
            )
            mode = "Dijkstra explora frontera 4"

        route_result = self._first_dijkstra_route(
            grid,
            local_area,
            targets,
            occupied,
            avoid_previous=(mode != "Dijkstra encontro jugador"),
        )
        if route_result:
            self.path = route_result["path"]
            self.scan_cells = route_result["explored"]
            self.last_decision = mode
            next_cell = route_result["path"][1]
            return next_cell, self._direction_to(next_cell)

        if mode == "Dijkstra encontro jugador":
            return self._choose_dijkstra_step(grid, occupied, None)

        if mode == "Dijkstra explora frontera 4":
            fallback_targets = sorted(
                [
                    cell for cell in local_area
                    if cell != self.get_pos()
                ],
                key=self._blind_target_rank,
            )
            route_result = self._first_dijkstra_route(
                grid,
                local_area,
                fallback_targets,
                occupied,
                avoid_previous=True,
            )
            if route_result:
                self.path = route_result["path"]
                self.scan_cells = route_result["explored"]
                self.last_decision = "Dijkstra explora local"
                next_cell = route_result["path"][1]
                return next_cell, self._direction_to(next_cell)

        self.path = []
        self.last_decision = "Dijkstra sin destino"
        return self._fallback_dijkstra_neighbor(grid, occupied, None)

    def _local_area(self, grid):
        area = set()
        for row in range(self.row - VISION_RADIUS, self.row + VISION_RADIUS + 1):
            for col in range(self.col - VISION_RADIUS, self.col + VISION_RADIUS + 1):
                if (
                    abs(row - self.row) <= VISION_RADIUS
                    and abs(col - self.col) <= VISION_RADIUS
                    and grid.can_place_entity(row, col, 1)
                ):
                    area.add((row, col))
        return area

    def _local_border(self, local_area):
        return [
            cell for cell in local_area
            if abs(cell[0] - self.row) == VISION_RADIUS
            or abs(cell[1] - self.col) == VISION_RADIUS
        ]

    def _run_local_dijkstra(self, grid, allowed, goal, occupied):
        start = self.get_pos()
        if start not in allowed or goal not in allowed:
            return {"path": [], "explored": []}

        distances = {start: 0}
        parents = {start: None}
        explored = []
        visited = set()
        heap = [(0, 0, start)]
        tie_breaker = 1

        while heap:
            current_cost, _, current = heapq.heappop(heap)
            if current in visited:
                continue
            if current_cost != distances.get(current, float("inf")):
                continue

            visited.add(current)
            explored.append(current)

            if current == goal:
                return {
                    "path": self._reconstruct_route(parents, goal),
                    "explored": explored,
                }

            row, col = current
            for dr, dc, _ in MOVE_DIRECTIONS:
                neighbor = (row + dr, col + dc)
                if neighbor not in allowed:
                    continue
                if neighbor in occupied and neighbor != start:
                    continue
                if not grid.can_move_entity(row, col, dr, dc, 1):
                    continue

                new_cost = current_cost + 10
                if new_cost < distances.get(neighbor, float("inf")):
                    distances[neighbor] = new_cost
                    parents[neighbor] = current
                    heapq.heappush(heap, (new_cost, tie_breaker, neighbor))
                    tie_breaker += 1

        return {"path": [], "explored": explored}

    def _run_local_dfs(self, grid, allowed, goals, occupied):
        start = self.get_pos()
        if start not in allowed:
            return {"path": [], "explored": []}

        valid_goals = {goal for goal in goals if goal in allowed}
        if not valid_goals:
            return {"path": [], "explored": []}

        stack = [start]
        visited = {start}
        parents = {start: None}
        explored = []

        while stack:
            current = stack.pop()
            explored.append(current)

            if current in valid_goals:
                return {
                    "path": self._reconstruct_route(parents, current),
                    "explored": explored,
                }

            row, col = current
            neighbors = []
            for dr, dc, _ in MOVE_DIRECTIONS:
                neighbor = (row + dr, col + dc)
                if neighbor not in allowed or neighbor in occupied:
                    continue
                if not grid.can_move_entity(row, col, dr, dc, 1):
                    continue
                neighbors.append(neighbor)

            for neighbor in reversed(neighbors):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parents[neighbor] = current
                    stack.append(neighbor)

        return {"path": [], "explored": explored}

    def _first_dijkstra_route(self, grid, local_area, targets, occupied, avoid_previous):
        fallback = None
        for target in targets:
            result = self._run_local_dijkstra(grid, local_area, target, occupied)
            if len(result["path"]) <= 1:
                continue
            if avoid_previous and self.previous_pos is not None and result["path"][1] == self.previous_pos:
                if fallback is None:
                    fallback = result
                continue
            return result
        return fallback

    def _reconstruct_route(self, parents, target):
        route = []
        current = target
        while current is not None:
            route.append(current)
            current = parents.get(current)
        route.reverse()
        if not route or route[0] != self.get_pos():
            return []
        return route

    def _distance_from_start(self, cell):
        return abs(cell[0] - self.row) + abs(cell[1] - self.col)

    def _distance_to_player(self, cell, player_cells):
        if not player_cells:
            return 0
        return min(abs(cell[0] - row) + abs(cell[1] - col) for row, col in player_cells)

    def _blind_target_rank(self, cell):
        return (
            self.visit_counts.get(cell, 0),
            cell == self.previous_pos,
            cell in self.visited,
            -self._distance_from_start(cell),
            self._direction_priority_to(cell),
            cell[0],
            cell[1],
        )

    def _blind_move_rank(self, move):
        index, pos, _ = move
        return (
            self.visit_counts.get(pos, 0),
            pos == self.previous_pos,
            pos in self.visited,
            index,
        )

    def _direction_priority_to(self, cell):
        dr = cell[0] - self.row
        dc = cell[1] - self.col
        if abs(dr) >= abs(dc):
            primary = (1 if dr > 0 else -1, 0)
        else:
            primary = (0, 1 if dc > 0 else -1)
        for index, (move_dr, move_dc, _) in enumerate(MOVE_DIRECTIONS):
            if primary == (move_dr, move_dc):
                return index
        return len(MOVE_DIRECTIONS)

    def _fallback_dijkstra_neighbor(self, grid, occupied, player_cells):
        moves = self._valid_moves(grid, occupied)
        if not moves:
            return None, "quieto"
        _, pos, name = min(
            moves,
            key=lambda item: (self._distance_to_player(item[1], player_cells), item[0]),
        )
        return pos, name

    def _choose_step_toward_player(self, grid, occupied, player_cells):
        moves = self._valid_moves(grid, occupied)
        if not moves:
            return None, "quieto"

        def distance_to_player(pos):
            return min(abs(pos[0] - pr) + abs(pos[1] - pc) for pr, pc in player_cells)

        _, pos, name = min(moves, key=lambda item: (distance_to_player(item[1]), item[0]))
        return pos, name

    def _move_one_cell(self, next_cell, direction):
        if next_cell is None or next_cell == self.get_pos():
            self.last_direction = direction
            return

        row_delta = abs(next_cell[0] - self.row)
        col_delta = abs(next_cell[1] - self.col)
        if row_delta + col_delta != 1:
            self.last_direction = "bloqueado"
            return

        self.previous_pos = self.get_pos()
        self.row, self.col = next_cell
        self.visited.add(next_cell)
        self.visit_counts[next_cell] = self.visit_counts.get(next_cell, 0) + 1
        self.last_direction = direction
        self._record_footstep()

    def _direction_to(self, target):
        dr = target[0] - self.row
        dc = target[1] - self.col
        for move_dr, move_dc, name in MOVE_DIRECTIONS:
            if (dr, dc) == (move_dr, move_dc):
                return name
        return "quieto"

    def _record_footstep(self):
        pos = self.get_pos()
        if pos not in self.explored:
            self.explored.append(pos)

    def _update_astar(self, grid, player_pos, occupied):
        """Persecucion informada con A*."""
        if self._needs_recalculate_astar():
            start = (self.row, self.col)
            player_cells = set(grid.entity_cells(*player_pos, PLAYER_SIZE))
            result = astar(grid, start, player_cells)

            self.last_result = result
            self.path = result.path
            self.path_index = 0
            self.steps_taken = 0

        if self.path and self.path_index < len(self.path) - 1:
            next_index = self.path_index + 1
            next_cell = self.path[next_index]

            if next_cell not in occupied:
                direction = self._direction_to(next_cell)
                self.path_index = next_index
                self.row = next_cell[0]
                self.col = next_cell[1]
                self.last_direction = direction
                self.last_decision = "A* persigue objetivo"
                self._record_footstep()

        self.steps_taken += 1

    def get_pos(self):
        return (self.row, self.col)

    def update_visual(self, dt):
        amount = min(1.0, ENTITY_LERP_SPEED * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * amount
        self.visual_col += (self.col - self.visual_col) * amount
