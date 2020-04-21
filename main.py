import time
import curses
from data import System

board = System()

screen = curses.initscr()
screen.clear()

def main(screen):
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.resize_term(128, 128)
    curses.start_color()
    screen.keypad(True)
    while True:
        board.print(screen)
        key = screen.getch()
        print(key)
        # CURSES: capture
        node = board.get_node_for_input(key)
        if node is None:
            continue
        board.visit_node(node)

curses.wrapper(main)
