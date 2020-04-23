import random
import curses
from collections import deque


WEST = 1
NORTH_WEST = 2
NORTH_EAST = 4
EAST = 8
SOUTH_EAST = 16
SOUTH_WEST = 32
ALL = (WEST | NORTH_WEST | NORTH_EAST | EAST | SOUTH_EAST | SOUTH_WEST)


# TODO: there is a rule that disallows the creation of
# bottlenecks of N>2 nodes
# this can probably be a rule that can be generalized
# as disallowing deletion of nodes if the surrounding
# nodes neighbors would form this kind of bottleneck

# TODO: i would also wager there is a multi-waypoint rule
# that guarantees at least two distinct paths to the
# core (to stop gauntlets)


class Node(object):

    def __init__(self, row: int, column: int):
        self.row = row
        self.column = column
        self.is_visited = False
        self.is_exposed = False
        self.block_count = 0
        self.input = 0
        self.num_neighbors = 0
        self.token = None

    @property
    def is_blocked(self):
        return self.block_count > 0

    def on_exposed(self):
        pass

    def on_attacked(self):
        pass


class BfsNode(object):
    def __init__(self, node, parent, depth):
        self.node = node
        self.parent = parent
        self.depth = depth


class System(object):

    def __init__(self, seed=None):
        self.width = 8
        self.height = 8
        self.nodes = []
        self.selected_node = None
        self.core_node = None
        self.exposed_count = 0
        self.virus = Virus(self)

        self.create_nodes(seed)

    def bfs_iterator(self, node):
        if node is None:
            raise ValueError
        queue = deque()
        queue.append(BfsNode(node, None, 0))
        visited = {node}
        while len(queue) > 0:
            cursor = queue.pop()
            yield cursor
            for neighbor in self.get_neighbors(cursor.node):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.insert(0, BfsNode(neighbor, cursor, cursor.depth + 1))

    def prune_disjoint(self, node):
        nodes = set([x.node for x in self.bfs_iterator(node)])
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[row][col]
                if node not in nodes:
                    self.nodes[row][col] = None

    def create_nodes(self, seed):
        # Initialize the random number generator with a seed, if provided
        if seed is not None:
            random.seed(seed)

        # Iterate over all the node spots and create a new node.
        for row_index in range(self.height):
            row = [None] * self.width
            self.nodes.append(row)
            for column_index in range(self.width):
                self.nodes[row_index][column_index] = Node(row_index, column_index)

        # TODO: randomly select a bunch of corner bits and turn them off?

        starting_node = self.get_starting_node()
        self.visit_node(starting_node, force=True)

        node_at_jumps = self.get_nodes_at_jumps(starting_node, 5)
        waypoint = random.choice(node_at_jumps)

        candidates = []
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[row][col]
                sp = self.get_path(starting_node, node)
                if sp is None or len(sp) < 8:
                    continue
                candidates.append(self.nodes[row][col])

        # Place down the core token
        self.core_node = random.choice(candidates)
        self.core_node.token = Core(self, self.core_node)
        self.nodes[self.core_node.row][self.core_node.column] = self.core_node

        # Lock down a path to the core
        p = self.get_path(starting_node, waypoint)
        q = self.get_path(waypoint, self.core_node)
        locked_nodes = set(p + q)
        locked_nodes.add(starting_node)

        population = []
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[row][col]
                if node in locked_nodes:
                    continue
                population.append(node)

        # Start deleting nodes at random from the remaining popoulation
        # there should probably be rules for this (can't have two adjacent nodes <= 2 neighbors)
        area = self.width * self.height
        k = area // 4
        nodes_to_delete = random.choices(population, k=k)
        for node in nodes_to_delete:
            self.nodes[node.row][node.column] = None

        # Prune disjointed trees
        self.prune_disjoint(starting_node)

        # Candidate nodes for firewalls
        population = []
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[row][col]
                if node is None:
                    continue
                if self.get_num_neighbors(node) < 6 or self.get_path(node, self.core_node) == 1:
                    population.append(node)
        firewall_nodes = random.choices(population, k=6)
        for node in firewall_nodes:
            node.token = Firewall(self, node)

    def remove_node(self, node):
        for neighbor in self.get_neighbors(node):
            neighbor.num_neighbors -= 1
        self.nodes[node.row][node.column] = None

    def is_valid_index(self, row, col):
        return row >= 0 and row < self.height and col >= 0 and col < self.width

    def can_visit_node(self, node):
        # is_visited -> has been visited once
        if node is None:
            return False
        if (node.is_visited and node.token is None) or node.is_blocked:
            return False
        return node.is_exposed

    def visit_node(self, node, force=False):
        if not force and not self.can_visit_node(node):
            return

        if node is None:
            raise RuntimeError('cannot visit a null node!')

        if not node.is_visited:
            # Node has not been visited before
            node.is_visited = True
            # Expose surrounding nodes
            node.is_exposed = True
            for neighbor in self.get_neighbors(node):
                if not neighbor.is_exposed:
                    neighbor.is_exposed = True
            # If a token exists, expose it
            if node.token is not None:
                node.token.on_exposed()
        else:
            if node.token is not None:
                node.token.on_attacked(self.virus)

        self.selected_node = node

    def get_starting_node(self):
        m = 100
        starting_nodes = []
        for row in range(self.height):
            for column in range(self.width):
                node = self.nodes[row][column]
                if node is None:
                    continue
                num_neighbors = self.get_num_neighbors(node)
                if num_neighbors < m:
                    m = num_neighbors
                    starting_nodes = [node]
                elif num_neighbors == m:
                    starting_nodes.append(node)
        return random.choice(starting_nodes)

    def get_nodes_at_jumps(self, node, jumps):
        # bfs, keep track of
        queue = deque()
        queue.append(BfsNode(node, None, 0))
        nodes = []
        visited = {node}
        while len(queue) > 0:
            cursor = queue.pop()
            neighbors = self.get_neighbors(cursor.node)
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                if cursor.depth >= jumps:
                    nodes.append(neighbor)
                    break
                new = BfsNode(neighbor, cursor, cursor.depth + 1)
                queue.insert(0, new)
        return nodes

    def get_neighbor(self, node, direction):
        if node is None:
            raise RuntimeError()

        row, column = node.row, node.column

        if direction == WEST:
            if column <= 0:
                return None
            return self.nodes[row][column - 1]
        elif direction == EAST:
            if column >= self.width - 1:
                return None
            return self.nodes[row][column + 1]

        if row % 2 == 0:  # even row
            # top-left
            if direction == NORTH_WEST and row > 0 and column > 0:
                return self.nodes[row - 1][column - 1]
            # above-right
            elif direction == NORTH_EAST and row > 0:
                return self.nodes[row - 1][column]
            # below-left
            elif direction == SOUTH_WEST and row < self.height - 1 and column > 0:
                return self.nodes[row + 1][column - 1]
            # below-right
            elif direction == SOUTH_EAST and row < self.height - 1:
                return self.nodes[row + 1][column]
        else:  # odd row
            if direction == NORTH_WEST and row > 0:
                return self.nodes[row - 1][column]
            elif direction == NORTH_EAST and row > 0 and column < self.width - 1:
                return self.nodes[row - 1][column + 1]
            elif direction == SOUTH_WEST and row < self.height - 1:
                return self.nodes[row + 1][column]
            elif direction == SOUTH_EAST and row < self.height - 1 and column < self.width - 1:
                return self.nodes[row + 1][column + 1]

        return None

    def get_neighbors(self, node):
        if node is None:
            return []
        neighbors = []
        for direction in map(lambda x: 1 << x, range(6)):
            neighbor = self.get_neighbor(node, direction)
            if neighbor is not None:
                neighbors.append(neighbor)
        return neighbors

    def get_num_neighbors(self, node):
        return sum(1 for _ in self.get_neighbors(node))

    # breadth-first search
    def get_path(self, start: Node, destination: Node):
        if start == destination:
            return []
        queue = deque()
        queue.append(BfsNode(start, None, 0))
        path = []
        visited = set()  # set of visited nodes
        while len(queue) > 0:
            cursor = queue.pop()
            visited.add(cursor.node)
            if cursor.node == destination:
                # traverse up parent hierarchy, reverse, and return
                while cursor.parent is not None:
                    path.insert(0, cursor.node)
                    cursor = cursor.parent
                return path
            neighbors = self.get_neighbors(cursor.node)
            for neighbor in neighbors:
                if neighbor not in visited:
                    child = BfsNode(neighbor, cursor, cursor.depth)
                    queue.insert(0, child)
                    visited.add(neighbor)
        return None

    def node_at(self, row, col):
        return self.nodes[row][col]

    def get_node_for_input(self, char):
        char = char - 97
        for row in range(self.height):
            for column in range(self.width):
                node = self.nodes[row][column]
                if node is not None and not node.is_visited and node.is_exposed and node.input == char:
                    return node
        return None

