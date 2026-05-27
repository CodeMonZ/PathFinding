# ============================================================
# main.py — Game Manager
# ============================================================

import pygame
import sys
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
        self._init_window()

        self.font_big = pygame.font.SysFont("consolas", 32, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 20)
        self.font_small = pygame.font.SysFont("consolas", 14)

        self.state = STATE_MENU
        self.running = True
        self.algorithm = "dfs"
        self.menu_selection = 0
        self.show_path = True
        self.show_explored = True

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

    def _init_window(self):
        """Crea/actualiza la ventana según el tamaño del grid."""
        w = self.grid.cols * CELL_SIZE
        h = self.grid.rows * CELL_SIZE + HUD_HEIGHT
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Simulador de Persecución Inteligente")

    def _win_w(self):
        return self.grid.cols * CELL_SIZE

    def _win_h(self):
        return self.grid.rows * CELL_SIZE + HUD_HEIGHT

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
            self.state = STATE_MENU
        elif event.key == pygame.K_v:
            self.show_path = not self.show_path
        elif event.key == pygame.K_b:
            self.show_explored = not self.show_explored

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
        col = pos[0] // CELL_SIZE
        row = pos[1] // CELL_SIZE
        if not self.grid.is_valid(row, col):
            return

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
        col = pos[0] // CELL_SIZE
        row = pos[1] // CELL_SIZE
        if self.grid.is_valid(row, col):
            self.grid.set_cell(row, col, EMPTY)
            self.grid.remove_enemy(row, col)

    def _editor_paint(self, pos):
        col = pos[0] // CELL_SIZE
        row = pos[1] // CELL_SIZE
        if self.grid.is_valid(row, col):
            player_cells = self.grid.entity_cells(*self.grid.player_start, PLAYER_SIZE)
            if (row, col) not in player_cells and (row, col) not in self.grid.enemy_starts:
                self.grid.set_cell(row, col, WALL)

    # ============================================================
    # ACTUALIZAR
    # ============================================================

    def update(self, dt):
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

        if self.state == STATE_MENU:
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

    def _draw_grid(self, ox=0, oy=0, scale=1.0):
        cell = int(CELL_SIZE * scale)
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                x = ox + c * cell
                y = oy + r * cell
                rect = pygame.Rect(x, y, cell, cell)
                color = OBSTACLE_COLOR if self.grid.cells[r][c] == WALL else DARK_BLUE
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, GRID_LINE, rect, 1)

    def _draw_cell(self, row, col, color, ox=0, oy=0, scale=1.0, shrink=4, text=None, size=1):
        cell = int(CELL_SIZE * scale)
        x = ox + col * cell + shrink
        y = oy + row * cell + shrink
        rect_size = cell * size - shrink * 2
        if rect_size > 0:
            pygame.draw.rect(self.screen, color, (x, y, rect_size, rect_size), border_radius=max(2, int(6 * scale)))
            if text:
                t_surf = self.font_med.render(text, True, BLACK)
                tx = x + rect_size / 2 - t_surf.get_width() / 2
                ty = y + rect_size / 2 - t_surf.get_height() / 2
                self.screen.blit(t_surf, (tx, ty))

    def _draw_overlay(self, cells, color_rgba, ox=0, oy=0, scale=1.0):
        cell = int(CELL_SIZE * scale)
        surf = pygame.Surface((cell, cell), pygame.SRCALPHA)
        surf.fill(color_rgba)
        for r, c in cells:
            self.screen.blit(surf, (ox + c * cell, oy + r * cell))

    # ---- Menú ----

    def _draw_menu(self):
        ww = self._win_w()
        title = self.font_big.render("PERSECUCIÓN INTELIGENTE", True, WHITE)
        self.screen.blit(title, (ww // 2 - title.get_width() // 2, 60))

        sub = self.font_small.render("Simulador de Algoritmos de Grafos", True, GRAY)
        self.screen.blit(sub, (ww // 2 - sub.get_width() // 2, 100))

        options = [
            ("1 - DFS (Profundidad)", DFS_COLOR),
            ("2 - Dijkstra", DIJKSTRA_COLOR),
            ("3 - A* (A-Star)", ASTAR_COLOR),
        ]
        descs = [
            "Ciego: explora sin saber dónde estás",
            "Ciego: expande por costo mínimo sin rumbo",
            "Inteligente: te persigue con heurística",
        ]

        y = 170
        for i, (text, color) in enumerate(options):
            prefix = "▶ " if i == self.menu_selection else "  "
            c = color if i == self.menu_selection else GRAY
            self.screen.blit(self.font_med.render(prefix + text, True, c), (180, y))
            y += 36

        self.screen.blit(self.font_small.render(descs[self.menu_selection], True, DARK_GRAY), (200, y + 5))

        y = 380
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

    # ---- Editor ----

    def _draw_editor(self):
        self._draw_grid()

        # Jugador
        pr, pc = self.grid.player_start
        self._draw_cell(pr, pc, PLAYER_COLOR, size=PLAYER_SIZE)

        # Todos los enemigos
        for er, ec in self.grid.enemy_starts:
            self._draw_cell(er, ec, DFS_COLOR)

        # HUD
        hy = self.grid.rows * CELL_SIZE
        pygame.draw.rect(self.screen, (15, 15, 35), (0, hy, self._win_w(), HUD_HEIGHT))

        tool_text = f"Herramienta: {self.editor_tool.upper()}  |  Enemigos: {len(self.grid.enemy_starts)}"
        self.screen.blit(self.font_small.render(tool_text, True, WHITE), (10, hy + 5))

        line1 = "W=Muro  P=Jugador  O=Enemigo(+/-)  C=Limpiar  1/2/3=Mapas"
        self.screen.blit(self.font_small.render(line1, True, GRAY), (10, hy + 24))

        line2 = "Click der=Borrar  ESC/ENTER=Menú"
        self.screen.blit(self.font_small.render(line2, True, GRAY), (10, hy + 43))

        self.screen.blit(self.font_small.render("■ Jugador", True, PLAYER_COLOR), (10, hy + 62))
        self.screen.blit(self.font_small.render("■ Enemigo", True, DFS_COLOR), (120, hy + 62))

    # ---- Juego ----

    def _draw_game(self):
        self._draw_grid()

        # Overlay de exploración y camino de cada enemigo
        for enemy in self.enemies:
            color = enemy.get_color()
            if self.show_explored and enemy.explored:
                self._draw_overlay(enemy.explored, (color[0], color[1], color[2], 30))
            if self.show_path and enemy.path:
                self._draw_overlay(enemy.path, (color[0], color[1], color[2], 80))

        # Jugador (movimiento suave, SIN exclamación)
        self._draw_cell(self.player.visual_row, self.player.visual_col, PLAYER_COLOR, size=self.player.size)

        # Enemigos (movimiento suave, CON exclamación si persiguen)
        for enemy in self.enemies:
            exclamacion = "!" if getattr(enemy, 'is_alerted', False) else None
            self._draw_cell(enemy.visual_row, enemy.visual_col, enemy.get_color(), text=exclamacion)

        # HUD
        hy = self.grid.rows * CELL_SIZE
        pygame.draw.rect(self.screen, (15, 15, 35), (0, hy, self._win_w(), HUD_HEIGHT))

        # Algoritmo
        algo_text = f"Algoritmo: {self.enemies[0].get_algorithm_name() if self.enemies else '?'}"
        algo_color = self.enemies[0].get_color() if self.enemies else WHITE
        self.screen.blit(self.font_med.render(algo_text, True, algo_color), (10, hy + 5))

        # Enemigos
        self.screen.blit(
            self.font_small.render(f"Enemigos: {len(self.enemies)}", True, GRAY), (10, hy + 32)
        )

        # Timer
        timer_color = WHITE if self.timer > 10 else DFS_COLOR
        self.screen.blit(
            self.font_med.render(f"Tiempo: {self.timer:.1f}s", True, timer_color),
            (self._win_w() // 2 - 50, hy + 5)
        )

        # Barra de tiempo (con bordes redondeados)
        bar_w = 200
        bar_h = 15
        bx = self._win_w() // 2 - bar_w // 2
        by = hy + 35
        pygame.draw.rect(self.screen, DARK_GRAY, (bx, by, bar_w, bar_h), border_radius=7)
        progress = max(0, min(1, (SURVIVAL_TIME - self.timer) / SURVIVAL_TIME))
        if progress > 0:
            pygame.draw.rect(self.screen, ASTAR_COLOR, (bx, by, int(bar_w * progress), bar_h), border_radius=7)
        pygame.draw.rect(self.screen, WHITE, (bx, by, bar_w, bar_h), 1, border_radius=7)

        # Controles
        self.screen.blit(
            self.font_small.render("V=Camino  B=Explorados  ESC=Menú", True, DARK_GRAY),
            (10, hy + 55)
        )

        # Meta
        self.screen.blit(
            self.font_small.render(f"¡Sobrevive {SURVIVAL_TIME}s!", True, GRAY),
            (self._win_w() - 140, hy + 55)
        )

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
            msg = f"Sobreviviste {SURVIVAL_TIME} segundos"
        else:
            title, color = "¡TE ATRAPARON!", DFS_COLOR
            msg = f"Sobreviviste {SURVIVAL_TIME - self.timer:.1f} segundos"

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

        title = self.font_big.render("MODO ANÁLISIS", True, WHITE)
        self.screen.blit(title, (self._win_w() // 2 - title.get_width() // 2, 10))

        # 3 mini grids animados
        mini_scale = 0.3
        mini_cell = int(CELL_SIZE * mini_scale)
        grid_w = self.grid.cols * mini_cell
        spacing = (self._win_w() - 3 * grid_w) // 4

        for i, (name, result, color) in enumerate(results):
            ox = spacing + i * (grid_w + spacing)
            oy = 85

            t = self.font_med.render(name, True, color)
            self.screen.blit(t, (ox, oy - 20))

            # Grid base
            self._draw_grid(ox, oy, mini_scale)

            # Nodos explorados hasta el paso actual (ANIMACIÓN)
            completed = self.anim_step >= len(result.explored)
            if not completed:
                visible_explored = result.explored[:min(self.anim_step, len(result.explored))]
                if visible_explored:
                    self._draw_overlay(visible_explored, (color[0], color[1], color[2], 55), ox, oy, mini_scale)

            # Mostrar camino solo cuando este algoritmo terminó de explorar
            if completed and result.path:
                self._draw_overlay(result.path, (color[0], color[1], color[2], 140), ox, oy, mini_scale)

            # Inicio enemigo y meta jugador
            self._draw_cell(start[0], start[1], color, ox, oy, mini_scale, 2)
            self._draw_cell(goal[0], goal[1], PLAYER_COLOR, ox, oy, mini_scale, 2, size=PLAYER_SIZE)

            # Estadísticas debajo
            sy = oy + self.grid.rows * mini_cell + 8
            # Nodos mostrados vs total
            shown = min(self.anim_step, len(result.explored))
            self.screen.blit(self.font_small.render(f"Nodos: {shown}/{result.nodes_explored}", True, GRAY), (ox, sy))
            # Camino (solo si terminó)
            if completed:
                self.screen.blit(self.font_small.render(f"Camino: {len(result.path)}", True, color), (ox, sy + 18))

        # Tabla comparativa
        ty = self._win_h() - 140
        self.screen.blit(self.font_med.render("Comparación", True, WHITE), (self._win_w() // 2 - 60, ty))
        ty += 28

        cols_x = [80, 230, 380, 530]
        headers = ["Métrica", "DFS", "Dijkstra", "A*"]
        for ci, h in enumerate(headers):
            self.screen.blit(self.font_small.render(h, True, WHITE), (cols_x[ci], ty))

        r_dfs, r_dij, r_ast = results[0][1], results[1][1], results[2][1]
        table_rows = [
            ("Nodos explorados", str(r_dfs.nodes_explored), str(r_dij.nodes_explored), str(r_ast.nodes_explored)),
            ("Longitud camino", str(len(r_dfs.path)), str(len(r_dij.path)), str(len(r_ast.path))),
        ]
        col_colors = [GRAY, DFS_COLOR, DIJKSTRA_COLOR, ASTAR_COLOR]
        for ri, row_data in enumerate(table_rows):
            y = ty + 22 + ri * 20
            for ci, val in enumerate(row_data):
                self.screen.blit(self.font_small.render(val, True, col_colors[ci]), (cols_x[ci], y))

        # Controles y estado
        status = "▶ Reproduciendo" if self.anim_playing else "⏸ Pausado"
        if self.anim_step >= self.anim_max:
            status = "✓ Completado"
        self.screen.blit(self.font_med.render(status, True, ASTAR_COLOR if "✓" in status else WHITE), (10, self._win_h() - 55))

        step_text = f"Paso: {self.anim_step}/{self.anim_max}  |  Velocidad: {self.anim_speed}ms"
        self.screen.blit(self.font_small.render(step_text, True, GRAY), (10, self._win_h() - 30))

        controls = "SPACE=Play/Pausa  →=Paso  R=Reiniciar  ↑↓=Velocidad  ESC=Menú"
        self.screen.blit(self.font_small.render(controls, True, DARK_GRAY), (280, self._win_h() - 30))

    # ============================================================
    # ACCIONES
    # ============================================================

    def _start_game(self):
        pr, pc = self.grid.player_start
        self.player = Player(pr, pc)

        self.enemies = []
        for er, ec in self.grid.enemy_starts:
            self.enemies.append(Enemy(er, ec, self.algorithm))

        self.timer = SURVIVAL_TIME
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
