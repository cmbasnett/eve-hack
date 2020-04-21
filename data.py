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



class Node(object):

    def __init__(self, row: int, column: int):
        self.row = row
        self.column = column
        self.is_visited = False
        self.is_exposed = False
        self.input = 0
        self.num_neighbors = 0


class BfsNode(object):
    def __init__(self, node, parent, depth):
        self.node = node
        self.parent = parent
        self.depth = depth


class System(object):

    def __init__(self, seed=None):
        self.width = 7
        self.height = 7
        self.nodes = []
        self.selected_node = None
        self.core = None
        self.exposed_count = 0
        self.virus_coherence = 60
        self.virus_strength = 25

        self.create_nodes(seed)


    # TODO: there is a rule that disallows the creation of
    # bottlenecks of N>2 nodes
    # this can probably be a rule that can be generalized
    # as disallowing deletion of nodes if the surrounding
    # nodes neighbors would form this kind of bottleneck

    # TODO: i would also wager there is a multi-waypoint rule
    # that guarantees at least two distinct paths to the
    # core (to stop gauntlets)


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
        print(waypoint)

        candidates = []
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[row][col]
                sp = self.get_path(starting_node, node)
                if sp is None or len(sp) < 8:
                    continue
                candidates.append(self.nodes[row][col])

        core = random.choice(candidates)

        p = self.get_path(starting_node, waypoint)
        q = self.get_path(waypoint, core)
        locked_nodes = set(p + q)
        locked_nodes.add(starting_node)

        population = []
        for row in range(self.height):
            for col in range(self.width):
                node = self.nodes[row][col]
                if node in locked_nodes:
                    continue
                population.append(node)

        # TODO: start deleting nodes at random
        # there should probably be rules for this (can't have two adjacent nodes <= 2 neighbors)
        area = self.width * self.height
        k = area // 4
        nodes_to_delete = random.choices(population, k=k)
        for node in nodes_to_delete:
            self.nodes[node.row][node.column] = None
        self.core = core

        self.prune_disjoint(starting_node)


    def remove_node(self, node):
        for neighbor in self.get_neighbors(node):
            neighbor.num_neighbors -= 1
        self.nodes[node.row][node.column] = None


    def is_valid_index(self, row, col):
        return row >= 0 and row < self.height and col >= 0 and col < self.width


    def can_visit_node(self, node):
        if node is None or node.is_visited:
            return False
        return node.is_exposed

    # TODO: we need a way to tell if a section is disjoint or not
    def visit_node(self, node, force=False):
        if not force and not self.can_visit_node(node):
            return
        if node is None:
            raise RuntimeError('cannot visit a null node!')
        node.is_exposed = True
        for neighbor in self.get_neighbors(node):
            if not neighbor.is_exposed:
                neighbor.is_exposed = True
                neighbor.input = self.exposed_count
                self.exposed_count += 1
        node.is_visited = True
        self.selected_node = node


    def get_starting_node(self):
        min = 100
        starting_nodes = []
        for row in range(self.height):
            for column in range(self.width):
                node = self.nodes[row][column]
                if node is None:
                    continue
                num_neighbors = self.get_num_neighbors(node)
                if num_neighbors < min:
                    min = num_neighbors
                    starting_nodes = [node]
                elif num_neighbors == min:
                    starting_nodes.append(node)
        return starting_nodes[random.randint(0, len(starting_nodes) - 1)]


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


    def get_adjacent_node(self, node, dir):
        if node is None:
            raise RuntimeError()

        row, column = node.row, node.column

        if dir == WEST:
            if column <= 0:
                return None
            return self.nodes[row][column - 1]
        elif dir == EAST:
            if column >= self.width - 1:
                return None
            return self.nodes[row][column + 1]

        if row % 2 == 0:  # even row
            # top-left
            if dir == NORTH_WEST and row > 0 and column > 0:
                return self.nodes[row - 1][column - 1]
            # above-right
            elif dir == NORTH_EAST and row > 0:
                return self.nodes[row - 1][column]
            # below-left
            elif dir == SOUTH_WEST and row < self.height - 1 and column > 0:
                return self.nodes[row + 1][column - 1]
            # below-right
            elif dir == SOUTH_EAST and row < self.height - 1:
                return self.nodes[row + 1][column]
        else:  # odd row
            if dir == NORTH_WEST and row > 0:
                return self.nodes[row - 1][column]
            elif dir == NORTH_EAST and row > 0 and column < self.width - 1:
                return self.nodes[row - 1][column + 1]
            elif dir == SOUTH_WEST and row < self.height - 1:
                return self.nodes[row + 1][column]
            elif dir == SOUTH_EAST and row < self.height - 1 and column < self.width - 1:
                return self.nodes[row + 1][column + 1]

        return None


    def get_neighbors(self, node):
        if node is None:
            return []
        adjacent_nodes = []
        for dir in map(lambda x: 1 << x, range(6)):
            adjacent_node = self.get_adjacent_node(node, dir)
            if adjacent_node is not None:
                adjacent_nodes.append(adjacent_node)
        return adjacent_nodes


    def get_num_neighbors(self, node):
        return sum(1 for x in self.get_neighbors(node))


    def get_node_string(self, row, column):
        node = self.nodes[row][column]
        if node is None:
            return '   '
        elif self.selected_node == node:
            path = self.get_path(node, self.core)
            return '(' + str(len(path)) + ')'
        elif node.is_visited:
            return '( )'
        elif node.is_exposed:
            return f'[{chr(65 + node.input)}]'
        else:
            return ' • '

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


    def get_node_for_input(self, input):
        input = input - 97
        for row in range(self.height):
            for column in range(self.width):
                node = self.nodes[row][column]
                if node is not None and not node.is_visited and node.is_exposed and node.input == input:
                    return node
        return None

    def print(self, screen):
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        y = 0
        for row_index, row in enumerate(self.nodes):
            s = ''
            if row_index % 2 == 1:
                s += '   '

            # draw the row
            for column_index in range(self.width):
                lhs = self.nodes[row_index][column_index]
                rhs = None if column_index >= self.width - 1 else self.nodes[row_index][column_index + 1]
                s += self.get_node_string(row_index, column_index)
                if lhs is not None and rhs is not None:
                    s += '---'
                else:
                    s += '   '

            screen.addstr(y, 0, s)
            y += 1

            if row_index >= self.height - 1:
                continue

            # draw edges
            c = ' '
            d = ' '

            if row_index % 2 == 0:
                # even rows
                for column_index in range(self.width):
                    lhs = self.nodes[row_index][column_index]

                    if lhs is not None:
                        # next one down
                        if self.nodes[row_index + 1][column_index] is not None:
                            c += r' \  '
                            d += r'  \ '
                        else:
                            c += '    '
                            d += '    '
                    else:
                        c += '    '
                        d += '    '

                    if column_index + 1 >= self.width:
                        continue

                    rhs = self.nodes[row_index][column_index + 1]
                    if rhs is not None and column_index >= 0 and \
                            column_index < self.width - 1 and \
                            self.nodes[row_index + 1][column_index] is not None:
                        c += r' /'
                        d += r'/ '
                    else:
                        c += '  '
                        d += '  '
            else:
                # odd rows
                for column_index in range(self.width):
                    lhs = self.nodes[row_index][column_index]

                    if lhs is not None:
                        # next one down
                        if self.nodes[row_index + 1][column_index] is not None:
                            c += r'  / '
                            d += r' /  '
                        else:
                            c += '    '
                            d += '    '
                    else:
                        c += '    '
                        d += '    '

                    if column_index + 1 >= self.width:
                        continue

                    if column_index < self.width - 1 and \
                            lhs is not None and \
                            self.nodes[row_index + 1][column_index + 1] is not None:
                        c += r'\ '
                        d += ' \\'
                    else:
                        c += '  '
                        d += '  '

            screen.addstr(y, 0, c)
            y += 1
            screen.addstr(y, 0, d)
            y += 1

        screen.refresh()


# virus suppressor
# firewall
# restoration
#


def CoreNode(Node):

    def __init__(self, row: int, column: int):
        super.__init__(row, column)
        self.coherence = 70
        self.strength = 10
