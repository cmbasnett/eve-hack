import curses
from data import Node, Core, Firewall


class SystemRenderer(object):

    def __init__(self):
        pass

    def get_node_string(self, system, node):
        # 🔧 repair
        #  secondary vector
        # 🛡️ - shield
        # 💔 - kernel rot
        if node is None:
            return '   '
        if node.is_blocked:
            return f' x '
        elif node.is_visited and isinstance(node.token, Core):
            return f'🖥️'
        elif node.is_visited and isinstance(node.token, Firewall):
            return f'🔥 '
        elif system.selected_node == node:
            path = system.get_path(node, system.core.node)
            return '(' + str(min(len(path), 5)) + ')'
        elif node.is_visited:
            return '( )'
        elif node.is_exposed:
            return f'[ ]'
        else:
            return ' • '

    def render(self, system, screen):
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        y = 0

        for row_index, row in enumerate(system.nodes):
            s = ''
            if row_index % 2 == 1:
                s += '   '

            # draw the row
            for column_index in range(system.width):
                lhs = system.nodes[row_index][column_index]
                rhs = None if column_index >= system.width - 1 else system.nodes[row_index][column_index + 1]
                s += self.get_node_string(system, lhs)
                if lhs is not None and rhs is not None:
                    s += '---'
                else:
                    s += '   '

            screen.addstr(y, 0, s)
            y += 1

            if row_index >= system.height - 1:
                continue

            # draw edges
            c = ' '
            d = ' '

            if row_index % 2 == 0:
                # even rows
                for column_index in range(system.width):
                    lhs = system.nodes[row_index][column_index]

                    if lhs is not None:
                        # next one down
                        if system.nodes[row_index + 1][column_index] is not None:
                            c += r' \  '
                            d += r'  \ '
                        else:
                            c += '    '
                            d += '    '
                    else:
                        c += '    '
                        d += '    '

                    if column_index + 1 >= system.width:
                        continue

                    rhs = system.nodes[row_index][column_index + 1]
                    if rhs is not None and 0 <= column_index < system.width - 1 and system.nodes[row_index + 1][column_index] is not None:
                        c += r' /'
                        d += r'/ '
                    else:
                        c += '  '
                        d += '  '
            else:
                # odd rows
                for column_index in range(system.width):
                    lhs = system.nodes[row_index][column_index]

                    if lhs is not None:
                        # next one down
                        if system.nodes[row_index + 1][column_index] is not None:
                            c += r'  / '
                            d += r' /  '
                        else:
                            c += '    '
                            d += '    '
                    else:
                        c += '    '
                        d += '    '

                    if column_index + 1 >= system.width:
                        continue

                    if column_index < system.width - 1 and \
                            lhs is not None and \
                            system.nodes[row_index + 1][column_index + 1] is not None:
                        c += r'\ '
                        d += ' \\'
                    else:
                        c += '  '
                        d += '  '

            screen.addstr(y, 0, c)
            y += 1
            screen.addstr(y, 0, d)
            y += 1

        y += 1

        # TODO: iterate over all the exposed tokens on the board and print them out
        if not system.virus.is_dead:
            screen.addstr(y, 0, f'VIRUS: ({system.virus.coherence}/{system.virus.strength})')
            y += 1

        if system.core.node.is_visited:
            screen.addstr(y, 0, f'CORE ({system.core.coherence}/{system.core.strength})')
            y += 1

        screen.refresh()
