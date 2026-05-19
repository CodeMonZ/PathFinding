# ============================================================
# pathfinding.py — Algoritmos de búsqueda en grafos
# ============================================================
#
# Tres algoritmos, cada uno con comportamiento diferente:
#   DFS      → explora profundo, caminos NO óptimos
#   Dijkstra → camino más corto garantizado
#   A*       → camino óptimo con menos exploración
#
# Todos retornan un PathResult con:
#   - path:     lista de celdas del camino final
#   - explored: lista de celdas visitadas (para visualización)
#
# ============================================================

import heapq
import time as _time


def _timer():
    """Timer de alta precisión (nanosegundos)."""
    return _time.perf_counter_ns()


def _elapsed_ms(start_ns):
    """Milisegundos transcurridos."""
    return (_time.perf_counter_ns() - start_ns) / 1_000_000


class PathResult:
    """Resultado estandarizado de cualquier algoritmo."""

    def __init__(self):
        self.path = []
        self.explored = []
        self.nodes_explored = 0
        self.time_ms = 0.0


def _reconstruct_path(parent, goal):
    """Reconstruye el camino desde goal hasta inicio."""
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


# ============================================================
# NIVEL 1: DFS (Depth-First Search)
# ============================================================
# - Usa PILA (stack) → explora profundo antes de retroceder
# - Encuentra UN camino, pero generalmente NO el más corto
# - El camino suele ser largo y dar vueltas innecesarias
# ============================================================

def dfs(grid, start, goal, size=1):
    """
    Búsqueda en profundidad.
    Encuentra UN camino (no el más corto).
    """
    result = PathResult()
    t0 = _timer()

    stack = [start]
    visited = {start}
    parent = {start: None}

    while stack:
        current = stack.pop()
        result.explored.append(current)

        if current == goal:
            result.path = _reconstruct_path(parent, goal)
            break

        # Vecinos en orden fijo: arriba, abajo, izq, der
        for neighbor in grid.get_neighbors(*current, size):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# NIVEL 2: Dijkstra
# ============================================================
# - Usa COLA DE PRIORIDAD (min-heap)
# - GARANTIZA el camino más corto
# - Explora muchos nodos de forma uniforme
# ============================================================

def dijkstra(grid, start, goal, size=1):
    """
    Algoritmo de Dijkstra.
    Camino más corto garantizado.
    """
    result = PathResult()
    t0 = _timer()

    heap = [(0, start)]
    cost = {start: 0}
    parent = {start: None}
    visited = set()

    while heap:
        current_cost, current = heapq.heappop(heap)

        if current in visited:
            continue

        visited.add(current)
        result.explored.append(current)

        if current == goal:
            result.path = _reconstruct_path(parent, goal)
            break

        for neighbor in grid.get_neighbors(*current, size):
            move_cost = 1.4 if neighbor[0] != current[0] and neighbor[1] != current[1] else 1
            new_cost = current_cost + move_cost

            if neighbor not in cost or new_cost < cost[neighbor]:
                cost[neighbor] = new_cost
                parent[neighbor] = current
                heapq.heappush(heap, (new_cost, neighbor))

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# NIVEL 3: A* (A-Star)
# ============================================================
# - f(n) = g(n) + h(n)  con heurística Manhattan
# - Camino ÓPTIMO con MENOS exploración que Dijkstra
# ============================================================

def heuristic(a, b):
    """Distancia octil entre dos celdas."""
    dr = abs(a[0] - b[0])
    dc = abs(a[1] - b[1])
    return max(dr, dc) + 0.4 * min(dr, dc)


def astar(grid, start, goal, size=1):
    """
    Algoritmo A*.
    Camino óptimo con menor exploración.
    """
    result = PathResult()
    t0 = _timer()

    g_score = {start: 0}
    f_score = heuristic(start, goal)
    heap = [(f_score, start)]
    parent = {start: None}
    visited = set()

    while heap:
        current_f, current = heapq.heappop(heap)

        if current in visited:
            continue

        visited.add(current)
        result.explored.append(current)

        if current == goal:
            result.path = _reconstruct_path(parent, goal)
            break

        for neighbor in grid.get_neighbors(*current, size):
            move_cost = 1.4 if neighbor[0] != current[0] and neighbor[1] != current[1] else 1
            tentative_g = g_score[current] + move_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                parent[neighbor] = current
                heapq.heappush(heap, (f, neighbor))

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result
