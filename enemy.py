# ============================================================
# enemy.py — Enemigo con inteligencia evolutiva
# ============================================================
#
# El enemigo sigue un camino calculado paso a paso.
# Recalcula cada N pasos para adaptarse al jugador.
#
# DFS:      cada 10 pasos → sigue caminos largos un rato
# Dijkstra: cada 3 pasos  → se adapta moderadamente
# A*:       cada 2 pasos  → siempre persiguiendo de cerca
#
# ============================================================

from constants import (
    ENEMY_SPEEDS, ENTITY_LERP_SPEED, RECALC_STEPS,
    DFS_COLOR, DIJKSTRA_COLOR, ASTAR_COLOR
)
from pathfinding import dfs, dijkstra, astar


class Enemy:
    """Enemigo que persigue al jugador."""

    def __init__(self, row, col, algorithm="dfs"):
        self.row = row
        self.col = col
        self.visual_row = float(row)
        self.visual_col = float(col)
        self.algorithm = algorithm
        self.move_timer = 0

        # Camino actual
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

        # Para visualización
        self.explored = []
        self.last_result = None

    def set_algorithm(self, algorithm):
        self.algorithm = algorithm
        self.path = []
        self.path_index = 0
        self.steps_taken = 0

    def get_color(self):
        colors = {"dfs": DFS_COLOR, "dijkstra": DIJKSTRA_COLOR, "astar": ASTAR_COLOR}
        return colors.get(self.algorithm, DFS_COLOR)

    def get_move_delay(self):
        return ENEMY_SPEEDS.get(self.algorithm, 200)

    def get_algorithm_name(self):
        names = {"dfs": "DFS", "dijkstra": "Dijkstra", "astar": "A*"}
        return names.get(self.algorithm, "???")

    def _needs_recalculate(self):
        if not self.path:
            return True
        if self.path_index >= len(self.path) - 1:
            return True
        max_steps = RECALC_STEPS.get(self.algorithm, 5)
        if self.steps_taken >= max_steps:
            return True
        return False

    def update(self, grid, player_pos, dt):
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        # ¿Recalcular?
        if self._needs_recalculate():
            start = (self.row, self.col)
            if self.algorithm == "dfs":
                result = dfs(grid, start, player_pos)
            elif self.algorithm == "dijkstra":
                result = dijkstra(grid, start, player_pos)
            else:
                result = astar(grid, start, player_pos)

            self.last_result = result
            self.path = result.path
            self.explored = result.explored
            self.path_index = 0
            self.steps_taken = 0

        # Avanzar un paso
        if self.path and self.path_index < len(self.path) - 1:
            self.path_index += 1
            self.row = self.path[self.path_index][0]
            self.col = self.path[self.path_index][1]

        self.steps_taken += 1
        self.move_timer = self.get_move_delay()

    def update_visual(self, dt):
        amount = min(1.0, ENTITY_LERP_SPEED * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * amount
        self.visual_col += (self.col - self.visual_col) * amount

    def get_pos(self):
        return (self.row, self.col)
