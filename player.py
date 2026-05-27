# ============================================================
# player.py - Entidad del jugador
# ============================================================

import pygame
from constants import ENTITY_LERP_SPEED, PLAYER_MOVE_DELAY, PLAYER_SIZE


class Player:
    """
    El jugador se mueve con WASD o flechas.
    Solo se mueve en 4 direcciones.
    """

    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.size = PLAYER_SIZE
        self.move_timer = 0
        self.visual_row = float(row)
        self.visual_col = float(col)

    def handle_input(self, keys, grid, dt):
        self.move_timer -= dt
        if self.move_timer > 0:
            return

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dr, dc = -1, 0
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dr, dc = 1, 0
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dr, dc = 0, -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dr, dc = 0, 1
        else:
            return

        if grid.can_move_entity(self.row, self.col, dr, dc, self.size):
            self.row += dr
            self.col += dc
            self.move_timer = PLAYER_MOVE_DELAY

    def get_pos(self):
        return (self.row, self.col)

    def occupies(self, row, col):
        return self.row <= row < self.row + self.size and self.col <= col < self.col + self.size

    def update_visual(self, dt):
        amount = min(1.0, ENTITY_LERP_SPEED * dt / 1000.0)
        self.visual_row += (self.row - self.visual_row) * amount
        self.visual_col += (self.col - self.visual_col) * amount
