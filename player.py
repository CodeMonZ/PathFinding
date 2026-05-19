# ============================================================
# player.py — Entidad del jugador
# ============================================================

import pygame
from constants import ENTITY_LERP_SPEED, PLAYER_MOVE_DELAY, PLAYER_SIZE


class Player:
    """
    El jugador se mueve con WASD o flechas.
    Solo puede moverse a celdas caminables.
    """

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.visual_row = float(row)
        self.visual_col = float(col)
        self.size = PLAYER_SIZE
        self.move_timer = 0  # Tiempo restante antes del próximo movimiento

    def handle_input(self, keys, grid, dt):
        """
        Lee el teclado y mueve al jugador si es posible.
        dt = tiempo transcurrido en milisegundos.
        """
        # Esperar antes de permitir otro movimiento
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        dr = 0
        dc = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dr -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dr += 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dc -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dc += 1

        moved = False
        if dr != 0 or dc != 0:
            if grid.can_move_entity(self.row, self.col, dr, dc, self.size):
                self.row += dr
                self.col += dc
                moved = True
            elif dr != 0 and dc != 0:
                if grid.can_move_entity(self.row, self.col, dr, 0, self.size):
                    self.row += dr
                    moved = True
                elif grid.can_move_entity(self.row, self.col, 0, dc, self.size):
                    self.col += dc
                    moved = True

        if moved:
            self.move_timer = PLAYER_MOVE_DELAY

    def update_visual(self, dt):
        amount = min(1.0, ENTITY_LERP_SPEED * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * amount
        self.visual_col += (self.col - self.visual_col) * amount

    def occupies(self, row, col):
        return self.row <= row < self.row + self.size and self.col <= col < self.col + self.size

    def get_pos(self):
        """Retorna la posición actual como tupla (row, col)."""
        return (self.row, self.col)
