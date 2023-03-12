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
""" stdout and screen handler """

import re
import os
import sys
import copy
import random
import logging
from time import sleep
from .misc import ReturnCode
from .intrinsics import RodHandler
from .exceptions import ConfigParseError, ProhibitedMove, EmptyRodError
from typing import Tuple, List, Dict, Union, Optional, Callable, TypeAlias, NoReturn


class ConfigHandler:
    """Handle user config and
    data.

    Contains a simple parser for a specialized
    loosely typed markup language which wasn't even
    needed in the first place but wrote it anyway cuz felt like it, xdd + the parser is pretty shitty.
    """

    CONFIG: TypeAlias = Dict[
        str, Dict[str, Union[str, bool, int, Dict[str, Union[str, bool, int]]]]
    ]

    def __init__(self, conf_type) -> None:
        is_tonoi_src: bool = conf_type.startswith("::#")
        assert (
            conf_type in ["player_data", "player_config"] or is_tonoi_src
        ), "Invalid config type!"
        self.conf_type: str
        self.conf_file: str
        self.home_dir: str = os.getenv("HOME") or os.getenv("USERPROFILE")
        if is_tonoi_src:
            self.conf_type = "tonoi_src"
            self.conf_file = conf_type[3:]
        else:
            self.conf_type = conf_type
            self.conf_file = os.path.join(self.home_dir, conf_type + ".konf")
        # invoke enter even if ConfigHandler is not used as a context manager
        # warn:an extra invocation when used as a context manager
        self.__enter__()

    def __enter__(self) -> "self":
        try:
            self.io_obj = open(self.conf_file, mode="r+")
        except FileNotFoundError:

            class io:
                def __init__(self, conf_file, super_object) -> None:
                    io.conf_file = conf_file
                    io.super_object = super_object

                def open(self, *args, **kwargs) -> None:
                    pass

                def read(self, *args, **kwargs) -> None:
                    pass

                def write(self, *args, **kwargs) -> None:
                    pass

                def close(self, *args, **kwargs) -> None:
                    try:
                        self.conf.close()
                    except AttributeError:
                        pass

                def create_conf(self, *args, **kwargs):
                    open(io.conf_file, "w").close()
                    self.conf = open(self.conf_file, "r+")
                    return io.super_object.__class__(
                        os.path.basename(io.conf_file).strip(".konf")
                    )

            self.io_obj = io(self.conf_file, self)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.io_obj.close()

    def __sanitize_raw_config(self, raw_conf: List[List[str]]) -> List[List[str]]:
        raw_conf_copy: List[List[str]] = copy.deepcopy(raw_conf)
        for index, section in enumerate(raw_conf):
            for section_element in section:
                if section_element.startswith('"') or section_element.strip() == "":
                    raw_conf_copy[index].remove(section_element)
        return raw_conf_copy

    def __infere_datatypes(self, data: str) -> Union[str, int, bool]:
        infered_data: Union[str, int, bool]
        str_to_bool: Dict[str, bool] = {"True": True, "False": False}
        if data in ["True", "False"]:
            infered_data = str_to_bool[data]
        elif data.isdigit():
            infered_data = int(data)
        else:
            infered_data = data

        return infered_data

    def __get_err_ln_col(self, operand_str: str) -> Tuple[int, int]:
        # return line no of first match of str
        # kinda shitty but works so...
        for idx, line in enumerate(self.raw_config_copy.splitlines()):
            if operand_str in line:
                return idx + 1, line.index(operand_str.strip())

    def __parse_sections(
        self, section_list: List[List[str]], expr_delimiter: str
    ) -> "ConfigHandler.CONFIG":
        parsed_data: ConfigHandler.CONFIG = {}

        def get_section_name(section_element: str) -> str:
            # if section_element starts with `:` then its
            # should be a section/block definition, in which case
            # get the section name. doing it this way as some other
            # element might define a variable with -> as value
            if section_element.startswith(":"):
                return section_element.split("->")[1].strip()
            else:
                raise IndexError

        for section in section_list:
            section_name: str
            section_data: Dict[str, Union[str, Dict[str, str]]] = {}
            is_block: bool = False
            block_name: str
            block_data: Dict[str, str] = {}
            if len(section) == 0:
                # continue if the section is empty
                continue
            for index, section_element in enumerate(section):
                if index == 0:
                    try:
                        section_name = get_section_name(section_element)
                    except IndexError:
                        section_name = "Meta"
                        try:
                            key, val = section_element.split(expr_delimiter)
                        except ValueError:
                            ln, col = self.__get_err_ln_col(section_element)
                            raise ConfigParseError.BadAssignmentError(
                                "ln:{}:col:{}::Expected an '=' delimited assignment but got '{}' in section 'Meta'".format(
                                    ln, col, section_element
                                )
                            )
                        else:
                            section_data.update(
                                {key.strip(): self.__infere_datatypes(val.strip())}
                            )
                    finally:
                        continue
                if is_block:
                    if re.match(r"<\s+END\s+\w+", section_element):
                        section_data.update({block_name: block_data.copy()})
                        is_block = False
                        block_data.clear()
                        continue
                    try:
                        key, val = section_element.split(expr_delimiter)
                    except ValueError:
                        ln, col = self.__get_err_ln_col(section_element)
                        raise ConfigParseError.BadAssignmentError(
                            "ln:{}:col{}::Expected an '{}' delimited assignment but got '{}' in  block '{}'".format(
                                ln, col, expr_delimiter, section_element, block_name
                            )
                        )
                    else:
                        block_data.update(
                            {key.strip(): self.__infere_datatypes(val.strip())}
                        )
                else:
                    try:
                        key, val = section_element.split(expr_delimiter)
                    except ValueError:
                        if "->" not in section_element:
                            ln, col = self.__get_err_ln_col(section_element)
                            raise ConfigParseError.BadAssignmentError(
                                "ln:{}:col{}::Expected an '{}' delimited assignment but got '{}' in section '{}'".format(
                                    ln,
                                    col,
                                    expr_delimiter,
                                    section_element,
                                    section_name,
                                )
                            )
                        is_block = True
                        block_name = get_section_name(section_element)
                    else:
                        section_data.update(
                            {key.strip(): self.__infere_datatypes(val.strip())}
                        )

            parsed_data.update({section_name: section_data})

        return parsed_data

    def __get_section(
        self, raw_conf: str, section: str, is_meta: bool = False
    ) -> List[str]:
        section_start_re: re.Pattern = re.compile(
            r"::\s+START\s+->\s+{}".format(section)
        )
        section_end_re: re.Pattern = re.compile(r"<-\s+END\s+@?{}".format(section))
        if section_start_pattern_obj := section_start_re.search(raw_conf) or is_meta:
            raw_conf_list: List[str] = raw_conf.splitlines()
            section_start_index: int
            if not is_meta:
                inq_section_start: str = section_start_pattern_obj.group()
                try:
                    section_start_index = raw_conf_list.index(inq_section_start)
                except ValueError:
                    ln, col = self.__get_err_ln_col(inq_section_start)
                    raise ConfigParseError.BadSectionDefinition(
                        "ln:{}:col:{}::Section Head definition '{}' was illegally prefixed by character(s)".format(
                            ln, col, inq_section_start
                        )
                    )
            else:
                section_start_index = 0
            if section_end_pattern_obj := section_end_re.search(raw_conf):
                inq_section_end: str = section_end_pattern_obj.group()
                try:
                    section_endpoint_index: int = raw_conf_list.index(inq_section_end)
                except ValueError:
                    ln, col = self.__get_err_ln_col(inq_section_end)
                    raise ConfigParseError.BadSectionDefinition(
                        "ln:{}:col:{}::Section Endpoint definition '{}' was illegally prefixed by character(s).".format(
                            ln, col, inq_section_end
                        )
                    )
                return raw_conf_list[section_start_index:section_endpoint_index]
            else:

                raise ConfigParseError.BadSectionDefinition(
                    "Ambigious/Bad section definition for section `{}`!".format(section)
                )
        else:
            raise ConfigParseError.BadSectionDefinition(
                "Ambigious/Bad section definition for section `{}`!".format(section)
            )

    def read_config(self, sections: Optional[List[str]] = []) -> Dict:
        raw_config: str
        self.raw_config_copy: str
        raw_config = self.raw_config_copy = self.io_obj.read()
        new_raw_conf: List[List[str]] = []
        assert isinstance(
            sections, List
        ), "\x1b[31mExpected section list of type 'List' but got of type '{}'\x1b[m".format(
            type(sections).__name__
        )
        if sections:
            for section in sections:
                if not re.search(r"::\s+START\s+->\s+{}".format(section), raw_config):
                    raise ConfigParseError.SectionUndefinedError(
                        "No section definitions matched for '{}'!".format(section)
                    )
                new_raw_conf.append(
                    self.__get_section(raw_conf=raw_config, section=section)
                )
        else:
            if section_heads_list := re.findall(r"::\s+START\s+->\s+\w+", raw_config):
                for section_head in section_heads_list:
                    section: str = section_head.split("->")[1].strip()
                    new_raw_conf.append(
                        self.__get_section(raw_conf=raw_config, section=section)
                    )
            else:
                raise ConfigParseError.SectionUndefinedError(
                    "No valid section definitions found!"
                )

        meta_section: List[str] = self.__get_section(
            raw_conf=raw_config, section="meta", is_meta=True
        )
        sanitized_meta: List[List[str]] = self.__sanitize_raw_config([meta_section])
        parsed_meta: ConfigHandler.CONFIG = self.__parse_sections(
            sanitized_meta, expr_delimiter="="
        )
        expression_delimiter = (
            parsed_meta["Meta"].get("expression_delimiter") if parsed_meta else "="
        )
        expression_delimiter = expression_delimiter or "="
        sanitized_raw_conf: List[List[str]] = self.__sanitize_raw_config(new_raw_conf)
        parsed_conf: ConfigHandler.CONFIG = self.__parse_sections(
            sanitized_raw_conf, expr_delimiter=expression_delimiter
        )

        parsed_conf.update(parsed_meta)

        self.io_obj.seek(0)

        return parsed_conf

    def validate_config_existence(self) -> bool:
        return os.path.exists(self.conf_file)

    def create_player_data_file(self) -> int:
        self.io_obj.write(
            """
" This Template was  automatically created by tonoi
" this file stores 'play history' of every registered player.
" Don't edit this file unless you know what you are doing
seed_value = 0
<- END @meta


:: START -> play_history
" this section stores player play history.
" All the player's play history will be here in data_structure called a block,
" each having its own block-name/id
" examplory block definition:
"   : START -> block_name
"       attr_1 = 10
"       attr_2 = a string
"       attr 3 = False
"   < END block_name


<- END play_history"""
        )
        # return initial seed value
        # -1 as generating player name will
        # normalize it to 0
        return -1

    def update_player_data(self, player_Id: int, **kwargs) -> None:
        assert (
            self.conf_type == "player_data"
        ), "This method only works with config of type `player_data`"
        player_name_re: re.Pattern = re.compile(
            r"\s*:\s+START\s+->\s+{}".format(player_Id)
        )

        def add_newline(position: str, op_str: str) -> str:
            if position in ["start", "end"] and not (
                op_str.endswith("\n") or op_str.startswith("\n")
            ):
                return "\n"
            return ""

        with open(self.conf_file, "r") as conf_file:
            config_data: str = conf_file.read()
        matched_patt = player_name_re.search(config_data)
        if matched_patt:
            conf_delimiter: str = matched_patt.group()
            conf_data_list: List[str] = config_data.split(conf_delimiter)
            conf_before: str = conf_data_list[0]
            conf_after: str = conf_data_list[1]
            var_list: List[str] = ["best_game_runs", "perfect_game_runs"]
            for var in var_list:
                var_matching_re: str = r"\s*{}\s+=\s+\w+".format(var)
                conf_after = re.sub(
                    count=1,
                    pattern=var_matching_re,
                    repl="\n" + var + " = " + str(kwargs.get(var)),
                    string=conf_after,
                )
            config_data: str = (
                conf_before
                + add_newline("start", conf_before)
                + conf_delimiter
                + add_newline("end", conf_after)
                + conf_after
            )
        else:
            config_data = (
                config_data[:-19]
                + """

: START -> {}
best_game_runs = {}
perfect_game_runs = {}
< END {}""".format(
                    player_Id,
                    kwargs.get("best_game_runs"),
                    kwargs.get("perfect_game_runs"),
                    player_Id,
                )
                + "\n<- END play_history"
            )
        with open(self.conf_file, "w") as write_conf:
            write_conf.write(config_data)

    @staticmethod
    def create_config() -> None:
        conf_path: str = os.path.join(
            (os.getenv("HOME") or os.getenv("USERPROFILE")), "player_config.konf"
        )
        if os.path.exists(conf_path):
            return None
        io_obj = open(conf_path, "w")
        io_obj.write(
            """
" Tonoi configuration file
" Switches passed to tonoi can also be defined here
<- END @meta

:: START -> tonoi_config

disk_capacity = 3
render_ascii = False
interface_type = graphics
debug = False

<- END tonoi_config"""
        )
        io_obj.close()

    def read_toh_src(self) -> Tuple[str, List[str]]:
        if not self.validate_config_existence():
            raise FileNotFoundError(
                "Source file not found!.check the path and try again."
            )
        src_data: str = self.io_obj.read()
        src_data_list = src_data.splitlines()
        empty_str_count: int = src_data_list.count("")
        for _ in range(empty_str_count):
            src_data_list.remove("")
        try:
            _ = int(src_data_list[0])
        except ValueError:
            raise AssertionError(
                "\x1b[31mExpected an integer as a torwer size but got {}\x1b[m".format(
                    src_data_list[0]
                )
            )
        return src_data_list[0], src_data_list[1:]

    def update_seed_value(self, seed_value: int) -> None:
        get_seed_re = re.compile(r"seed_value\s+=\s+\d+")
        config: str = self.io_obj.read()
        self.io_obj.seek(0)
        new_config = get_seed_re.sub("seed_value = {}".format(seed_value), config)
        self.io_obj.write(new_config)

    def write_config(self, *args, **kwargs) -> NoReturn:
        raise NotImplementedError("write_config() is not implemented as of now!")


