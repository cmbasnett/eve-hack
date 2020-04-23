import curses
from data import System
from render import SystemRenderer


screen = curses.initscr()
screen.clear()


def get_node_at_mouse(board: System, my, mx):
    if my % 3 != 0:
        return None
    row = my // 3
    if row % 2 == 0:
        col = mx // 3
        if col % 2 == 0:
            col = col // 2
            return board.node_at(row, col)
    else:
        mx -= 3
        col = mx // 3
        if col % 2 == 0:
            col = col // 2
            return board.node_at(row, col)
    return None


def main(screen):
    board = System()
    renderer = SystemRenderer()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.resize_term(128, 128)
    curses.start_color()
    screen.keypad(True)
    curses.mousemask(True)

    while True:
        renderer.render(board, screen)
        ch = screen.getch()
        if ch == curses.KEY_MOUSE:
            _, mx, my, _, _ = curses.getmouse()
            node = get_node_at_mouse(board, my, mx)
            if board.can_visit_node(node):
                board.visit_node(node)
        if ch == curses.KEY_ENTER:
            board = System()


curses.wrapper(main)
