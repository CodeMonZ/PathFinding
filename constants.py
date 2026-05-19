# ============================================================
# constants.py — Configuración global del juego
# ============================================================

# --- Tamaño de la cuadrícula (por defecto) ---
DEFAULT_COLS = 20
DEFAULT_ROWS = 15
CELL_SIZE = 40
PLAYER_SIZE = 2

# --- Ventana ---
HUD_HEIGHT = 112

# --- Colores (R, G, B) ---
BLACK      = (10, 10, 26)
DARK_BLUE  = (22, 22, 58)
GRID_LINE  = (40, 40, 80)
WHITE      = (255, 255, 255)
GRAY       = (150, 150, 150)
DARK_GRAY  = (80, 80, 80)
OBSTACLE_COLOR = (70, 70, 100)

PLAYER_COLOR   = (255, 215, 0)
DFS_COLOR      = (255, 71, 87)
DIJKSTRA_COLOR = (55, 66, 250)
ASTAR_COLOR    = (46, 213, 115)

# --- Velocidades (milisegundos entre movimientos) ---
FPS = 60
PLAYER_MOVE_DELAY = 120
ENTITY_LERP_SPEED = 14

ENEMY_SPEEDS = {
    "dfs":      200,
    "dijkstra": 180,
    "astar":    150,
}

# --- Recalculación del camino ---
# DFS = 9999 → sigue TODO el camino antes de recalcular
#   (esto evita que vaya y vuelva en loop)
# Dijkstra/A* = recalculan seguido para adaptarse al jugador
RECALC_STEPS = {
    "dfs":      9999,
    "dijkstra": 3,
    "astar":    2,
}

# --- Tiempo de supervivencia (segundos) ---
SURVIVAL_TIME = 60

# --- Tipos de celda ---
EMPTY = 0
WALL = 1

# --- Estados del juego ---
STATE_MENU     = "menu"
STATE_EDITOR   = "editor"
STATE_PLAYING  = "playing"
STATE_GAME_OVER = "game_over"
STATE_WIN      = "win"
STATE_ANALYSIS = "analysis"

# --- Tamaños de mapa ---
MAP_SIZES = {
    "small":  (15, 10),
    "medium": (20, 15),
    "large":  (30, 20),
}