class EventHandler:
    def __init__(self) -> None:
        self.event_list: Dict[str, Callable] = {}

    def register_event(self, name: str, callback: Callable) -> None:
        """
        event types:
         - terminal_size_change ----
                                    |- atrribute_change
                                    |- terminal_size_error
         - atrribute_change
         - error_out ---
         -              |- crash_log
         - time_log
        """
        # TODO: for [0.2.0 .. 1.0.0]: multiplayer mode in local network using sockets.
        self.event_list.update({name: callback})

    def handle_event(
        self, name: str, callback_args: Dict[str, Union[bool, str, int]] = {}
    ) -> None:
        self.event_list[name](**callback_args)


class StdoutHandler:
    handlers_list: Dict[str, "StdoutHandler"] = {}

    class BufferCache(Dict):
        def __init__(self, **kwargs) -> None:
            self.counter = 0
            super().__init__(**kwargs)

        def update(self, mapping={}, **kwargs) -> None:
            map_tuple = tuple(mapping.items())[0]
            key, val = map_tuple
            # `{n}_%%%` act as special characters delimiters
            # used to distinguish same text. these characters
            # cant be used in regular text
            key = "{}_%%%{}".format(self.counter, key)
            super().update({key: val})
            self.counter += 1

        def get_line_data(self, line: int) -> Dict[int, str]:
            # print(self)
            # sleep(0.06)
            # input()
            line_data: Dict[int, str] = {}
            for key, val in self.items():
                if val[0] == line:
                    key = key.split("_%%%")[1]
                    line_data.update({val[1]: "\x1b[{}m".format(val[2]) + key})
            return line_data

    def __init__(self, name: str = None) -> None:
        self.name: str = name or self.name
        # list of SGR parameters: https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_(Select_Graphic_Rendition)_parameters
        self.color_list: Dict[str, int] = {
            "default": 0,
            "red": 31,
            "green": 32,
            "yellow": 33,
            "blue": 34,
            "cyan": 36,
            "white": 97,
        }
        self.buffer_cache: StdoutHandler.BufferCache = StdoutHandler.BufferCache()
        self.hide_buffer_cache: bool = False
        StdoutHandler.handlers_list.update({name: self})

    @property
    def coordinates(self) -> os.terminal_size:
        return os.get_terminal_size()

    @property
    def random_color(self) -> str:
        return random.choice(tuple(self.color_list.keys()))

    def transit_position(self, line: int, col: int) -> None:
        print("\x1b[{};{}H".format(line, col), end="")

    def print_stdout(
        self,
        position: Union[Tuple[int, int], str],
        text: str,
        color: Optional[str] = None,
        blink_text: bool = False,
        return_coords_only: bool = False,
        after_position: Optional[Union[Tuple[int, int], str]] = None,
    ) -> Optional[Tuple[int, int]]:
        if color is None:
            color = "default"
        elif color == "random":
            color = self.random_color
        if isinstance(position, Tuple):
            lines, cols = position
        elif isinstance(position, str):
            cols, lines = self.coordinates
            if position == "center":
                cols = cols // 2 - len(text) // 2
                lines //= 2
            elif position == "top-left":
                lines = 0
                cols = 0
            elif position == "top-right":
                lines = 0
                cols = cols - len(text)
            elif position == "bottom-left":
                cols = 0
            elif position == "bottom-right":
                cols = cols - len(text)
            elif position == "after-prompt":
                lines -= 2
                cols = 7
            else:
                raise NotImplementedError("Undefined position string!")
        else:
            raise AssertionError(
                "Position '{}' is not supported!".format(type(position))
            )
        if return_coords_only:
            return lines, cols
        if self.hide_buffer_cache:
            line_data = {cols: "\x1b[{}m".format(self.color_list.get(color)) + text}
        else:
            self.buffer_cache.update({text: (lines, cols, self.color_list.get(color))})
            line_data = self.buffer_cache.get_line_data(lines)
        index_print_order = sorted(line_data)
        # ANSI control codes
        # reference:
        #           https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_(Control_Sequence_Introducer)_sequences
        #           https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797
        for print_index in index_print_order:
            print("\x1b[5m" if blink_text else "", end="")
            print(
                "\x1b[{};{}H".format(
                    lines,
                    print_index,
                ),
                line_data[print_index],
                end="",
            )
            sys.stdout.flush()
            print("\x1b[0K", end="")  # erase from cursor to end of line
            print("\x1b[25m", end="")  # reset blinking effect
        if after_position:
            lines, cols = self.print_stdout(after_position, "", return_coords_only=True)
            print("\x1b[{};{}H".format(lines, cols), end="")

        # print("\x1b[0K", end="") # erase from cursor to end of lines
        # print("\x1b[{}D".format(len(text)), end="") # move cursor len(text) cols left
        # print("\x1b[1K", end="") # erase from cursor to beginning of line
        # print("\x1b[{}C".format(len(text)), end="") # move cursor len(text) right


class LogHandler:
    """
    use logging module for both logging to stdout
    and file.
    """

    def __init__(self) -> None:
        pass


class SourceValidationHandler:
    def __init__(self, toh_source: str) -> None:
        self.toh_source: str = toh_source

    def validate_toh_source(self) -> Union[Tuple[str, str], bool]:
        with ConfigHandler("::#" + self.toh_source) as toh_source:
            rod_capacity, moves_list = toh_source.read_toh_src()
        game_handle = RodHandler(int(rod_capacity))
        for move in moves_list:
            try:
                src, dest = move.split("->")
            except ValueError:
                # raised when there are less moves then
                # declared for rod_capacity, tldr: not enough
                # moves were given for game to end
                return False
            try:
                game_won: bool = game_handle.move_disk(int(src), int(dest))
            except ProhibitedMove:
                return move, "Larger disk can't be put over a smaller disk!"
            except EmptyRodError:
                return move, "Can't move a disk from empty rod"
        if game_won:
            return True
        else:
            return False
