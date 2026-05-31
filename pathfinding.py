# ============================================================
# pathfinding.py - Algoritmos de busqueda en grafos
# ============================================================
#
# Reglas implementadas:
# - explored son nodos visitados por la busqueda.
# - path es SOLO el camino reconstruido con parent al llegar a la meta.
# - Los movimientos son solo 4 direcciones.
# - Cada movimiento cuesta 10.
# - A* usa heuristica Manhattan.
# ============================================================

import heapq
import time as _time


STRAIGHT_COST = 10


def _timer():
    return _time.perf_counter_ns()


def _elapsed_ms(start_ns):
    return (_time.perf_counter_ns() - start_ns) / 1_000_000


class PathResult:
    """Resultado estandarizado de cualquier algoritmo."""

    def __init__(self):
        self.path = []
        self.explored = []
        self.nodes_explored = 0
        self.time_ms = 0.0
        self.total_cost = 0


def _reconstruct_path(parent, goal):
    """Reconstruye el camino desde goal hasta inicio usando parent."""
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def _move_cost(a, b):
    return STRAIGHT_COST


def _path_cost(path):
    return sum(_move_cost(a, b) for a, b in zip(path, path[1:]))


def _finish(result, parent, goal, cost=None):
    result.path = _reconstruct_path(parent, goal)
    result.total_cost = _path_cost(result.path) if cost is None else cost


def _as_goals(goal):
    if isinstance(goal, tuple) and len(goal) == 2 and all(isinstance(value, int) for value in goal):
        return {goal}
    return set(goal)


def _tree_path_between(parent, start, goal):
    """Camino entre dos nodos ya conocidos dentro del arbol de busqueda."""
    if start not in parent or goal not in parent:
        return []

    start_chain = []
    current = start
    while current is not None:
        start_chain.append(current)
        current = parent[current]

    goal_chain = []
    current = goal
    while current is not None:
        goal_chain.append(current)
        current = parent[current]

    start_index = {node: index for index, node in enumerate(start_chain)}
    lca = None
    goal_lca_index = 0
    for index, node in enumerate(goal_chain):
        if node in start_index:
            lca = node
            goal_lca_index = index
            break

    if lca is None:
        return []

    up_to_lca = start_chain[:start_index[lca] + 1]
    down_to_goal = list(reversed(goal_chain[:goal_lca_index]))
    return up_to_lca + down_to_goal


def _append_trace_step(result, parent, previous, current):
    """Agrega current a explored sin saltos visuales, retrocediendo por el arbol si hace falta."""
    if previous is None:
        result.explored.append(current)
        return current

    if abs(previous[0] - current[0]) + abs(previous[1] - current[1]) == 1:
        result.explored.append(current)
        return current

    bridge = _tree_path_between(parent, previous, current)
    if bridge:
        result.explored.extend(bridge[1:])
    else:
        result.explored.append(current)
    return current


def heuristic(a, b):
    """Heuristica Manhattan para movimiento en 4 direcciones."""
    dy = abs(a[0] - b[0])
    dx = abs(a[1] - b[1])
    return STRAIGHT_COST * (dx + dy)


def _heuristic_to_goals(node, goals):
    return min(heuristic(node, goal) for goal in goals)


def _dfs_neighbors(grid, start, current, size, goals=None):
    neighbors = grid.get_neighbors(*current, size)
    if not goals:
        return neighbors

    target_col = min(goals, key=lambda node: abs(node[1] - start[1]))[1]
    horizontal_step = -1 if target_col < start[1] else 1
    signed_col_offset = (current[1] - start[1]) * horizontal_step

    if signed_col_offset < 0:
        target_row = min(goals, key=lambda node: abs(node[0] - current[0]))[0]
        vertical_step = -1 if target_row < current[0] else 1
    else:
        vertical_step = -1 if signed_col_offset % 2 == 0 else 1

    preferred = [
        (vertical_step, 0),
        (0, horizontal_step),
        (-vertical_step, 0),
        (0, -horizontal_step),
    ]
    priority = {direction: index for index, direction in enumerate(preferred)}

    def rank(node):
        direction = (node[0] - current[0], node[1] - current[1])
        return priority.get(direction, len(preferred))

    return sorted(neighbors, key=rank)


# ============================================================
# NIVEL 1: DFS (Depth-First Search)
# ============================================================

def dfs(grid, start, goal, size=1, explore_all=False):
    """
    DFS real:
    - usa stack
    - marca visitado al meter en la pila
    - guarda parent
    - reconstruye el camino final solo al encontrar la meta
    - si explore_all=True, sigue explorando todo lo alcanzable antes de mostrar el camino
    """
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)
    if not grid.can_place_entity(*start, size) or not any(grid.can_place_entity(*node, size) for node in goals):
        result.time_ms = _elapsed_ms(t0)
        return result

    stack = [start]
    visited = {start}
    parent = {start: None}
    found_goal = None
    previous_trace = None

    while stack:
        current = stack.pop()
        previous_trace = _append_trace_step(result, parent, previous_trace, current)

        if current in goals and found_goal is None:
            found_goal = current
            if not explore_all:
                break

        # Stack = LIFO, por eso se empuja en reversa.
        for neighbor in reversed(_dfs_neighbors(grid, start, current, size, goals)):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    if found_goal is not None:
        _finish(result, parent, found_goal)

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# NIVEL 2: Dijkstra
# ============================================================