# TODO: virus is kind of like a node!
# has coherence, has health? component?? kind of overkill

# TODO nodes can have a token on them! makes it a bit easier and allows clean abstraction
# to allow the virus itself to be a token


class Token(object):

    def __init__(self, system, node=None):
        self.node = node
        self.system = system
        self.coherence = 0
        self.strength = 0

    # TODO: let the system logic handle this??
    def on_attacked(self, attacker):
        self.take_damage(attacker.strength)
        if not self.is_dead:
            # If the token survives the attack, hit the attacker back!
            attacker.take_damage(self.strength)

    def take_damage(self, coherence):
        self.coherence = max(0, self.coherence - coherence)
        if self.is_dead:
            self.on_destroyed()

    @property
    def is_dead(self):
        return self.coherence <= 0

    def on_exposed(self):
        pass

    def on_destroyed(self):
        if self.node is not None:
            self.node.token = None


class Virus(Token):

    def __init__(self, system, node=None):
        super().__init__(system, node)
        self.coherence = 80
        self.strength = 20

    def on_destroyed(self):
        # if it's
        pass


class Core(Token):

    def __init__(self, system, node=None):
        super().__init__(system, node)
        self.coherence = 70
        self.strength = 10

    def on_destroyed(self):
        pass


class Firewall(Token):

    def __init__(self, system, node=None):
        super().__init__(system, node)
        self.coherence = 80
        self.strength = 10

    @property
    def can_be_attacked(self):
        return True

    def on_exposed(self):
        super().on_exposed()
        for neighbor in self.system.get_neighbors(self.node):
            neighbor.block_count += 1

    def on_destroyed(self):
        super().on_destroyed()
        for neighbor in self.system.get_neighbors(self.node):
            neighbor.block_count -= 1
