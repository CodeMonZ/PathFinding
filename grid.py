# ============================================================
# grid.py — Cuadrícula y estructura de grafo
# ============================================================
#
# CONCEPTO:
#   Cada celda = NODO del grafo
#   Cada movimiento = ARISTA
#   Obstáculos = nodos BLOQUEADOS
#
# Soporta MÚLTIPLES posiciones de enemigos.
#
# ============================================================

from constants import EMPTY, PLAYER_SIZE, WALL


class Grid:
    """Mapa del juego modelado como un grafo."""

    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[EMPTY] * cols for _ in range(rows)]
        self.player_start = (1, 1)
        self.enemy_starts = [(rows - 2, cols - 2)]  # Lista de enemigos

    # ---- Consultas del grafo ----

    def is_valid(self, row, col):
        """¿Está dentro del grid?"""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_walkable(self, row, col):
        """¿Se puede caminar aquí?"""
        return self.is_valid(row, col) and self.cells[row][col] != WALL

    def can_place_entity(self, row, col, size=1):
        """True si una entidad size x size cabe completa en esa posicion."""
        for r in range(row, row + size):
            for c in range(col, col + size):
                if not self.is_walkable(r, c):
                    return False
        return True

    def entity_cells(self, row, col, size=1):
        """Celdas ocupadas por una entidad size x size."""
        return [
            (r, c)
            for r in range(row, row + size)
            for c in range(col, col + size)
            if self.is_valid(r, c)
        ]

    def can_move_entity(self, row, col, dr, dc, size=1):
        """Valida movimiento en 4 direcciones para una entidad size x size."""
        if dr != 0 and dc != 0:
            return False

        new_row = row + dr
        new_col = col + dc
        return self.can_place_entity(new_row, new_col, size)

    def get_neighbors(self, row, col, size=1):
        """
        Vecinos caminables = ARISTAS del nodo en el grafo.
        Orden fijo en 4 direcciones: arriba, derecha, abajo, izquierda.
        """
        directions = [
            (-1, 0),
            (0, 1),
            (1, 0),
            (0, -1),
        ]
        neighbors = []
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if self.can_move_entity(row, col, dr, dc, size):
                neighbors.append((nr, nc))
        return neighbors

    # ---- Modificación ----

    def set_cell(self, row, col, value):
        if self.is_valid(row, col):
            self.cells[row][col] = value

    def toggle_wall(self, row, col):
        if not self.is_valid(row, col):
            return
        if self.cells[row][col] == WALL:
            self.cells[row][col] = EMPTY
        else:
            self.cells[row][col] = WALL

    def clear(self):
        self.cells = [[EMPTY] * self.cols for _ in range(self.rows)]
        self.enemy_starts = []

    # ---- Enemigos ----

    def add_enemy(self, row, col):
        """Agrega una posición de enemigo."""
        pos = (row, col)
        if pos not in self.enemy_starts:
            self.enemy_starts.append(pos)
            self.set_cell(row, col, EMPTY)  # No puede ser muro

    def remove_enemy(self, row, col):
        """Quita un enemigo de una posición."""
        pos = (row, col)
        if pos in self.enemy_starts:
            self.enemy_starts.remove(pos)

    def toggle_enemy(self, row, col):
        """Agrega o quita un enemigo en esa posición."""
        pos = (row, col)
        if pos in self.enemy_starts:
            self.enemy_starts.remove(pos)
        else:
            self.enemy_starts.append(pos)
            self.set_cell(row, col, EMPTY)

    # ---- Redimensionar ----

    def resize(self, new_cols, new_rows):
        """Cambia el tamaño del mapa, manteniendo lo que quepa."""
        new_cells = [[EMPTY] * new_cols for _ in range(new_rows)]

        # Copiar las celdas que quepan
        for r in range(min(self.rows, new_rows)):
            for c in range(min(self.cols, new_cols)):
                new_cells[r][c] = self.cells[r][c]

        self.cols = new_cols
        self.rows = new_rows
        self.cells = new_cells

        # Ajustar posiciones que queden fuera
        pr, pc = self.player_start
        max_pr = max(0, new_rows - PLAYER_SIZE)
        max_pc = max(0, new_cols - PLAYER_SIZE)
        self.player_start = (min(pr, max_pr), min(pc, max_pc))

        valid_enemies = []
        for er, ec in self.enemy_starts:
            if er < new_rows and ec < new_cols:
                valid_enemies.append((er, ec))
        self.enemy_starts = valid_enemies

        if not self.enemy_starts:
            self.enemy_starts = [(new_rows - 2, new_cols - 2)]

    # ---- Mapas prediseñados ----

    def load_map(self, number):
        self.clear()
        if number == 1:
            self._map_easy()
        elif number == 2:
            self._map_medium()
        elif number == 3:
            self._map_hard()

    def _map_easy(self):
        self.player_start = (1, 1)
        self.enemy_starts = [(self.rows - 2, self.cols - 2)]
        walls = [
            (3, 5), (3, 6), (3, 7),
            (7, 10), (8, 10), (9, 10),
            (5, 15), (6, 15),
            (11, 3), (11, 4), (11, 5),
            (2, 12), (3, 12),
        ]
        for r, c in walls:
            if self.is_valid(r, c):
                self.cells[r][c] = WALL

    def _map_medium(self):
        self.player_start = (1, 1)
        self.enemy_starts = [(self.rows - 2, self.cols - 2)]
        for c in range(3, min(12, self.cols)):
            self.cells[3][c] = WALL
        for r in range(5, min(12, self.rows)):
            self.cells[r][6] = WALL
        for c in range(10, min(18, self.cols)):
            if 10 < self.rows:
                self.cells[10][c] = WALL
        for r in range(2, min(8, self.rows)):
            if 14 < self.cols:
                self.cells[r][14] = WALL
        for c in range(16, min(19, self.cols)):
            if 5 < self.rows:
                self.cells[5][c] = WALL

    def _map_hard(self):
        self.player_start = (1, 1)
        self.enemy_starts = [(self.rows - 2, self.cols - 2)]
        wall_rows = {
            2: list(range(2, 8)) + list(range(10, 18)),
            5: list(range(1, 6)) + list(range(8, 14)),
            8: list(range(3, 10)) + list(range(12, 19)),
            11: list(range(0, 5)) + list(range(7, 16)),
        }
        for row, cols in wall_rows.items():
            if row < self.rows:
                for c in cols:
                    if c < self.cols:
                        self.cells[row][c] = WALL
        # Paredes verticales
        vert = [(3, 16), (4, 16), (6, 3), (7, 3), (9, 15), (10, 15), (12, 10), (13, 10)]
        for r, c in vert:
            if self.is_valid(r, c):
                self.cells[r][c] = WALL
