# ============================================================
# main.py — Game Manager
# ============================================================

import pygame
import sys
import math
from constants import *  # noqa: F401, F403
from grid import Grid
from player import Player
from enemy import Enemy
from pathfinding import dfs, dijkstra, astar


class Game:
    def __init__(self):
        pygame.init()
        self.grid = Grid(DEFAULT_COLS, DEFAULT_ROWS)
        self.grid.load_map(1)
        self.fullscreen = False
        self.resolution_index = DEFAULT_RESOLUTION_INDEX
        self.windowed_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.enemy_speed_level = DEFAULT_SPEED_LEVEL
        self.survival_time_index = DEFAULT_SURVIVAL_TIME_INDEX
        self._init_window()

        self.font_big = pygame.font.SysFont("consolas", 32, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 20)
        self.font_small = pygame.font.SysFont("consolas", 14)

        self.state = STATE_INTRO
        self.running = True
        self.algorithm = "dfs"
        self.menu_selection = 0
        self.show_path = True
        self.show_explored = True
        self.show_help = False

        # Entidades
        self.player = None
        self.enemies = []    # Lista de enemigos

        # Timer
        self.timer = 0.0

        # Editor
        self.editor_tool = "wall"
        self.mouse_dragging = False

        # Análisis animado
        self.analysis_results = None
        self.anim_step = 0
        self.anim_playing = False
        self.anim_timer = 0
        self.anim_speed = 30       # ms entre pasos
        self.anim_max = 0

        # Intro
        self.intro_timer = 0
        self.intro_duration = 2400

    def _init_window(self):
        """Crea/actualiza la ventana según el tamaño del grid."""
        if self.fullscreen:
            size = self._selected_resolution()
            flags = pygame.FULLSCREEN
        else:
            size = self.windowed_size
            flags = pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode(size, flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
        pygame.display.set_caption("Simulador de Persecución Inteligente")

    def _win_w(self):
        return self.screen.get_width()

    def _win_h(self):
        return self.screen.get_height()

    def _grid_layout(self):
        available_h = max(1, self._win_h() - HUD_HEIGHT)
        cell = max(8, min(self._win_w() // self.grid.cols, available_h // self.grid.rows))
        grid_w = self.grid.cols * cell
        grid_h = self.grid.rows * cell
        ox = (self._win_w() - grid_w) // 2
        oy = max(0, (available_h - grid_h) // 2)
        return ox, oy, cell

    def _hud_y(self):
        return self._win_h() - HUD_HEIGHT

    def _screen_to_cell(self, pos):
        ox, oy, cell = self._grid_layout()
        col = (pos[0] - ox) // cell
        row = (pos[1] - oy) // cell
        if 0 <= row < self.grid.rows and 0 <= col < self.grid.cols:
            return int(row), int(col)
        return None

    def _toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed_size = (self.screen.get_width(), self.screen.get_height())
        self.fullscreen = not self.fullscreen
        self._init_window()

    def _selected_resolution(self):
        return RESOLUTION_OPTIONS[self.resolution_index]

    def _change_resolution(self, delta=1):
        self.resolution_index = (self.resolution_index + delta) % len(RESOLUTION_OPTIONS)
        if self.fullscreen:
            self._init_window()

    def _change_enemy_speed(self, delta):
        self.enemy_speed_level = max(0, min(len(SPEED_LEVELS) - 1, self.enemy_speed_level + delta))
        for enemy in self.enemies:
            enemy.speed_multiplier = SPEED_LEVELS[self.enemy_speed_level]

    def _change_survival_time(self, delta):
        self.survival_time_index = (self.survival_time_index + delta) % len(SURVIVAL_TIME_OPTIONS)

    def _selected_survival_time(self):
        return SURVIVAL_TIME_OPTIONS[self.survival_time_index]

    # ============================================================
    # LOOP PRINCIPAL
    # ============================================================

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    # ============================================================
    # EVENTOS
    # ============================================================

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_size = (max(960, event.w), max(540, event.h))
                self._init_window()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self._toggle_fullscreen()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F10:
                self._change_resolution(1)
            elif self.state == STATE_INTRO:
                self._ev_intro(event)
            elif self.state == STATE_MENU:
                self._ev_menu(event)
            elif self.state == STATE_EDITOR:
                self._ev_editor(event)
            elif self.state == STATE_PLAYING:
                self._ev_playing(event)
            elif self.state in (STATE_GAME_OVER, STATE_WIN):
                self._ev_gameover(event)
            elif self.state == STATE_ANALYSIS:
                self._ev_analysis(event)

    def _ev_intro(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.state = STATE_MENU

    def _ev_menu(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_1:
            self.menu_selection = 0
            self.algorithm = "dfs"
        elif event.key == pygame.K_2:
            self.menu_selection = 1
            self.algorithm = "dijkstra"
        elif event.key == pygame.K_3:
            self.menu_selection = 2
            self.algorithm = "astar"
        elif event.key in (pygame.K_UP, pygame.K_LEFT):
            self.menu_selection = (self.menu_selection - 1) % 3
            self.algorithm = ("dfs", "dijkstra", "astar")[self.menu_selection]
        elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
            self.menu_selection = (self.menu_selection + 1) % 3
            self.algorithm = ("dfs", "dijkstra", "astar")[self.menu_selection]
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._change_enemy_speed(-1)
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self._change_enemy_speed(1)
        elif event.key in (pygame.K_t, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self._change_survival_time(1)
        elif event.key == pygame.K_RETURN:
            self._start_game()
        elif event.key == pygame.K_e:
            self.state = STATE_EDITOR
        elif event.key == pygame.K_TAB:
            self._start_analysis()
        elif event.key == pygame.K_ESCAPE:
            self.running = False

    def _ev_editor(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = STATE_MENU
            elif event.key == pygame.K_RETURN:
                self.state = STATE_MENU
            elif event.key == pygame.K_1:
                self.grid.load_map(1)
            elif event.key == pygame.K_2:
                self.grid.load_map(2)
            elif event.key == pygame.K_3:
                self.grid.load_map(3)
            elif event.key == pygame.K_c:
                self.grid.clear()
                self.grid.player_start = (1, 1)
                self.grid.enemy_starts = [(self.grid.rows - 2, self.grid.cols - 2)]
            elif event.key == pygame.K_w:
                self.editor_tool = "wall"
            elif event.key == pygame.K_p:
                self.editor_tool = "player"
            elif event.key == pygame.K_o:
                self.editor_tool = "enemy"

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.mouse_dragging = True
                self._editor_click(event.pos)
            elif event.button == 3:  # Click derecho = borrar
                self._editor_erase(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            self.mouse_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.mouse_dragging and self.editor_tool == "wall":
                self._editor_paint(event.pos)

    def _ev_playing(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            if self.show_help:
                self.show_help = False
                return
            self.state = STATE_MENU
        elif event.key == pygame.K_v:
            self.show_path = not self.show_path
        elif event.key == pygame.K_b:
            self.show_explored = not self.show_explored
        elif event.key == pygame.K_h:
            self.show_help = not self.show_help
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._change_enemy_speed(-1)
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self._change_enemy_speed(1)

    def _ev_gameover(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_r:
            self._start_game()
        elif event.key == pygame.K_ESCAPE:
            self.state = STATE_MENU

    def _ev_analysis(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.state = STATE_MENU
        elif event.key == pygame.K_SPACE:
            self.anim_playing = not self.anim_playing
        elif event.key == pygame.K_RIGHT:
            # Avanzar un paso manualmente
            if self.anim_step < self.anim_max:
                self.anim_step += 1
        elif event.key == pygame.K_r:
            # Reiniciar animación
            self.anim_step = 0
            self.anim_playing = False
            self.anim_timer = 0
        elif event.key == pygame.K_UP:
            self.anim_speed = max(5, self.anim_speed - 10)
        elif event.key == pygame.K_DOWN:
            self.anim_speed = min(200, self.anim_speed + 10)

    # ============================================================
    # EDITOR HELPERS
    # ============================================================

    def _resize_map(self, cols, rows):
        self.grid.resize(cols, rows)
        self._init_window()

    def _editor_click(self, pos):
        cell_pos = self._screen_to_cell(pos)
        if cell_pos is None:
            return
        row, col = cell_pos

        if self.editor_tool == "wall":
            # No poner muro sobre jugador o enemigos
            player_cells = self.grid.entity_cells(*self.grid.player_start, PLAYER_SIZE)
            if (row, col) not in player_cells and (row, col) not in self.grid.enemy_starts:
                self.grid.toggle_wall(row, col)
        elif self.editor_tool == "player":
            player_cells = self.grid.entity_cells(row, col, PLAYER_SIZE)
            if self.grid.can_place_entity(row, col, PLAYER_SIZE) and not any(cell in self.grid.enemy_starts for cell in player_cells):
                self.grid.player_start = (row, col)
                for pr, pc in player_cells:
                    self.grid.set_cell(pr, pc, EMPTY)
                self.editor_tool = "wall"
        elif self.editor_tool == "enemy":
            if (row, col) not in self.grid.entity_cells(*self.grid.player_start, PLAYER_SIZE):
                self.grid.toggle_enemy(row, col)

    def _editor_erase(self, pos):
        cell_pos = self._screen_to_cell(pos)
        if cell_pos is None:
            return
        row, col = cell_pos
        self.grid.set_cell(row, col, EMPTY)
        self.grid.remove_enemy(row, col)

    def _editor_paint(self, pos):
        cell_pos = self._screen_to_cell(pos)
        if cell_pos is None:
            return
        row, col = cell_pos
        player_cells = self.grid.entity_cells(*self.grid.player_start, PLAYER_SIZE)
        if (row, col) not in player_cells and (row, col) not in self.grid.enemy_starts:
            self.grid.set_cell(row, col, WALL)

    # ============================================================
    # ACTUALIZAR
    # ============================================================

    def update(self, dt):
        if self.state == STATE_INTRO:
            self.intro_timer += dt
            if self.intro_timer >= self.intro_duration:
                self.state = STATE_MENU
            return

        if self.state == STATE_ANALYSIS:
            if self.anim_playing and self.anim_step < self.anim_max:
                self.anim_timer += dt
                while self.anim_timer >= self.anim_speed:
                    self.anim_timer -= self.anim_speed
                    self.anim_step += 1
                    if self.anim_step >= self.anim_max:
                        self.anim_playing = False
                        break
            return

        if self.state != STATE_PLAYING:
            return

        keys = pygame.key.get_pressed()
        self.player.handle_input(keys, self.grid, dt)
        self.player.update_visual(dt)

        player_pos = self.player.get_pos()

        for i, enemy in enumerate(self.enemies):
            # Anti-superposición: celdas ocupadas por los otros enemigos
            occupied = {e.get_pos() for j, e in enumerate(self.enemies) if j != i}
            enemy.update(self.grid, player_pos, dt, occupied)
            enemy.update_visual(dt)
            if self.player.occupies(*enemy.get_pos()):
                self.state = STATE_GAME_OVER
                return

        # Timer
        self.timer -= dt / 1000.0
        if self.timer <= 0:
            self.timer = 0
            self.state = STATE_WIN

    # ============================================================
    # DIBUJAR
    # ============================================================

    def draw(self):
        self.screen.fill(BLACK)

        if self.state == STATE_INTRO:
            self._draw_intro()
        elif self.state == STATE_MENU:
            self._draw_menu()
        elif self.state == STATE_EDITOR:
            self._draw_editor()
        elif self.state == STATE_PLAYING:
            self._draw_game()
        elif self.state == STATE_GAME_OVER:
            self._draw_gameover(False)
        elif self.state == STATE_WIN:
            self._draw_gameover(True)
        elif self.state == STATE_ANALYSIS:
            self._draw_analysis()

        pygame.display.flip()

    def _draw_grid(self, ox=None, oy=None, scale=None):
        if ox is None or oy is None or scale is None:
            ox, oy, cell = self._grid_layout()
        else:
            cell = int(CELL_SIZE * scale)
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                x = ox + c * cell
                y = oy + r * cell
                rect = pygame.Rect(x, y, cell, cell)
                color = OBSTACLE_COLOR if self.grid.cells[r][c] == WALL else DARK_BLUE
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, GRID_LINE, rect, 1)

    def _draw_cell(self, row, col, color, ox=None, oy=None, scale=None, shrink=4, text=None, size=1):
        if ox is None or oy is None or scale is None:
            ox, oy, cell = self._grid_layout()
            radius_scale = cell / CELL_SIZE
        else:
            cell = int(CELL_SIZE * scale)
            radius_scale = scale
        x = ox + col * cell + shrink
        y = oy + row * cell + shrink
        rect_size = cell * size - shrink * 2
        if rect_size > 0:
            pygame.draw.rect(self.screen, color, (x, y, rect_size, rect_size), border_radius=max(2, int(6 * radius_scale)))
            if text:
                t_surf = self.font_med.render(text, True, BLACK)
                tx = x + rect_size / 2 - t_surf.get_width() / 2
                ty = y + rect_size / 2 - t_surf.get_height() / 2
                self.screen.blit(t_surf, (tx, ty))

    def _draw_overlay(self, cells, color_rgba, ox=None, oy=None, scale=None):
        if ox is None or oy is None or scale is None:
            ox, oy, cell = self._grid_layout()
        else:
            cell = int(CELL_SIZE * scale)
        surf = pygame.Surface((cell, cell), pygame.SRCALPHA)
        surf.fill(color_rgba)
        for r, c in cells:
            self.screen.blit(surf, (ox + c * cell, oy + r * cell))

    def _draw_panel(self, rect, title):
        pygame.draw.rect(self.screen, (18, 18, 42), rect, border_radius=8)
        pygame.draw.rect(self.screen, GRID_LINE, rect, 1, border_radius=8)
        self.screen.blit(self.font_small.render(title, True, DARK_GRAY), (rect.x + 12, rect.y + 10))

    def _draw_help_overlay(self):
        overlay = pygame.Surface((self._win_w(), self._win_h()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        w = min(560, self._win_w() - 80)
        h = 300
        x = self._win_w() // 2 - w // 2
        y = self._win_h() // 2 - h // 2
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, (18, 18, 42), rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, rect, 1, border_radius=10)

        title = self.font_med.render("Controles", True, WHITE)
        self.screen.blit(title, (x + 24, y + 22))
        lines = [
            ("WASD / Flechas", "Mover jugador"),
            ("V", "Mostrar u ocultar camino"),
            ("B", "Mostrar u ocultar exploracion"),
            ("+ / -", "Ajustar velocidad del enemigo"),
            ("F11", "Pantalla completa"),
            ("ESC", "Volver al menu"),
        ]
        yy = y + 70
        for key, desc in lines:
            self.screen.blit(self.font_small.render(key, True, ASTAR_COLOR), (x + 28, yy))
            self.screen.blit(self.font_small.render(desc, True, GRAY), (x + 190, yy))
            yy += 30

        hint = self.font_small.render("H para cerrar", True, DARK_GRAY)
        self.screen.blit(hint, (x + w - hint.get_width() - 24, y + h - 34))

    # ---- Menú ----

    def _draw_intro(self):
        progress = min(1.0, self.intro_timer / self.intro_duration)
        alpha = int(255 * min(1.0, progress * 1.8))
        sweep = int(self._win_w() * progress)

        self.screen.fill(BLACK)
        pygame.draw.rect(self.screen, DARK_BLUE, (0, self._win_h() // 2 - 2, sweep, 4))

        title = self.font_big.render("SIMULADOR DE PERSECUCION", True, WHITE)
        subtitle = self.font_med.render("iniciando busqueda inteligente", True, GRAY)
        hint = self.font_small.render("presiona cualquier tecla para continuar", True, DARK_GRAY)

        for surf, y in (
            (title, self._win_h() // 2 - 72),
            (subtitle, self._win_h() // 2 - 26),
            (hint, self._win_h() // 2 + 42),
        ):
            fade = surf.copy()
            fade.set_alpha(alpha)
            self.screen.blit(fade, (self._win_w() // 2 - surf.get_width() // 2, y))

        cx = self._win_w() // 2
        cy = self._win_h() // 2 + 12
        radius = 7
        dots = [
            (cx - 54, cy, DFS_COLOR),
            (cx - 18, cy, DIJKSTRA_COLOR),
            (cx + 18, cy, ASTAR_COLOR),
            (cx + 54, cy, PLAYER_COLOR),
        ]
        for index, (x, y, color) in enumerate(dots):
            if progress >= index * 0.18:
                pygame.draw.circle(self.screen, color, (x, y), radius)
                if index > 0:
                    prev_x = dots[index - 1][0]
                    pygame.draw.line(self.screen, GRID_LINE, (prev_x + radius + 3, y), (x - radius - 3, y), 2)

    def _draw_menu(self):
        ww = self._win_w()
        title = self.font_big.render("PERSECUCIÓN INTELIGENTE", True, WHITE)
        self.screen.blit(title, (ww // 2 - title.get_width() // 2, 60))

        sub = self.font_small.render("Simulador de Algoritmos de Grafos", True, GRAY)
        self.screen.blit(sub, (ww // 2 - sub.get_width() // 2, 100))

        options = [
            ("1 - DFS", DFS_COLOR),
            ("2 - Dijkstra", DIJKSTRA_COLOR),
            ("3 - A* (A-Star)", ASTAR_COLOR),
        ]
        descs = [
            "Ciego: explora sin saber dónde estás",
            "Ciego: expande por costo mínimo sin rumbo",
            "Inteligente: te persigue con heurística",
        ]
        self._draw_menu_panels(options, descs)
        return

        y = 170
        for i, (text, color) in enumerate(options):
            prefix = "▶ " if i == self.menu_selection else "  "
            c = color if i == self.menu_selection else GRAY
            self.screen.blit(self.font_med.render(prefix + text, True, c), (180, y))
            y += 36

        self.screen.blit(self.font_small.render(descs[self.menu_selection], True, DARK_GRAY), (200, y + 5))
        speed_text = f"Velocidad enemigo: x{SPEED_LEVELS[self.enemy_speed_level]:.2g}"
        time_text = f"Duracion: {self._selected_survival_time()}s"
        self.screen.blit(self.font_med.render(speed_text, True, WHITE), (180, y + 44))
        self.screen.blit(self.font_med.render(time_text, True, WHITE), (180, y + 78))
        self.screen.blit(self.font_small.render("+/- velocidad    T duracion    F11 pantalla completa", True, GRAY), (180, y + 112))

        y = 410
        info = [
            "ENTER → Jugar",
            "E     → Editor de mapas",
            "TAB   → Modo Análisis",
            "ESC   → Salir",
            "",
            f"Mapa: {self.grid.cols}x{self.grid.rows}  |  Enemigos: {len(self.grid.enemy_starts)}",
        ]
        for line in info:
            c = GRAY if line else BLACK
            self.screen.blit(self.font_small.render(line, True, c), (200, y))
            y += 22

    def _draw_menu_panels(self, options, descs):
        margin = 48
        gap = 18
        panel_y = 160
        panel_h = 270
        panel_w = (self._win_w() - margin * 2 - gap * 2) // 3
        panels = [
            pygame.Rect(margin + (panel_w + gap) * i, panel_y, panel_w, panel_h)
            for i in range(3)
        ]

        self._draw_panel(panels[0], "ALGORITMO")
        option_y = panels[0].y + 42
        for i, (text, color) in enumerate(options):
            selected = i == self.menu_selection
            row_rect = pygame.Rect(panels[0].x + 12, option_y - 6, panels[0].w - 24, 32)
            if selected:
                pygame.draw.rect(self.screen, (28, 28, 64), row_rect, border_radius=6)
                pygame.draw.rect(self.screen, color, row_rect, 1, border_radius=6)
            label = self.font_med.render(text, True, color if selected else GRAY)
            self.screen.blit(label, (row_rect.x + 12, option_y))
            option_y += 42
        self.screen.blit(
            self.font_small.render(descs[self.menu_selection], True, DARK_GRAY),
            (panels[0].x + 14, panels[0].y + 184),
        )

        self._draw_panel(panels[1], "CONFIGURACION")
        self.screen.blit(
            self.font_med.render(f"Velocidad x{SPEED_LEVELS[self.enemy_speed_level]:.2g}", True, WHITE),
            (panels[1].x + 16, panels[1].y + 48),
        )
        self.screen.blit(self.font_small.render("+ / - ajustar", True, DARK_GRAY), (panels[1].x + 18, panels[1].y + 78))
        self.screen.blit(
            self.font_med.render(f"Duracion {self._selected_survival_time()}s", True, WHITE),
            (panels[1].x + 16, panels[1].y + 116),
        )
        self.screen.blit(self.font_small.render("T cambiar", True, DARK_GRAY), (panels[1].x + 18, panels[1].y + 146))
        res_w, res_h = self._selected_resolution()
        self.screen.blit(
            self.font_small.render(f"Pantalla {res_w}x{res_h}", True, GRAY),
            (panels[1].x + 16, panels[1].y + 174),
        )
        self.screen.blit(self.font_small.render("F10 cambiar", True, DARK_GRAY), (panels[1].x + 18, panels[1].y + 198))
        self.screen.blit(
            self.font_small.render(f"Mapa {self.grid.cols}x{self.grid.rows}  |  Enemigos {len(self.grid.enemy_starts)}", True, GRAY),
            (panels[1].x + 16, panels[1].y + 220),
        )

        self._draw_panel(panels[2], "ACCIONES")
        actions = [
            ("ENTER", "Jugar"),
            ("E", "Editor de mapas"),
            ("TAB", "Modo Analisis"),
            ("F10", "Pantalla"),
            ("F11", "Pantalla completa"),
            ("ESC", "Salir"),
        ]
        action_y = panels[2].y + 44
        for key, desc in actions:
            self.screen.blit(self.font_small.render(key, True, ASTAR_COLOR), (panels[2].x + 18, action_y))
            self.screen.blit(self.font_small.render(desc, True, GRAY), (panels[2].x + 92, action_y))
            action_y += 32

    # ---- Editor ----

    def _draw_editor(self):
        self._draw_grid()

        # Jugador
        pr, pc = self.grid.player_start
        self._draw_cell(pr, pc, PLAYER_COLOR, size=PLAYER_SIZE)

        # Todos los enemigos
        for er, ec in self.grid.enemy_starts:
            self._draw_cell(er, ec, DFS_COLOR)

        self._draw_editor_hud()
        return

        # HUD
        hy = self._hud_y()
        pygame.draw.rect(self.screen, (15, 15, 35), (0, hy, self._win_w(), HUD_HEIGHT))

        tool_text = f"Herramienta: {self.editor_tool.upper()}  |  Enemigos: {len(self.grid.enemy_starts)}"
        self.screen.blit(self.font_small.render(tool_text, True, WHITE), (10, hy + 5))

        line1 = "W=Muro  P=Jugador  O=Enemigo(+/-)  C=Limpiar  1/2/3=Mapas"
        self.screen.blit(self.font_small.render(line1, True, GRAY), (10, hy + 24))

        line2 = "Click der=Borrar  ESC/ENTER=Menú"
        self.screen.blit(self.font_small.render(line2, True, GRAY), (10, hy + 43))

        self.screen.blit(self.font_small.render("■ Jugador", True, PLAYER_COLOR), (10, hy + 62))
        self.screen.blit(self.font_small.render("■ Enemigo", True, DFS_COLOR), (120, hy + 62))

    def _draw_editor_hud(self):
        hy = self._hud_y()
        pygame.draw.rect(self.screen, (12, 12, 30), (0, hy, self._win_w(), HUD_HEIGHT))

        margin = 18
        gap = 12
        usable_w = self._win_w() - margin * 2 - gap * 3
        panel_w = usable_w // 4
        panel_h = HUD_HEIGHT - 24
        y = hy + 12
        panels = [
            pygame.Rect(margin + (panel_w + gap) * i, y, panel_w, panel_h)
            for i in range(4)
        ]

        tool_names = {"wall": "Muro", "player": "Jugador", "enemy": "Enemigo"}
        self._draw_panel(panels[0], "HERRAMIENTA")
        self.screen.blit(
            self.font_med.render(tool_names.get(self.editor_tool, self.editor_tool), True, WHITE),
            (panels[0].x + 12, panels[0].y + 34),
        )
        self.screen.blit(self.font_small.render("Click pinta", True, GRAY), (panels[0].x + 12, panels[0].y + 66))
        self.screen.blit(self.font_small.render("Derecho borra", True, GRAY), (panels[0].x + 12, panels[0].y + 88))

        self._draw_panel(panels[1], "MAPA")
        self.screen.blit(
            self.font_med.render(f"{self.grid.cols} x {self.grid.rows}", True, WHITE),
            (panels[1].x + 12, panels[1].y + 34),
        )
        self.screen.blit(
            self.font_small.render(f"Enemigos: {len(self.grid.enemy_starts)}", True, GRAY),
            (panels[1].x + 12, panels[1].y + 66),
        )
        self.screen.blit(self.font_small.render("1 / 2 / 3 mapas", True, GRAY), (panels[1].x + 12, panels[1].y + 88))

        self._draw_panel(panels[2], "EDICION")
        actions = [("W", "Muro"), ("P", "Jugador"), ("O", "Enemigo"), ("C", "Limpiar")]
        action_y = panels[2].y + 34
        for key, desc in actions:
            self.screen.blit(self.font_small.render(key, True, ASTAR_COLOR), (panels[2].x + 12, action_y))
            self.screen.blit(self.font_small.render(desc, True, GRAY), (panels[2].x + 54, action_y))
            action_y += 20

        self._draw_panel(panels[3], "SALIDA")
        self.screen.blit(self.font_small.render("ENTER Menu", True, GRAY), (panels[3].x + 12, panels[3].y + 34))
        self.screen.blit(self.font_small.render("ESC Menu", True, GRAY), (panels[3].x + 12, panels[3].y + 56))

        legend_y = panels[3].y + 84
        legend = [
            (PLAYER_COLOR, "Jugador", panels[3].x + 12, legend_y),
            (DFS_COLOR, "Enemigo", panels[3].x + 112, legend_y),
            (OBSTACLE_COLOR, "Muro", panels[3].x + 226, legend_y),
        ]
        for color, label, x, y in legend:
            pygame.draw.rect(self.screen, color, (x, y, 14, 14), border_radius=3)
            self.screen.blit(self.font_small.render(label, True, GRAY), (x + 20, y - 1))

    # ---- Juego ----

    def _draw_game(self):
        self._draw_grid()

        # Overlay de exploración y camino de cada enemigo
        for enemy in self.enemies:
            color = enemy.get_color()
            scan_cells = getattr(enemy, "scan_cells", [])
            if self.show_explored and scan_cells:
                self._draw_overlay(scan_cells, (color[0], color[1], color[2], 18))
            if self.show_explored and enemy.explored:
                self._draw_overlay(enemy.explored, (color[0], color[1], color[2], 30))
            if self.show_path and enemy.path:
                self._draw_overlay(enemy.path, (color[0], color[1], color[2], 80))

        # Jugador (movimiento suave, SIN exclamación)
        self._draw_cell(self.player.visual_row, self.player.visual_col, PLAYER_COLOR, size=self.player.size)

        # Enemigos (movimiento suave, CON exclamación si persiguen)
        for enemy in self.enemies:
            self._draw_cell(enemy.visual_row, enemy.visual_col, enemy.get_color())
            if getattr(enemy, "is_alerted", False):
                self._draw_alert_marker(enemy)

        self._draw_game_hud()
        if self.show_help:
            self._draw_help_overlay()

    def _draw_alert_marker(self, enemy):
        ox, oy, cell = self._grid_layout()
        pulse = (math.sin(pygame.time.get_ticks() / 180.0) + 1) / 2
        y_offset = 10 + int(5 * pulse)
        alpha = 150 + int(105 * pulse)
        x = ox + enemy.visual_col * cell + cell // 2
        y = oy + enemy.visual_row * cell - y_offset

        surf = self.font_med.render("!", True, WHITE)
        surf.set_alpha(alpha)
        halo_radius = max(8, cell // 5)
        halo = pygame.Surface((halo_radius * 2, halo_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*enemy.get_color(), 60 + int(80 * pulse)), (halo_radius, halo_radius), halo_radius)
        self.screen.blit(halo, (x - halo_radius, y - halo_radius + 4))
        self.screen.blit(surf, (x - surf.get_width() // 2, y - surf.get_height() // 2))

    def _draw_game_hud(self):
        hy = self._hud_y()
        pygame.draw.rect(self.screen, (12, 12, 30), (0, hy, self._win_w(), HUD_HEIGHT))

        margin = 18
        gap = 12
        usable_w = self._win_w() - margin * 2 - gap * 3
        panel_w = usable_w // 4
        panel_h = HUD_HEIGHT - 24
        y = hy + 12
        panels = [
            pygame.Rect(margin + (panel_w + gap) * i, y, panel_w, panel_h)
            for i in range(4)
        ]

        algo_text = self.enemies[0].get_algorithm_name() if self.enemies else "?"
        algo_color = self.enemies[0].get_color() if self.enemies else WHITE
        speed = SPEED_LEVELS[self.enemy_speed_level]
        selected_time = self._selected_survival_time()
        timer_color = WHITE if self.timer > 10 else DFS_COLOR

        self._draw_panel(panels[0], "ENEMIGO")
        self.screen.blit(self.font_med.render(algo_text, True, algo_color), (panels[0].x + 12, panels[0].y + 34))
        self.screen.blit(self.font_small.render(f"{len(self.enemies)} activos", True, GRAY), (panels[0].x + 12, panels[0].y + 66))
        direction = getattr(self.enemies[0], "last_direction", "inicio") if self.enemies else "inicio"
        self.screen.blit(self.font_small.render(f"Paso: {direction}", True, GRAY), (panels[0].x + 12, panels[0].y + 88))

        self._draw_panel(panels[1], "VELOCIDAD")
        self.screen.blit(self.font_med.render(f"x{speed:.2g}", True, WHITE), (panels[1].x + 12, panels[1].y + 34))
        self.screen.blit(self.font_small.render("+ / - ajustar", True, GRAY), (panels[1].x + 12, panels[1].y + 66))

        self._draw_panel(panels[2], "TIEMPO")
        timer_text = self.font_med.render(f"{self.timer:.1f}s", True, timer_color)
        self.screen.blit(timer_text, (panels[2].x + 12, panels[2].y + 34))
        bar_w = max(80, panels[2].w - 24)
        bar_h = 12
        bx = panels[2].x + 12
        by = panels[2].y + 72
        pygame.draw.rect(self.screen, DARK_GRAY, (bx, by, bar_w, bar_h), border_radius=6)
        progress = max(0, min(1, (selected_time - self.timer) / selected_time))
        if progress > 0:
            pygame.draw.rect(self.screen, ASTAR_COLOR, (bx, by, int(bar_w * progress), bar_h), border_radius=6)
        pygame.draw.rect(self.screen, WHITE, (bx, by, bar_w, bar_h), 1, border_radius=6)

        self._draw_panel(panels[3], "OBJETIVO")
        self.screen.blit(self.font_med.render(f"{selected_time}s", True, GRAY), (panels[3].x + 12, panels[3].y + 34))
        self.screen.blit(self.font_small.render("H controles", True, GRAY), (panels[3].x + 12, panels[3].y + 66))

    # ---- Game Over ----

    def _draw_gameover(self, won):
        self._draw_grid()
        if self.player:
            self._draw_cell(self.player.row, self.player.col, PLAYER_COLOR, size=self.player.size)
        for enemy in self.enemies:
            self._draw_cell(enemy.row, enemy.col, enemy.get_color())

        overlay = pygame.Surface((self._win_w(), self._win_h()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = self._win_w() // 2

        if won:
            title, color = "¡GANASTE!", ASTAR_COLOR
            msg = f"Sobreviviste {self._selected_survival_time()} segundos"
        else:
            title, color = "¡TE ATRAPARON!", DFS_COLOR
            msg = f"Sobreviviste {self._selected_survival_time() - self.timer:.1f} segundos"

        t = self.font_big.render(title, True, color)
        self.screen.blit(t, (cx - t.get_width() // 2, 180))

        t = self.font_med.render(msg, True, WHITE)
        self.screen.blit(t, (cx - t.get_width() // 2, 240))

        if self.enemies:
            algo = f"Algoritmo: {self.enemies[0].get_algorithm_name()}"
            t = self.font_med.render(algo, True, self.enemies[0].get_color())
            self.screen.blit(t, (cx - t.get_width() // 2, 280))

            t = self.font_med.render(f"Enemigos: {len(self.enemies)}", True, GRAY)
            self.screen.blit(t, (cx - t.get_width() // 2, 310))

        t = self.font_small.render("R = Reintentar    ESC = Menú", True, GRAY)
        self.screen.blit(t, (cx - t.get_width() // 2, 380))

    # ---- Análisis (animado) ----

    def _draw_analysis(self):
        if not self.analysis_results:
            return

        results = self.analysis_results
        start = self.grid.enemy_starts[0] if self.grid.enemy_starts else (self.grid.rows - 2, self.grid.cols - 2)
        goal = self.grid.player_start

        self._draw_analysis_layout(results, start, goal)

    def _draw_analysis_layout(self, results, start, goal):
        margin = max(24, self._win_w() // 40)
        gap = 18
        hud_h = 148
        hud_y = self._win_h() - hud_h - 16
        cards_y = 88
        cards_h = max(220, hud_y - cards_y - 18)
        usable_w = self._win_w() - margin * 2 - gap * 2
        card_w = usable_w // 3

        title = self.font_big.render("MODO ANALISIS", True, WHITE)
        self.screen.blit(title, (self._win_w() // 2 - title.get_width() // 2, 24))

        mini_cell = max(
            7,
            min(
                (card_w - 28) // self.grid.cols,
                (cards_h - 86) // self.grid.rows,
            ),
        )
        mini_scale = mini_cell / CELL_SIZE
        grid_w = self.grid.cols * mini_cell
        grid_h = self.grid.rows * mini_cell

        for index, (name, result, color) in enumerate(results):
            card = pygame.Rect(margin + index * (card_w + gap), cards_y, card_w, cards_h)
            self._draw_panel(card, name.upper())

            label = self.font_med.render(name, True, color)
            self.screen.blit(label, (card.x + 14, card.y + 32))

            ox = card.x + (card.w - grid_w) // 2
            oy = card.y + 66
            self._draw_grid(ox, oy, mini_scale)

            completed = self.anim_step >= len(result.explored)
            if not completed:
                visible_explored = result.explored[:min(self.anim_step, len(result.explored))]
                if visible_explored:
                    self._draw_overlay(visible_explored, (color[0], color[1], color[2], 55), ox, oy, mini_scale)
            elif result.path:
                self._draw_overlay(result.path, (color[0], color[1], color[2], 140), ox, oy, mini_scale)

            self._draw_cell(start[0], start[1], color, ox, oy, mini_scale, 2)
            self._draw_cell(goal[0], goal[1], PLAYER_COLOR, ox, oy, mini_scale, 2, size=PLAYER_SIZE)

            shown = min(self.anim_step, len(result.explored))
            stats_y = oy + grid_h + 12
            self.screen.blit(
                self.font_small.render(f"Nodos {shown}/{result.nodes_explored}", True, GRAY),
                (card.x + 14, stats_y),
            )
            path_text = f"Camino {len(result.path)}" if completed else "Camino --"
            self.screen.blit(
                self.font_small.render(path_text, True, color if completed else DARK_GRAY),
                (card.x + 14, stats_y + 22),
            )

        self._draw_analysis_hud(hud_y, hud_h, results)

    def _draw_analysis_hud(self, y, height, results):
        pygame.draw.rect(self.screen, (12, 12, 30), (0, y - 8, self._win_w(), height + 16))

        margin = max(24, self._win_w() // 40)
        gap = 14
        status_w = max(230, self._win_w() // 5)
        controls_w = max(330, self._win_w() // 4)
        compare_w = self._win_w() - margin * 2 - gap * 2 - status_w - controls_w
        panels = [
            pygame.Rect(margin, y, status_w, height),
            pygame.Rect(margin + status_w + gap, y, compare_w, height),
            pygame.Rect(margin + status_w + gap + compare_w + gap, y, controls_w, height),
        ]

        status = "Reproduciendo" if self.anim_playing else "Pausado"
        status_color = WHITE
        if self.anim_step >= self.anim_max:
            status = "Completado"
            status_color = ASTAR_COLOR

        self._draw_panel(panels[0], "ESTADO")
        self.screen.blit(self.font_med.render(status, True, status_color), (panels[0].x + 14, panels[0].y + 36))
        self.screen.blit(
            self.font_small.render(f"Paso {self.anim_step}/{self.anim_max}", True, GRAY),
            (panels[0].x + 14, panels[0].y + 72),
        )
        self.screen.blit(
            self.font_small.render(f"Velocidad {self.anim_speed}ms", True, GRAY),
            (panels[0].x + 14, panels[0].y + 96),
        )

        self._draw_panel(panels[1], "COMPARACION")
        r_dfs, r_dij, r_ast = results[0][1], results[1][1], results[2][1]
        col_colors = [GRAY, DFS_COLOR, DIJKSTRA_COLOR, ASTAR_COLOR]
        headers = ["Metrica", "DFS", "Dijkstra", "A*"]
        rows = [
            ("Nodos", str(r_dfs.nodes_explored), str(r_dij.nodes_explored), str(r_ast.nodes_explored)),
            ("Camino", str(len(r_dfs.path)), str(len(r_dij.path)), str(len(r_ast.path))),
        ]
        start_x = panels[1].x + 16
        col_w = max(82, (panels[1].w - 32) // 4)
        for index, header in enumerate(headers):
            self.screen.blit(self.font_small.render(header, True, col_colors[index]), (start_x + index * col_w, panels[1].y + 36))
        for row_index, row in enumerate(rows):
            row_y = panels[1].y + 70 + row_index * 28
            for col_index, text in enumerate(row):
                self.screen.blit(self.font_small.render(text, True, col_colors[col_index]), (start_x + col_index * col_w, row_y))

        self._draw_panel(panels[2], "CONTROLES")
        controls = [
            ("SPACE", "Play/Pausa"),
            ("DERECHA", "Paso"),
            ("R", "Reiniciar"),
            ("ARR/ABA", "Velocidad"),
            ("ESC", "Menu"),
        ]
        for index, (key, desc) in enumerate(controls):
            row_y = panels[2].y + 34 + index * 22
            self.screen.blit(self.font_small.render(key, True, ASTAR_COLOR), (panels[2].x + 14, row_y))
            self.screen.blit(self.font_small.render(desc, True, GRAY), (panels[2].x + 128, row_y))

    # ============================================================
    # ACCIONES
    # ============================================================

    def _start_game(self):
        pr, pc = self.grid.player_start
        self.player = Player(pr, pc)

        self.enemies = []
        for er, ec in self.grid.enemy_starts:
            enemy = Enemy(er, ec, self.algorithm)
            enemy.speed_multiplier = SPEED_LEVELS[self.enemy_speed_level]
            self.enemies.append(enemy)

        self.timer = self._selected_survival_time()
        self.state = STATE_PLAYING

    def _start_analysis(self):
        """Calcula los 3 algoritmos y prepara la animación."""
        # En analisis el enemigo busca al jugador.
        start = self.grid.enemy_starts[0] if self.grid.enemy_starts else (self.grid.rows - 2, self.grid.cols - 2)
        goal = set(self.grid.entity_cells(*self.grid.player_start, PLAYER_SIZE))

        self.analysis_results = [
            ("DFS", dfs(self.grid, start, goal), DFS_COLOR),
            ("Dijkstra", dijkstra(self.grid, start, goal), DIJKSTRA_COLOR),
            ("A*", astar(self.grid, start, goal), ASTAR_COLOR),
        ]

        # Máximo de pasos = el algoritmo que más nodos exploró
        self.anim_max = max(len(r.explored) for _, r, _ in self.analysis_results)
        self.anim_step = 0
        self.anim_playing = False
        self.anim_timer = 0
        self.state = STATE_ANALYSIS


# ============================================================
if __name__ == "__main__":
    Game().run()
