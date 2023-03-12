#  _______                _
# |__   __|              (_)
#    | | ___  _ __   ___  _
#    | |/ _ \| '_ \ / _ \| |
#    | | (_) | | | | (_) | |
#    |_|\___/|_| |_|\___/|_|
# ©Justaus3r 2022
# This file is part of "Tonoi",a playable implementation of tower of hanoi.
# Distributed under GPLV3
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
""" Main entrypoint and argument handler """


import sys
import random
import argparse
import datetime
import subprocess
from time import sleep
from .canvas import Canvas
from pprint import PrettyPrinter
from .intrinsics import RodHandler
from typing import List, NoReturn, Tuple, Optional, Union, Callable
from .handlers import ConfigHandler, EventHandler, SourceValidationHandler
from .misc import Misc, ReturnCode, version_validator, gen_player_name, inject_debugger
from .termutils import (
    clear_screen,
    ThreadedEventsAdaptor,
    get_platform,
    ansi_controlcode_supported,
)
from .exceptions import (
    EmptyRodError,
    BadCommandError,
    ProhibitedMove,
    SubArgumentError,
    DisksOverLimitError,
    ConfigParseError,
)


if get_platform() in ("Linux", "Darwin"):
    import readline


@inject_debugger
class Tonoi:

    canvas = Canvas("canvas_handle", drawing_format=None)

    def __init__(self, **kwargs) -> None:
        self.config: ConfigHandler.CONFIG = {}
        self.game_finished: bool = False
        self.game_won: bool = False
        self.allow_illegal_move: bool = False
        self.ye_mama_innocent: bool = False
        self.no_tl_dialog: bool = False
        self.command_history: List[str] = []
        self.time_limit: Optional[int] = kwargs.get("time_limit")
        self.init_time: Optional[datetime.datetime] = None
        if self.time_limit:
            self.init_time = datetime.datetime.now()
        self.do_debugging: bool = kwargs.get("debug")
        with ConfigHandler("player_config") as config_handle:
            if config_handle.validate_config_existence():
                entire_config = config_handle.read_config()
                self.config = entire_config["tonoi_config"]
            else:
                self.config = Misc.default_config
        self.interaction_mode: str = (
            kwargs.get("interaction_mode") or self.config["interface_type"]
        )
        with ConfigHandler("player_data") as players_data_handle:
            seed_value: int
            if players_data_handle.validate_config_existence():
                players_data = players_data_handle.read_config()
                seed_value = players_data["Meta"].get("seed_value")
            else:
                players_data_handle = players_data_handle.io_obj.create_conf()
                seed_value = players_data_handle.create_player_data_file()
                players_data = {}
            new_player_name = gen_player_name(seed_value)
            self.config.update({"player_name": new_player_name})
            default_player_data: Dict[str, Optional[str]] = {
                "best_game_runs": "None",
                "perfect_game_runs": "None",
            }
            if player_name := kwargs.get("player_name"):
                try:
                    player_data = players_data["play_history"][player_name]
                except KeyError:
                    player_data = default_player_data
                finally:
                    default_player_data.update({"player_name": player_name})
            else:
                player_data = default_player_data
                players_data_handle.update_seed_value(seed_value + 1)

        self.config.update(kwargs)
        self.config.update({"player_data": player_data})

    class ScreenData:
        player_name: str
        moves: str
        lines: int
        columns: int
        best_game_run: int
        perfect_game_runs: int
        remaining_lives: int
        actual_disk_count: str
        appearent_max_disk_count_nrod: int
        disk_count_1rod: int
        disk_count_2rod: int
        disk_count_3rod: int

    def draw_interface(self, **kwargs) -> None:
        if not self.is_graphics_mode():
            # probably redraw is being used in textual mode
            print("`redraw` is unavailable in this mode")
            return None
        clear_screen()
        Tonoi.canvas.buffer_cache.counter = 0
        Tonoi.canvas.buffer_cache.clear()
        Tonoi.canvas.partial_reinit()
        # disk_count_first_rod initially being equal to actual_disk_count
        # will change throughout the game.
        actual_disk_count_1rod = Tonoi.ScreenData.disk_count_1rod
        actual_disk_count_2rod = Tonoi.ScreenData.disk_count_2rod
        actual_disk_count_3rod = Tonoi.ScreenData.disk_count_3rod

        draw_top_only: bool = kwargs.get("top_el_only")

        def draw_unit_tower(
            rod_no: int, actual_disk_count_nrod: int, top_el_only: bool = False
        ) -> int:
            assert rod_no in [1, 2, 3], "Rod no must be in range 1..3"

            (
                appearent_disk_count_nrod,
                cloud_line_nrod,
                render_overlimiter_nrod,
            ) = Tonoi.canvas.get_appearent_disk_count(actual_disk_count_nrod)

            rod_count_curr: int = Tonoi.canvas.get_appearent_rod_count(
                Tonoi.ScreenData.appearent_max_disk_count_nrod,
                appearent_disk_count_nrod,
            )
            cloud_col_nrod: int
            disk_rendering_col: int
            cloud_col_nrod = disk_rendering_col = (
                3
                if rod_no == 1
                else (
                    (Tonoi.canvas.coordinates.columns // 3 - 3)
                    if rod_no == 2
                    else ((Tonoi.canvas.coordinates.columns // 3 - 3) * 2)
                )
            )

            if cloud_line_nrod:
                Tonoi.canvas.draw_scenery(
                    cloud_line_nrod, cloud_col_nrod, rod_no=rod_no
                )

            if render_overlimiter_nrod:
                # subtracting the lines occupied by the disks - the lines occupied items at the item
                # will give us the line at which the 'Rod' is rendered.
                overlimiter_render_line: int = (
                    Tonoi.canvas.coordinates.lines - appearent_disk_count_nrod - 4
                )
                Tonoi.canvas.draw_overlimit_indicator(
                    actual_disk_count_nrod - appearent_disk_count_nrod,
                    overlimiter_render_line,
                    cloud_col_nrod,
                )
            Tonoi.canvas.draw_tower(
                Tonoi.canvas.coordinates.lines - 4,
                disk_rendering_col,
                rod_no,
                appearent_disk_count_nrod,
                rod_count_curr,
                top_el_only=top_el_only,
                actual_disk_count=Tonoi.ScreenData.actual_disk_count,
            )

        draw_unit_tower(
            rod_no=1,
            actual_disk_count_nrod=actual_disk_count_1rod,
            top_el_only=draw_top_only,
        )

        draw_unit_tower(
            rod_no=2,
            actual_disk_count_nrod=actual_disk_count_2rod,
            top_el_only=draw_top_only,
        )
        draw_unit_tower(
            rod_no=3,
            actual_disk_count_nrod=actual_disk_count_3rod,
            top_el_only=draw_top_only,
        )
        upper_box_str = Tonoi.canvas.prepare_upper_box_elements_string(
            Player_Name=Tonoi.ScreenData.player_name,
            Best_Runs=Tonoi.ScreenData.best_game_runs,
            Perfect_Runs=Tonoi.ScreenData.perfect_game_runs,
            Current_Moves=Tonoi.ScreenData.moves,
            Remaining_Lives=Tonoi.ScreenData.remaining_lives,
        )

        Tonoi.canvas.draw_box_output(
            upper_box_str,
            box_position="top-full",
            text_color="random",
        )

        Tonoi.canvas.draw_box_output(
            text=None,
            box_position="full-screen",
            text_color="green",
        )
        Tonoi.canvas.draw_box_output(
            ">>",
            box_position="bottom-full",
            text_color="green",
        )
        Tonoi.canvas.transit_position(Tonoi.canvas.coordinates.lines - 2, 7)

    def allow_prohibited_move(self) -> None:
        self.allow_illegal_move = True

    def disallow_prohibited_move(self) -> None:
        self.allow_illegal_move = False

    def mama_no_innocent(self) -> None:
        self.ye_mama_innocent = True

    def no_time_limit_dialog(self) -> None:
        self.no_tl_dialog = True

    def list_commands(self) -> None:
        cmd_txt = r"""
------------------------------------------------
|Commands         |Description                 |
|-----------------|----------------------------| 
|redraw, rd       | redraw the screen          | 
|                 |(won't work in textual mode)| 
|-----------------|----------------------------| 
|quit,exit        |quit the game               | 
|-----------------|----------------------------| 
|move, m          |move a disk from src to dest| 
|<src> <dest>     |both must be +ve integers   | 
|-----------------|----------------------------| 
|register-player  |register player with a name |
|, rg             |                            |
|-----------------|----------------------------|
|help             |show basic help             |
|-----------------|----------------------------|
|replay <p,disks> |replay the game, optional   | 
|                 |disk_no(use 'p' to go with  |
|                 |current disk_no) may be     |
|                 |given for the new game      |
|-----------------|----------------------------|
|show-minima, sm  |display minimum moves req   |
|                 |to solve the puzzle         |
|-----------------|----------------------------|
|seek-top         |show topmost disks of every |
|                 |rod                         |
|-----------------|----------------------------|
|icheat, inocheat |use them respectively to    |
|                 |either enable               |
|                 |`no life deduction` or not  |
|-----------------|----------------------------|
|butmymamainnocent|no yo mama jokes for you    |
|-----------------|----------------------------|
|history          |show command history        |
|-----------------|----------------------------|
|toggle-mode      |toggle interface mode from  |
| <mode>          |graphics to textual and     |
|                 |vice-versa.use 'g', 'tui'   |
|                 |'graphics' for graphics mode| 
|                 |and 'textual', 't' for text |
|                 |mode                        |
|-----------------|----------------------------|
|list-commands, lc|show this command table     |
|-----------------|----------------------------|
|create-config, cc|create config file in HOME  |
|-----------------|----------------------------|
|time-limit, tl   |show time limit,if available|
|-----------------|----------------------------|
|no-tld           |disable time limit dialog   |
------------------------------------------------
"""
        self.show_pager_output(cmd_txt)

    def invoke_action(self, callback: str, action_args: List[str]) -> Optional[int]:
        valid_actions = {
            "redraw": self.draw_interface,
            "rd": self.draw_interface,
            "quit": self.quit,
            "exit": self.quit,
            "move": self.move,
            "m": self.move,
            "register-player": self.register_player,
            "rg": self.register_player,
            "help": self.help,
            "replay": self.replay,
            "seek-top": self.seek_top,
            "show-minima": self.show_minima,
            "sm": self.show_minima,
            "icheat": self.allow_prohibited_move,
            "inocheat": self.disallow_prohibited_move,
            "butmymamainnocent": self.mama_no_innocent,
            "history": self.show_history,
            "toggle-mode": self.toggle_mode,
            "tm": self.toggle_mode,
            "list-commands": self.list_commands,
            "lc": self.list_commands,
            "create-config": ConfigHandler.create_config,
            "cc": ConfigHandler.create_config,
            "time-limit": self.get_time_limit,
            "tl": self.get_time_limit,
            "no-tld": self.no_time_limit_dialog,
            "dbc": self._dump_buffer_cache,
        }
        try:
            game_won: bool = valid_actions[callback](*action_args)
            if game_won:
                return True
        except KeyError:
            raise BadCommandError
        except TypeError:
            raise SubArgumentError(callback)

    def confirmation_prompt(self, msg: str, opt_col_offset: int = 0) -> str:
        line, col = self.canvas.draw_confirmation_box(msg)
        self.canvas.transit_position(line, col - opt_col_offset)
        ans: str = input("\x1b[31m")
        if ans in ["Y", "y"]:
            return True
        else:
            return False

    def replay(self, disk_count: Union[int, str]) -> None:
        if not self.game_finished:
            confirmation: bool = self.confirmation_prompt(
                "Current game has not finished yet!,\n replay will cause all game data to be lost ",
                4,
            )
            if confirmation:
                pass
            else:
                return None
        if disk_count == "p":
            pass
        else:
            try:
                disk_count = int(disk_count)
                Tonoi.ScreenData.actual_disk_count = disk_count
            except ValueError:
                self.canvas.draw_error_screen("`replay expects an integer argument!`")
        self.play(init_only=True)
        self.canvas.disks_info.clear()
        self.game_finished = False
        self.game_won = False
        self.allow_illegal_move = False
        self.internal_game_handle.__init__(Tonoi.ScreenData.actual_disk_count)

    def move(self, src: str, dest: str) -> Optional[None]:
        try:
            src = int(src)
            dest = int(dest)
        except ValueError:
            self.canvas.draw_error_screen("`move` expects integer arguments!")
            return None
        game_won: Optional[bool] = self.internal_game_handle.move_disk(src, dest)
        _, top_element = self.canvas.disks_info[src].popitem()
        dest_top: int
        try:
            dest_top = list(self.canvas.disks_info[dest].keys())[-1] + 1
        except IndexError:
            dest_top = 0
        finally:
            self.canvas.disks_info[dest][dest_top] = top_element
        src_disk_count: int = getattr(Tonoi.ScreenData, "disk_count_{}rod".format(src))
        dest_disk_count: int = getattr(
            Tonoi.ScreenData, "disk_count_{}rod".format(dest)
        )
        setattr(Tonoi.ScreenData, "disk_count_{}rod".format(src), src_disk_count - 1)
        setattr(Tonoi.ScreenData, "disk_count_{}rod".format(dest), dest_disk_count + 1)
        if game_won:
            return True

    def seek_top(self) -> None:
        self.draw_interface(top_el_only=True)
        print("Press Enter to continue!", end="")
        input()

    def repl_mode(self) -> None:
        print(self.internal_game_handle.primary_rod)
        print(self.internal_game_handle.secondary_rod)
        print(self.internal_game_handle.tertiary_rod)
        print(">>", end="")

    def toggle_mode(self, mode: str) -> None:
        self.interaction_mode = mode
        if self.is_graphics_mode():
            self.tsv_instance.signal = 1
        else:
            self.tsv_instance.signal = 2
        clear_screen()

    def is_graphics_mode(self) -> bool:
        return True if self.interaction_mode in ("graphics", "g", "tui") else False

    def invoke_display_method(self, tui_mode: Callable, repl_mode: Callable) -> None:
        if self.is_graphics_mode():
            tui_mode()
        else:
            self.repl_mode()

    def _dump_buffer_cache(self) -> None:
        print("\n\n")
        clear_screen()
        pp = PrettyPrinter(indent=4)
        p_dump = pp.pformat(Tonoi.canvas.buffer_cache)
        self.show_pager_output(p_dump)

    def show_minima(self) -> None:
        minima: int = 2 ** int(Tonoi.ScreenData.actual_disk_count) - 1
        prepared_str: str = "MM: {}".format(minima)
        len_prepared_str: int = len(prepared_str)
        Tonoi.canvas.print_stdout(
            (
                Tonoi.ScreenData.lines - 2,
                Tonoi.ScreenData.columns - len_prepared_str - 5,
            ),
            prepared_str,
            after_position="after-prompt",
        )
        input("Press Enter to Continue")

    def show_history(self) -> None:
        cmd_str: str = "\n".join(self.command_history)
        self.show_pager_output(cmd_str)

    def show_pager_output(self, text: str) -> None:
        # clear_screen doesn't work properly here
        # some residue text from previous draw_interface
        # call still remains, so we also print some new lines and
        # call the pager
        clear_screen()
        print("\n\n")
        try:
            return_code: int = subprocess.run(
                ["more"], input=text.encode(), shell=True
            ).returncode
        except FileNotFoundError:
            # 127 -> command not found returncode?
            return_code = 127
        if return_code != 0:
            self.canvas.draw_warning_screen(
                "No pager program found or\nsubprocess returned a non-zero code. \nfalling back to simple terminal output "
            )
            clear_screen()
            self.canvas.transit_position(0, 0)
            text += "\nPress Enter to Continue!"
            print(text)
            input()

    def show_stacktrace(self) -> None:
        raise NotImplementedError

    def register_player(self, player_name: str) -> None:
        self.ScreenData.player_name = player_name

    def help(self) -> None:
        self.canvas.draw_info_screen(Misc.util_howtoplay)
        input()

    def quit(self) -> Optional[NoReturn]:
        if not self.game_finished:
            confirmation: bool = self.confirmation_prompt(
                "Are you sure you want to\nend the game abruptly?\nNote that all game data will be lost!"
            )
            if confirmation:
                pass
            else:
                return None
        print("\x1b[0m", end="")
        clear_screen()
        self.tsv_instance.signal = 0
        sys.exit(0)

    def get_time_limit(self, value_only: bool = False) -> Optional[datetime.datetime]:
        if self.time_limit:
            time_delta: datetime.datetime = self.time_limit - (
                (datetime.datetime.now() - self.init_time).seconds
            )
            if value_only:
                return time_delta
            time_delta_pretty: str = datetime.timedelta(time_delta)
            self.canvas.print_stdout(
                (self.ScreenData.lines - 2, 7),
                "Remaining Time: {}, \tPress Enter to Continue".format(time_delta),
            )
            input()

    def time_limit_indicator(self, time_remaining: int) -> None:
        if not self.time_limit:
            return None
        if time_remaining in (self.time_limit // 2, self.time_limit // 4):
            self.canvas.draw_info_screen(
                "Remaining time: {}  ".format(
                    datetime.timedelta(seconds=time_remaining)
                )
            )
            sleep(2)
            self.invoke_display_method(self.draw_interface, self.repl_mode)
            self.canvas.transit_position(self.ScreenData.lines - 2, 7)
        elif time_remaining == 0:
            self.canvas.draw_error_screen("Timelimit Exceeded!")
            self.invoke_display_method(self.draw_interface, self.repl_mode)
            self.canvas.transit_position(self.ScreenData.lines - 2, 7)

    def term_width_warning(self) -> None:
        self.canvas.draw_warning_screen(
            "Terminal width change detected!\nPlease revert to orignal terminal width for an optimal gamerun."
        )

    def yo_mama_jokes(self) -> str:
        yo_mama_joke_list: List[str] = [
            "Yo mama's such a cold bitch, \nher tits give soft serve ice cream",
            "Yo mama's so easy that when she heard Santa Claus \nsay Ho Ho Ho she thought she was getting \nit three times",
            "Yo mama sucks so much, a black hole would be embarrased",
            "Yo mama sucks so much dick, \nher lips went double platinum",
            "Yo mama so stupid she put cat-food \ndown her pants to feed her pussy",
            "Yo mama so fat that your dad has to have a 'heavy machinary' \nlicense to have sex",
            "Yo mama so bad at sex, \nthe only kind of head she gives is severed",
            "Yo mama reminds me of \na toilet, fat, white, and smells like shit",
        ]
        return random.choice(yo_mama_joke_list)

    def play(self, init_only=False) -> ReturnCode:
        """Initialize `ScreenData`"""
        Tonoi.ScreenData.player_name = self.config.get("player_name")
        Tonoi.ScreenData.moves = "0"
        try:
            Tonoi.ScreenData.best_game_runs = str(
                self.config["player_data"]["best_game_runs"]
            )
            Tonoi.ScreenData.perfect_game_runs = str(
                self.config["player_data"]["perfect_game_runs"]
            )
            Tonoi.ScreenData.actual_disk_count = (
                Tonoi.ScreenData.actual_disk_count
                if init_only
                else self.config["disk_capacity"]
            )
            Tonoi.canvas.drawing_format = (
                "ascii" if self.config["render_ascii"] else "ansi"
            )
        except KeyError:
            raise ConfigParseError.BadKeyValuePair(
                "Incomplete Configuration Data!. Possibly due to incompatible key-value pair assignment"
            )
        Tonoi.ScreenData.remaining_lives = 3
        # if init_only=True, probably means that a replay was invoke,
        # in which case actual_disk_count has already been set by the procedure
        # otherwise get it from config

        Tonoi.ScreenData.disk_count_1rod = Tonoi.ScreenData.actual_disk_count
        Tonoi.ScreenData.disk_count_2rod = 0
        Tonoi.ScreenData.disk_count_3rod = 0
        Tonoi.canvas.partial_reinit()
        (
            Tonoi.ScreenData.appearent_max_disk_count_nrod,
            *_,
        ) = Tonoi.canvas.get_appearent_disk_count(Tonoi.canvas.disk_horizontal())
        if init_only:
            return None
        Tonoi.ScreenData.lines = Tonoi.canvas.coordinates.lines
        Tonoi.ScreenData.columns = Tonoi.canvas.coordinates.columns
        self.internal_game_handle = RodHandler(Tonoi.ScreenData.actual_disk_count)
        event_handler = EventHandler()
        event_handler.register_event(name="redraw", callback=self.draw_interface)
        event_handler.register_event(
            name="elict_term_width_warning", callback=self.term_width_warning
        )
        event_handler.register_event(
            name="time_limit_indicator", callback=self.time_limit_indicator
        )
        self.tsv_instance = ThreadedEventsAdaptor(
            event_handler, Tonoi.ScreenData, Tonoi.canvas, self
        )
        self.tsv_instance.start()
        while Tonoi.ScreenData.remaining_lives > 0:
            try:
                self.invoke_display_method(self.draw_interface, self.repl_mode)
                raw_input = input(
                    "\x1b[{}m".format(random.choice([0, 31, 32, 33, 34, 36, 97]))
                )
                self.command_history.append(raw_input)
                try:
                    action, *args = raw_input.split()
                    game_won: Optional[bool] = self.invoke_action(action, args)
                    if game_won:
                        self.canvas.draw_win_screen(
                            int(Tonoi.ScreenData.moves) + 1,
                            Tonoi.ScreenData.actual_disk_count,
                        )
                        self.game_finished = True
                        with ConfigHandler("player_data") as ch:
                            minimum_moves_req: int = (
                                2 ** int(Tonoi.ScreenData.actual_disk_count) - 1
                            )
                            Tonoi.ScreenData.best_game_runs = (
                                "0"
                                if Tonoi.ScreenData.best_game_runs == "None"
                                else Tonoi.ScreenData.best_game_runs
                            )
                            Tonoi.ScreenData.perfect_game_runs = (
                                "0"
                                if Tonoi.ScreenData.perfect_game_runs == "None"
                                else Tonoi.ScreenData.perfect_game_runs
                            )
                            best_game_runs: int = int(
                                Tonoi.ScreenData.best_game_runs
                            ) + (
                                1
                                if int(Tonoi.ScreenData.moves) + 1
                                in range(minimum_moves_req + 1, minimum_moves_req + 7)
                                else 0
                            )
                            perfect_game_runs = int(
                                Tonoi.ScreenData.perfect_game_runs
                            ) + (
                                1
                                if int(Tonoi.ScreenData.moves) + 1 == minimum_moves_req
                                else 0
                            )
                            Tonoi.ScreenData.best_game_runs = str(best_game_runs)
                            Tonoi.ScreenData.perfect_game_runs = str(perfect_game_runs)
                            ch.update_player_data(
                                Tonoi.ScreenData.player_name,
                                best_game_runs=best_game_runs,
                                perfect_game_runs=perfect_game_runs,
                            )
                except BadCommandError:
                    self.canvas.draw_error_screen("entrée de données très erronée!")
                except SubArgumentError as e:
                    self.canvas.draw_error_screen(
                        "'{}' expects some arguments!".format(e.callback)
                    )
                    Tonoi.ScreenData.moves = str(int(Tonoi.ScreenData.moves) - 1)
                except ValueError:
                    # prolly empty str input
                    pass
                except ProhibitedMove:
                    if not self.allow_illegal_move:
                        self.canvas.draw_error_screen(
                            "Smaller disk can't be put over a larger disk "
                        )
                        Tonoi.ScreenData.remaining_lives -= 1
                        # will normalize the moves increament
                        Tonoi.ScreenData.moves = str(int(Tonoi.ScreenData.moves) - 1)
                except EmptyRodError:
                    self.canvas.draw_warning_screen(
                        "Can't move disk from an empty rod "
                    )
                    Tonoi.ScreenData.moves = str(int(Tonoi.ScreenData.moves) - 1)
                if raw_input.strip() and action in ("move", "m"):
                    Tonoi.ScreenData.moves = str(int(Tonoi.ScreenData.moves) + 1)
            except AttributeError as e:
                clear_screen()
                print("I am AttributeError with val: {}".format(e))
                input()
            except (KeyboardInterrupt, EOFError):
                if not self.game_finished:
                    confirmation: bool = self.confirmation_prompt(
                        "A game is in progress!.data might be lost ", 5
                    )
                    if confirmation:
                        self.game_finished = True
                        self.quit()
        else:
            self.tsv_instance.signal = 0
            self.game_finished = True
            Tonoi.canvas.draw_death_screen(
                "YOU ARE A FAILURE!"
                + (
                    "\nAND\n{}".format(self.yo_mama_jokes())
                    if not self.ye_mama_innocent
                    else ""
                )
            )
            clear_screen()
            self.quit()


def main(sys_args: List[str], dump_debug: bool = False) -> int:
    argparser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog=Misc.util_name,
        usage=Misc.util_usage,
        description=Misc.util_description,
        epilog=Misc.util_epilog,
    )

    argparser.add_argument(
        "-pn", "--player-name", type=str, help="use custom player name"
    )
    argparser.add_argument(
        "-dc",
        "--disk-capacity",
        type=int,
        help="initial disk count for the primary tower",
        default=None,
    )
    argparser.add_argument(
        "-gm",
        "--get-maxima",
        help="get maxima value for disk capacity",
        action="store_true",
    )
    argparser.add_argument(
        "--ascii", help="use ascii characters for rendering", action="store_true"
    )
    argparser.add_argument(
        "-im",
        "--interaction-mode",
        type=str,
        help="game interaction mode",
        default=None,
    )
    argparser.add_argument(
        "-tl",
        "--time-limit",
        type=int,
        help="pseudo time limit to solve toh in seconds",
    )
    argparser.add_argument("-f", "--file", type=str, help="solve toh from a file")
    argparser.add_argument(
        "-cv",
        "--check-version",
        help="check for new version and exit",
        action="store_true",
    )
    argparser.add_argument(
        "-d",
        "--debug",
        help="invoke debugger(for developer)",
        action="store_true",
    )
    argparser.add_argument(
        "-dt",
        "--delay-time",
        help="debug delay time after executing a subroutine(for developer)",
        action="store_true",
    )
    argparser.add_argument(
        "-v",
        "--version",
        help="Show utility version",
        action="version",
        version="{} {}".format(Misc.util_name, Misc.util_version),
    )
    args: argparse.Namespace = argparser.parse_args(sys_args)

    rod_disk_capacity: Optional[int] = args.disk_capacity
    interface_type: Optional[str] = args.interaction_mode
    render_ascii: bool = args.ascii
    if args.check_version:
        if version := version_validator():
            if not isinstance(version, (int, str)):
                # contains exception class in such case
                raise version("Internet Connection Error, retry after troubleshoot")
            else:
                print("New version available!: {}".format(version))
        else:
            print("Aready up to date")
        sys.exit(0)
    if args.get_maxima:
        # since Canvas isn't instantiated at this point Canvas.drawing_format
        # will be None , resulting in disk_width for ascii mode, which is actually
        # doubled for mentioned reasons. below we normalize that value.
        print("Maxima value: {}".format(Canvas.disk_horizontal() // 2))
        sys.exit(0)
    if args.file:
        validate_src = SourceValidationHandler(args.file)
        response: Union[str, bool] = validate_src.validate_toh_source()
        if isinstance(response, Tuple):
            print(
                """\x1b[31m**Illegal Move Attempted**
move: {}
Reason: {}\x1b[m""".format(
                    response[0], response[1]
                )
            )
        else:
            if response:
                print("\x1b[32mFile Validated Successfully!\x1b[m")
            else:
                print(
                    "\x1b[33mNo errors were encountered during the validation, but the puzzle was not solved, probably due to insufficient moves.\x1b[m"
                )
        sys.exit(0)

    disk_capacity = (
        args.disk_capacity
        if args.disk_capacity
        else Misc.default_config["disk_capacity"]
    )
    if disk_capacity > Canvas.disk_horizontal() // 2:
        raise DisksOverLimitError(
            "Disk number is over the permitted limit. provide a value `less than/equal to` value provided by --get-maxima."
        )
    contructer_args = {}
    for arg_name, arg_val in (
        ("player_name", args.player_name),
        ("disk_capacity", args.disk_capacity),
        ("render_ascii", args.ascii),
        ("interaction_mode", args.interaction_mode),
        ("time_limit", args.time_limit),
    ):
        if arg_val:
            if arg_name == "interaction_mode" and arg_val not in (
                "graphics",
                "textual",
                "t",
                "g",
                "tui",
            ):
                continue
            contructer_args.update({arg_name: arg_val})
        if dump_debug:
            print("**DEBUG**: CommandLineArg:: {}: {}".format(arg_name, arg_val))
    if dump_debug:
        sleep(5)

    contructer_args.update({"debug": dump_debug})
    tonoi_instance: Tonoi = Tonoi(**contructer_args)
    tonoi_instance.play()


def __into_main__(main_func) -> NoReturn:
    ansi_support: Optional[bool] = ansi_controlcode_supported()
    if ansi_support is False:
        print(
            """Your Windows build does not support Ansi Escape Sequences for cmd.exe.
You can do the following things:
1:Install Windows Anniversary Update(build-number: 14393), if on windows 10
2:Use Terminal emulator like ConEmu that supports Ansi Escape Sequences and set an environmental variable named `ANSI_SUPPORTED`(with any value), if on < Windows 10
3:Windows sucks, change to *nix"""
        )
        sys.exit(1)
    elif ansi_support is None:
        sys.exit(0)
    do_debug: bool = False
    delay_time: int = 5
    for idx, debug_arg in enumerate(["-d", "--debug", "--delay-time", "-dt"]):
        if debug_arg in sys.argv and idx in range(0, 2):
            do_debug = True
            sys.argv.remove(debug_arg)
        elif debug_arg in sys.argv and idx in range(2, 4):
            delay_time = int(sys.argv[sys.argv.index(debug_arg) + 1])
            sys.argv.remove(str(delay_time))
            sys.argv.remove(debug_arg)
    main = inject_debugger(absorbed_obj=delay_time, dump_debug=do_debug)(main_func)
    main(sys.argv[1:])


def main_entry() -> NoReturn:
    __into_main__(main)