def dijkstra(grid, start, goal, size=1):
    """Dijkstra con min-heap, distancias y parent map."""
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)
    if not grid.can_place_entity(*start, size) or not any(grid.can_place_entity(*node, size) for node in goals):
        result.time_ms = _elapsed_ms(t0)
        return result

    distances = {start: 0}
    parent = {start: None}
    visited = set()
    heap = [(0, 0, start)]
    tie_breaker = 1
    found = False

    while heap:
        current_distance, _, current = heapq.heappop(heap)

        if current in visited:
            continue
        if current_distance != distances.get(current, float("inf")):
            continue

        visited.add(current)
        result.explored.append(current)

        if current in goals:
            found = True
            goal = current
            break

        for neighbor in grid.get_neighbors(*current, size):
            new_distance = current_distance + _move_cost(current, neighbor)
            if new_distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_distance
                parent[neighbor] = current
                heapq.heappush(heap, (new_distance, tie_breaker, neighbor))
                tie_breaker += 1

    if found:
        _finish(result, parent, goal, distances[goal])

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# NIVEL 3: A* (A-Star)
# ============================================================

def astar(grid, start, goal, size=1):
    """A* con f(n)=g(n)+h(n), heuristica Manhattan y control de duplicados."""
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)
    if not grid.can_place_entity(*start, size) or not any(grid.can_place_entity(*node, size) for node in goals):
        result.time_ms = _elapsed_ms(t0)
        return result

    g_score = {start: 0}
    parent = {start: None}
    visited = set()
    start_h = _heuristic_to_goals(start, goals)
    heap = [(start_h, start_h, 0, 0, start)]
    tie_breaker = 1
    found = False

    while heap:
        current_f, current_h, current_g, _, current = heapq.heappop(heap)

        if current in visited:
            continue
        if current_g != g_score.get(current, float("inf")):
            continue

        visited.add(current)
        result.explored.append(current)

        if current in goals:
            found = True
            goal = current
            break

        for neighbor in grid.get_neighbors(*current, size):
            tentative_g = current_g + _move_cost(current, neighbor)
            if tentative_g < g_score.get(neighbor, float("inf")):
                parent[neighbor] = current
                g_score[neighbor] = tentative_g
                h_score = _heuristic_to_goals(neighbor, goals)
                f_score = tentative_g + h_score
                heapq.heappush(heap, (f_score, h_score, tentative_g, tie_breaker, neighbor))
                tie_breaker += 1

    if found:
        _finish(result, parent, goal, g_score[goal])

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)
    return result


# ============================================================
# EXPLORADORES CIEGOS (paso a paso, sin goal)
# ============================================================

class DFSExplorer:
    """
    Exploracion DFS paso a paso, SIN goal conocido.
    Usa una PILA (stack). El enemigo se mueve al nodo que hace pop.
    """

    def __init__(self, grid, start):
        self.grid = grid
        self.start = start
        self.stack = [start]
        self.visited = {start}
        self.parent = {start: None}
        self.explored = []
        self.finished = False

    def step(self):
        if not self.stack:
            self.finished = True
            return None

        current = self.stack.pop()
        self.explored.append(current)

        for neighbor in reversed(_dfs_neighbors(self.grid, self.start, current, 1)):
            if neighbor not in self.visited:
                self.visited.add(neighbor)
                self.parent[neighbor] = current
                self.stack.append(neighbor)

        return current

    def reset(self, start):
        self.start = start
        self.stack = [start]
        self.visited = {start}
        self.parent = {start: None}
        self.explored = []
        self.finished = False

    def path_between(self, start, goal):
        return _tree_path_between(self.parent, start, goal)


class DijkstraExplorer:
    """
    Exploracion Dijkstra paso a paso, SIN goal conocido.
    Usa min-heap y desempate por orden de insercion.
    """

    def __init__(self, grid, start):
        self.grid = grid
        self.heap = [(0, 0, start)]
        self.distances = {start: 0}
        self.parent = {start: None}
        self.tie_breaker = 1
        self.visited = set()
        self.explored = []
        self.finished = False

    def step(self):
        while self.heap:
            cost, _, current = heapq.heappop(self.heap)

            if current in self.visited:
                continue
            if cost != self.distances.get(current, float("inf")):
                continue

            self.visited.add(current)
            self.explored.append(current)

            for neighbor in self.grid.get_neighbors(*current, 1):
                new_cost = cost + _move_cost(current, neighbor)
                if new_cost < self.distances.get(neighbor, float("inf")):
                    self.distances[neighbor] = new_cost
                    self.parent[neighbor] = current
                    heapq.heappush(self.heap, (new_cost, self.tie_breaker, neighbor))
                    self.tie_breaker += 1

            return current

        self.finished = True
        return None

    def reset(self, start):
        self.heap = [(0, 0, start)]
        self.distances = {start: 0}
        self.parent = {start: None}
        self.tie_breaker = 1
        self.visited = set()
        self.explored = []
        self.finished = False

    def path_between(self, start, goal):
        return _tree_path_between(self.parent, start, goal)
