# ============================================================
# pathfinding.py - Algoritmos de busqueda en grafos
# ============================================================

import heapq
import time as _time


STRAIGHT_COST = 10

MOVE_DIRECTIONS = [
    (0, 1),    # derecha
    (-1, 0),   # arriba
    (1, 0),    # abajo
    (0, -1),   # izquierda
]


def _timer():
    return _time.perf_counter_ns()


def _elapsed_ms(start_ns):
    return (_time.perf_counter_ns() - start_ns) / 1_000_000


class PathResult:
    def __init__(self):
        self.path = []
        self.explored = []
        self.nodes_explored = 0
        self.time_ms = 0.0
        self.total_cost = 0


def _reconstruct_path(parent, goal):
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
    if (
        isinstance(goal, tuple)
        and len(goal) == 2
        and all(isinstance(value, int) for value in goal)
    ):
        return {goal}

    return set(goal)


def heuristic(a, b):
    dy = abs(a[0] - b[0])
    dx = abs(a[1] - b[1])
    return STRAIGHT_COST * (dx + dy)


def _heuristic_to_goals(node, goals):
    return min(heuristic(node, goal) for goal in goals)


# ============================================================
# DFS
# ============================================================

def _dfs_neighbors(grid, current, size, visited):
    neighbors = []

    for dr, dc in MOVE_DIRECTIONS:
        nr = current[0] + dr
        nc = current[1] + dc
        node = (nr, nc)

        if grid.can_place_entity(nr, nc, size) and node not in visited:
            neighbors.append(node)

    return neighbors


def dfs(grid, start, goal, size=1, explore_all=False):
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)

    if (
        not grid.can_place_entity(*start, size)
        or not any(grid.can_place_entity(*node, size) for node in goals)
    ):
        result.time_ms = _elapsed_ms(t0)
        return result

    stack = [start]
    visited = {start}
    parent = {start: None}
    found_goal = None

    while stack:
        current = stack[-1]

        if current not in result.explored:
            result.explored.append(current)

        if current in goals and found_goal is None:
            found_goal = current

            if not explore_all:
                break

        neighbors = _dfs_neighbors(grid, current, size, visited)

        if neighbors:
            next_node = neighbors[0]
            visited.add(next_node)
            parent[next_node] = current
            stack.append(next_node)
        else:
            stack.pop()

    if found_goal is not None:
        _finish(result, parent, found_goal)

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)

    return result


# ============================================================
# Dijkstra global como antes
# ============================================================

def dijkstra(grid, start, goal, size=1):
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)

    if (
        not grid.can_place_entity(*start, size)
        or not any(grid.can_place_entity(*node, size) for node in goals)
    ):
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
# A*
# ============================================================

def astar(grid, start, goal, size=1):
    result = PathResult()
    t0 = _timer()

    goals = _as_goals(goal)

    if (
        not grid.can_place_entity(*start, size)
        or not any(grid.can_place_entity(*node, size) for node in goals)
    ):
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

                heapq.heappush(
                    heap,
                    (
                        f_score,
                        h_score,
                        tentative_g,
                        tie_breaker,
                        neighbor
                    )
                )

                tie_breaker += 1

    if found:
        _finish(result, parent, goal, g_score[goal])

    result.time_ms = _elapsed_ms(t0)
    result.nodes_explored = len(result.explored)

    return result


# ============================================================
# Exploradores paso a paso
# ============================================================

class DFSExplorer:
    def __init__(self, grid, start):
        self.grid = grid
        self.start = start
        self.stack = [start]
        self.visited = {start}
        self.parent = {start: None}
        self.explored = [start]
        self.finished = False

    def step(self):
        if not self.stack:
            self.finished = True
            return None

        current = self.stack[-1]
        neighbors = _dfs_neighbors(self.grid, current, 1, self.visited)

        if neighbors:
            next_node = neighbors[0]
            self.visited.add(next_node)
            self.parent[next_node] = current
            self.stack.append(next_node)

            if next_node not in self.explored:
                self.explored.append(next_node)

            return next_node

        self.stack.pop()

        if not self.stack:
            self.finished = True
            return None

        return self.stack[-1]

    def reset(self, start):
        self.start = start
        self.stack = [start]
        self.visited = {start}
        self.parent = {start: None}
        self.explored = [start]
        self.finished = False


class DijkstraExplorer:
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

                    heapq.heappush(
                        self.heap,
                        (
                            new_cost,
                            self.tie_breaker,
                            neighbor
                        )
                    )

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