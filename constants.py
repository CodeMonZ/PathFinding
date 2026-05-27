# ============================================================
# constants.py - Configuracion global del juego
# ============================================================

# --- Tamano de la cuadricula ---
DEFAULT_COLS = 20
DEFAULT_ROWS = 15
CELL_SIZE = 40
PLAYER_SIZE = 2

# --- Ventana ---
HUD_HEIGHT = 80

# --- Colores (R, G, B) ---
BLACK = (10, 10, 26)
DARK_BLUE = (22, 22, 58)
GRID_LINE = (40, 40, 80)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
DARK_GRAY = (80, 80, 80)
OBSTACLE_COLOR = (70, 70, 100)

PLAYER_COLOR = (255, 215, 0)      # Amarillo
DFS_COLOR = (255, 71, 87)         # Rojo
DIJKSTRA_COLOR = (55, 66, 250)    # Azul
ASTAR_COLOR = (46, 213, 115)      # Verde

# --- Velocidades (milisegundos entre movimientos) ---
FPS = 60
PLAYER_MOVE_DELAY = 120
ENTITY_LERP_SPEED = 14

ENEMY_SPEEDS = {
    "dfs": 200,
    "dijkstra": 180,
    "astar": 150,
}

# --- Recalculo del camino para A* ---
ASTAR_RECALC_STEPS = 2

# --- Tiempo de supervivencia (segundos) ---
SURVIVAL_TIME = 60

# --- Tipos de celda ---
EMPTY = 0
WALL = 1

# --- Estados del juego ---
STATE_MENU = "menu"
STATE_EDITOR = "editor"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_WIN = "win"
STATE_ANALYSIS = "analysis"
