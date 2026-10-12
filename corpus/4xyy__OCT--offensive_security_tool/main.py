import curses
import os
from modules.exploits.mac_file_exfiltration import MacOSFileExfiltrationExploit

def print_menu(stdscr, selected_row_idx):
    stdscr.clear()

    # Setting up color pairs
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)   # Highlight selected menu
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Regular text
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Header text
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # ASCII art color

    # Extended ASCII art header
    art = [
        "               ~~~~~~~~                        ",
        "          ~~~~~~~~~~~~~~~~                      ",
        "      ~~~~~~~~~~~~~~~~~~~~~~~~                  ",
        "    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~               ",
        "  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~              ",
        " ~~~~~~~~~~~~~~~~~~~~~~~  ~~~~~~~~~~            ",
        " ~~~~~~~~~~~~~~~~~~~~~     ~~~~~~~~~~~          ",
        " ~~~~~~~~~~~~~~                ~~~~~~~~~        ",
        " ~~~~~~~~~~~~                   ~~~~~~~~        ",
        "  ~~~~~~~~~                       ~~~~~~~       ",
        "  ~~~~~~~~                          ~~~~~~~     ",
        "   ~~~~~~                             ~~~~~~    ",
        "   ~~~~~                                ~~~~~   ",
        "    ~~~~                                 ~~~~~  ",
        "     ~~~                                   ~~~~ ",
        "      ~~                                   ~~~~ ",
        "        ~                                   ~~  ",
        "         ~                                  ~   "
    ]

    for i, line in enumerate(art):
        stdscr.addstr(i + 1, 5, line, curses.color_pair(4))

    # Tool header and metadata
    stdscr.addstr(20, 10, "[----------------------------]", curses.color_pair(3))
    stdscr.addstr(21, 10, " The Offensive Security Toolkit ", curses.color_pair(3))
    stdscr.addstr(22, 10, "[----------------------------]", curses.color_pair(3))

    stdscr.addstr(24, 5, "Created by: Aymen A", curses.color_pair(2))
    stdscr.addstr(25, 5, "Version: 1.0.0", curses.color_pair(2))
    stdscr.addstr(26, 5, "Codename: 'StealthWave'", curses.color_pair(2))

    stdscr.addstr(28, 5, "Select an exploit from the menu:", curses.color_pair(2))

    # Menu options
    menu = [
        "1) MacOS File Exfiltration",
        "2) MacOS Reverse Shell",
        "3) Windows Privilege Escalation",
        "4) Windows Reverse Shell",
        "5) Windows File Exfiltration",
        "99) Exit"
    ]

    for idx, row in enumerate(menu):
        x = 10
        y = 30 + idx
        if idx == selected_row_idx:
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(y, x, row)
            stdscr.attroff(curses.color_pair(1))
        else:
            stdscr.addstr(y, x, row)

    stdscr.refresh()

def run_tool(stdscr, selected_row_idx):
    stdscr.clear()
    stdscr.refresh()
    if selected_row_idx == 0:
        stdscr.addstr(5, 5, "Running MacOS File Exfiltration...", curses.color_pair(2))
        stdscr.addstr(7, 5, "Enter the path to the file to exfiltrate:", curses.color_pair(2))
        stdscr.refresh()
        curses.echo()  # Enable user input
        file_path = stdscr.getstr(9, 5, 60).decode('utf-8')
        stdscr.addstr(11, 5, f"Exfiltrating {file_path}...", curses.color_pair(2))
        stdscr.refresh()

        # Run the MacOS file exfiltration exploit (example)
        try:
            exploit = MacOSFileExfiltrationExploit(file_path)
            exploit.exfiltrate_file()
            stdscr.addstr(13, 5, "File exfiltration completed.", curses.color_pair(2))
        except Exception as e:
            stdscr.addstr(13, 5, f"Error during exfiltration: {str(e)}", curses.color_pair(2))

    elif selected_row_idx == 1:
        stdscr.addstr(5, 5, "Running MacOS Reverse Shell...", curses.color_pair(2))
        stdscr.refresh()
    elif selected_row_idx == 2:
        stdscr.addstr(5, 5, "Running Windows Privilege Escalation...", curses.color_pair(2))
        stdscr.refresh()
    elif selected_row_idx == 3:
        stdscr.addstr(5, 5, "Running Windows Reverse Shell...", curses.color_pair(2))
        stdscr.refresh()
    elif selected_row_idx == 4:
        stdscr.addstr(5, 5, "Running Windows File Exfiltration...", curses.color_pair(2))
        stdscr.refresh()
    elif selected_row_idx == 5:
        stdscr.addstr(5, 5, "Exiting...", curses.color_pair(2))
        stdscr.refresh()
        exit()

    stdscr.addstr(15, 5, "Press any key to return to the main menu.", curses.color_pair(2))
    stdscr.refresh()
    stdscr.getch()

def main(stdscr):
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)

    current_row = 0
    print_menu(stdscr, current_row)

    while True:
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < 5:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            run_tool(stdscr, current_row)
            stdscr.clear()
            print_menu(stdscr, current_row)

curses.wrapper(main)
