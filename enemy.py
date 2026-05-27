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

from constants import (
    ASTAR_COLOR,
    ASTAR_RECALC_STEPS,
    DFS_COLOR,
    DIJKSTRA_COLOR,
    ENEMY_SPEEDS,
    ENTITY_LERP_SPEED,
    PLAYER_SIZE,
)
from pathfinding import astar, DFSExplorer, DijkstraExplorer


class Enemy:
    """Enemigo que busca o persigue segun el algoritmo seleccionado."""

    def __init__(self, row, col, algorithm="dfs"):
        self.row = row
        self.col = col
        self.algorithm = algorithm
        self.move_timer = 0

        self.visual_row = float(row)
        self.visual_col = float(col)

        # Explorador ciego usado por DFS y Dijkstra.
        self.explorer = None
        self.travel_path = []

        # Camino calculado solo para A*.
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

        self.is_alerted = False
        self.explored = [(row, col)]
        self.last_result = None

    def set_algorithm(self, algorithm):
        self.algorithm = algorithm
        self.explorer = None
        self.travel_path = []
        self.path = []
        self.path_index = 0
        self.steps_taken = 0
        self.is_alerted = False
        self.explored = [(self.row, self.col)]
        self.last_result = None

    def get_color(self):
        colors = {"dfs": DFS_COLOR, "dijkstra": DIJKSTRA_COLOR, "astar": ASTAR_COLOR}
        return colors.get(self.algorithm, DFS_COLOR)

    def get_move_delay(self):
        return ENEMY_SPEEDS.get(self.algorithm, 200)

    def get_algorithm_name(self):
        names = {"dfs": "DFS", "dijkstra": "Dijkstra", "astar": "A*"}
        return names.get(self.algorithm, "???")

    def _init_explorer(self, grid):
        """Crea una busqueda ciega nueva desde la posicion actual."""
        start = (self.row, self.col)
        self.travel_path = []
        self.explored = [start]
        if self.algorithm == "dfs":
            self.explorer = DFSExplorer(grid, start)
        elif self.algorithm == "dijkstra":
            self.explorer = DijkstraExplorer(grid, start)

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
            self._update_blind(grid, occupied)
        else:
            self.is_alerted = True
            self._update_astar(grid, player_pos, occupied)

        self.move_timer = self.get_move_delay()

    def _update_blind(self, grid, occupied):
        """Exploracion ciega paso a paso y ciclica."""
        if self._follow_travel_path(occupied):
            return

        if self.explorer is None or self.explorer.finished:
            self._init_explorer(grid)

        next_cell = self.explorer.step()

        if next_cell is not None:
            self._set_travel_target(next_cell)
            self._follow_travel_path(occupied)
        else:
            # Cuando agota el mapa, vuelve a empezar desde donde quedo.
            self._init_explorer(grid)

    def _set_travel_target(self, target):
        current = self.get_pos()
        if target == current:
            self.travel_path = []
            return

        route = []
        if self.explorer is not None and hasattr(self.explorer, "path_between"):
            route = self.explorer.path_between(current, target)

        if not route:
            route = [current, target]

        self.travel_path = route[1:]

    def _follow_travel_path(self, occupied):
        while self.travel_path and self.travel_path[0] == self.get_pos():
            self.travel_path.pop(0)

        if not self.travel_path:
            return False

        next_cell = self.travel_path[0]
        if next_cell in occupied:
            return True

        self.row, self.col = next_cell
        self.travel_path.pop(0)
        self._record_footstep()
        return True

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
                self.path_index = next_index
                self.row = next_cell[0]
                self.col = next_cell[1]
                self._record_footstep()

        self.steps_taken += 1

    def get_pos(self):
        return (self.row, self.col)

    def update_visual(self, dt):
        amount = min(1.0, ENTITY_LERP_SPEED * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * amount
        self.visual_col += (self.col - self.visual_col) * amount
