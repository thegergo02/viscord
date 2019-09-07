import curses
import sys
import queue

from ui.ui_utils import UIUtils
from ui.ui_windows import UIWindows
from utils.command_interpreter import CommandInterpreter
from threading import Thread

class UIMain:
    def __init__(self, loop_queue, ui_queue):
        self.loop_queue, self.ui_queue = loop_queue, ui_queue
        self.commands = {
                "q": ["system", "exit"],
                "send": ["discord_api", "send_message"],
                "guilds": ["discord_api", "get_all_guilds"],
                "guild": ["discord_api", "switch_to_guild"],
                "channels": ["discord_api", "get_all_channels"],
                "channel": ["discord_api", "switch_to_channel"],}

    def setup_ui(self, stdscr):
        """This is called by the curses wrapper, it configures the main window, makes the bars and starts the UI loop."""
        UIUtils.configure_main_window(stdscr)
        self.stdscr = stdscr
        self.com_interpreter = CommandInterpreter()
        self.top_bar = UIWindows.TopBar()
        self.bottom_bar = UIWindows.BottomBar()
        self.chat_body = UIWindows.ChatBody()
        self.ui_loop()

    def handle_queue_tasks(self):
        try:
            new_task = self.ui_queue.get()
            if new_task[0]:
                obj = getattr(self, new_task[0])
            else:
                obj = self
            func = getattr(obj, new_task[1])
            try:
                func(*new_task[2])
            except IndexError:
                func()
        except queue.Empty:
            return

    def handle_command(self, com):
        if not com[0] in self.commands.keys():
            self.bottom_bar.change_text("This command does not exists!")
            return
        task_args = self.commands[com[0]]
        try:
            task_args = (*task_args, com[1])
        except IndexError:
            pass
        finally:
            self.loop_queue.put(tuple(task_args))

    def handle_key(self, key):
        if key == 27: #ESC
            self.bottom_bar.is_user_input = False
            self.bottom_bar.is_pagination_active = False
            self.bottom_bar.current_command = ""
        elif key == 10: #ENTER
            if self.bottom_bar.is_user_input and len(self.bottom_bar.current_command) > 0:
                com = self.com_interpreter.interpret(self.bottom_bar.current_command)
                self.handle_command(com)
                self.ui_queue.put(("bottom_bar", "clear_window"))
                self.bottom_bar.current_command = ""
                self.bottom_bar.is_user_input = False
            elif self.bottom_bar.is_pagination_active:
                self.ui_queue.put(("bottom_bar", "show_next_page"))
            else: 
                self.bottom_bar.is_user_input = False
        elif key == 127: #BACKSPACE
            if self.bottom_bar.delete_last_char():
                self.bottom_bar.current_command = self.bottom_bar.current_command[0:-1]
        elif key < 255:
            if self.bottom_bar.is_user_input:
                c = chr(key)
                if self.bottom_bar.add_user_char(c):
                    self.bottom_bar.current_command += c
            elif key == 58: #":"
                self.bottom_bar.clear_window()
                self.bottom_bar.is_user_input = True
                self.bottom_bar.add_user_char(":")
                self.bottom_bar.current_command += ":"

    def handle_user_input(self):
        while True:
            c = self.bottom_bar.get_input()
            self.ui_queue.put((None, "handle_key", (c,)))

    def ui_loop(self):
        input_task = Thread(target=self.handle_user_input, name="input_thread")
        input_task.start()
        while True:
            self.handle_queue_tasks()
