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
""" drawer for the game """

import os
import random
from time import sleep
from .handlers import StdoutHandler
from .termutils import clear_screen
from .exceptions import TerminalSizeError
from typing import Any, List, Tuple, Dict, Callable, ClassVar, Union, Optional, Iterator


class GeometricalShapes:
    # ascii -> ascii character encoding
    # ansi -> unicode character encoding
    class Shapes:
        # codepoints can also be used for unicode characters
        # but literal character definition is better and more understandable.
        rod_component: Dict[str, str] = {"ascii": "||", "ansi": "██"}
        disk_component: Dict[str, str] = {
            "ascii": ["[", "#", "]"],
            "ansi": ["[", "██", "]"],
        }
        box_component: Dict[str, Dict[str, str]] = {
            "horizontal_line": {"ascii": "-", "ansi": "═"},
            "vertical_line": {"ascii": "|", "ansi": "║"},
            "ansi_box_corner": {
                "top_right": "╗",
                "top_left": "╔",
                "bottom_right": "╝",
                "bottom_left": "╚",
            },
        }
        life_indicator: Dict[str, str] = {"ascii": "*", "ansi": "♡"}
        bird: Dict[str, str] = {"ascii": "~v~", "ansi": "🕊"}

    @classmethod
    def render_box_component(
        cls, render_type: str, characters: int = 1, render_format: str = "ansi"
    ) -> str:
        return cls.Shapes.box_component[render_type][render_format] * characters

    @classmethod
    def render_rod_component(cls, render_format: str = "ansi") -> str:
        return "".join(cls.Shapes.rod_component[render_format])

    @classmethod
    def render_disk_component(
        cls,
        characters: int = 1,
        render_format: str = "ansi",
        no_extremes: bool = False,
    ) -> str:
        disk_char_index: int = 1
        base_disk: List[str] = cls.Shapes.disk_component[render_format].copy()
        if no_extremes:
            base_disk = base_disk[1:-1]
            disk_char_index = 0
        base_disk.insert(1, base_disk[disk_char_index] * (characters - 1))
        return "".join(base_disk)

    @classmethod
    def render_life_indicator(cls, render_format: str = "ansi") -> None:
        return cls.Shapes.life_indicator[render_format]

    @classmethod
    def render_bird(cls, render_format: str):
        return cls.Shapes.bird[render_format]


class Canvas(StdoutHandler):
    def __init__(self, name: str, drawing_format: str) -> None:
        super().__init__(name=name)
        self.drawing_format: str
        Canvas.drawing_format: ClassVar[str]
        self.drawing_format = Canvas.drawing_format = drawing_format
        self.item_info: Dict[str, Any] = {}
        self.disks_info: Dict[int, Dict[int, Tuple[int, str, int]]] = {}
        self.disk_width: Optional[int] = None
        self.init_disk_width: Optional[int] = None

    def partial_reinit(self) -> None:
        # for calculating the disk width, we divide total columns into 3 parts.
        # a unit space being 1/3 of total columns, then we again divide that unit space
        # by 2 to get to center of that unit space and subtracting an arbitrary, i.e: 5
        # gets us to more or less a suitable disk_width to start printing the disk.
        # we double the disk width in ascii format as same number of disk components
        # are reduced to render it properly.
        Canvas.drawing_format = self.drawing_format
        self.disk_width = self.disk_horizontal()
        if not self.init_disk_width:
            # if self.init_disk_width is set , that means
            # terminal window is probably resized, in which
            # case don't update inital disk width, otherwise
            # update it.
            self.init_disk_width = self.disk_horizontal()

    # synonmyous to disk_width
    @classmethod
    def disk_horizontal(cls) -> int:
        cols, _ = os.get_terminal_size()
        return (
            ((cols // 6) - 5) if cls.drawing_format == "ansi" else ((cols // 6) - 5) * 2
        )

    def draw_tower(
        self,
        line: int,
        column: int,
        rod_no: int,
        appearent_disk_count: int,
        rod_component_count: int,
        *,
        is_cloud: bool = False,
        top_el_only: bool = False,
        actual_disk_count: Optional[int] = None
    ) -> None:
        rod: Dict[int, Tuple[int, str]]
        cols_copy: int = column
        try:
            rod = self.disks_info[rod_no]
        except KeyError:
            rod = self.disks_info[rod_no] = {}
            if rod_no == 1:
                assert actual_disk_count, "`actual_disk_count` missing!"
                column_offset: int = 0
                for disk_no in range(actual_disk_count):
                    self.disks_info[rod_no][disk_no] = (
                        self.disk_width,
                        self.random_color,
                        column_offset,
                    )
                    self.disk_width = (
                        self.disk_width - 1
                        if self.drawing_format == "ansi"
                        else self.disk_width - 2
                    )
                    column_offset += 1
                rod = self.disks_info[rod_no]
        if is_cloud:
            init_cloud_width: int = self.disk_horizontal()
            rod = {
                0: (init_cloud_width, "cyan", 0),
                1: (init_cloud_width - 1, "cyan", 1),
                2: (init_cloud_width - 2, "cyan", 2),
            }
        if top_el_only:
            try:
                top_element_idx: int = list(rod.keys())[-1]
            except IndexError:
                pass
            else:
                top_element: Tuple[int, str, int] = rod[top_element_idx]
                rod: Dict[int, Tuple[int, str, int]] = {0: top_element}
                appearent_disk_count = 1
            rod_component_count = 1

        if not len(rod) == 0:
            for idx in range(appearent_disk_count):
                column = cols_copy + rod[idx][2]
                self.print_stdout(
                    position=(line, column),
                    text=GeometricalShapes.render_disk_component(
                        **{
                            "characters": rod[idx][0],
                            "no_extremes": is_cloud,
                            "render_format": self.drawing_format,
                        },
                    ),
                    color=rod[idx][1],
                )
                line -= 1
        column = cols_copy
        column += (
            self.init_disk_width
            if self.drawing_format == "ansi"
            else (self.init_disk_width // 2)
        )
        for _ in range(rod_component_count):
            self.print_stdout(
                position=(line, column),
                text=GeometricalShapes.render_rod_component(
                    **{"render_format": self.drawing_format}
                ),
            )
            line -= 1

    def draw_box_output(
        self,
        text: str,
        box_position: str,
        text_position: int = 0,
        box_title: Optional[str] = None,
        blink_box_title: bool = False,
        text_color: str = "random",
        box_title_color: str = "random",
        return_only: bool = False,
    ) -> Optional[Dict[str, Any]]:
        assert isinstance(
            box_position, str
        ), "Position of type '{}' is not supported!".format(type(box_position).__name__)

        # max_line_len is the maximum length of printable text in a line
        cols: int
        lines: int
        max_line_len: int
        text_list: List[str]
        box_vertical_length: int
        box_horizontal_length: int

        # an extra space a box saves a box...
        """
        if text:
            text += " "
        """

        if box_position == "center":
            text_list = text.split("\n")
            max_line_len = sorted(map(len, text_list))[-1]
            # since we print one sentence from text_list per line,
            # vertical length of the box will be length of text_list + 1
            # and horizontal length will be: max_line_len + 2(for corner characters)
            box_vertical_length = len(text_list) + 1
            box_horizontal_length = max_line_len + 2
            lines = (self.coordinates.lines // 2) - (box_vertical_length // 2)
            cols = (self.coordinates.columns // 2) - (box_horizontal_length // 2)
        elif box_position == "bottom-full":
            text_list = [" " * text_position + text]
            # -2(for corner characters) - 1(as max_line_len will be 1 less than horizontal length)
            # -1(since one column will be reserved for printing full screen banner )
            # -3(as printing from col 3)
            max_line_len = self.coordinates.columns - 7
            box_horizontal_length = max_line_len + 2
            box_vertical_length = 1
            cols = 3
            # -2(for printing the actual box) -1(for printing full screen box)
            lines = self.coordinates.lines - 3
        elif box_position == "full-screen":
            max_line_len = self.coordinates.columns - 3
            box_horizontal_length = max_line_len + 2
            box_vertical_length = self.coordinates.lines
            cols = 0
            lines = 1
            text_list = [""] * box_vertical_length
        elif box_position == "top-full":
            max_line_len = self.coordinates.columns - 7
            box_horizontal_length = max_line_len + 2
            box_vertical_length = 3
            cols = 3
            # 1(as printing at ln 0 doesn't seem to work) + 1(leaving 1 line for full screen box)
            lines = 2
            text_list = ["", " " * text_position + text, ""]

        else:
            raise AssertionError("Position string Undefined!")
        self.item_info.update(
            {
                "{}-box".format(box_position): {
                    "box_vertical_length": box_vertical_length,
                    "box_horizontal_length": box_horizontal_length,
                    "text_list": text_list,
                    "coordinates": (lines, cols),
                    "max_line_len": max_line_len,
                    "box-title": box_title,
                }
            }
        )
        if return_only:
            return self.item_info
        if box_title:
            self.print_stdout(
                (lines - 1, cols + max_line_len // 2 - len(box_title) // 2),
                box_title,
                box_title_color,
                blink_text=blink_box_title,
            )
        # draw upper and bottom exteriors of the box
        def draw_box_exteriors(exterior_type: str, lines: int, cols: int) -> None:
            assert exterior_type in ["top", "bottom"], "Undefined exerior type!"
            self.print_stdout(
                (lines, cols),
                (
                    GeometricalShapes.render_box_component(
                        render_type="ansi_box_corner",
                        render_format="{}_left".format(exterior_type),
                    )
                    + GeometricalShapes.render_box_component(
                        render_type="horizontal_line",
                        characters=box_horizontal_length
                        - 2,  # '- 2' cuz of two extra characters, i.e '╗/|'
                        render_format=self.drawing_format,
                    )
                    + GeometricalShapes.render_box_component(
                        render_type="ansi_box_corner",
                        render_format="{}_right".format(exterior_type),
                    )
                )
                if self.drawing_format == "ansi"
                else (
                    GeometricalShapes.render_box_component(
                        render_type="vertical_line", render_format="ascii"
                    )
                    + GeometricalShapes.render_box_component(
                        render_type="horizontal_line",
                        characters=box_horizontal_length - 2,
                        render_format=self.drawing_format,
                    )
                    + GeometricalShapes.render_box_component(
                        render_type="vertical_line", render_format="ascii"
                    )
                ),
                color="random",
            )

        draw_box_exteriors("top", lines, cols)
        lines += 1
        # middle part of the box
        for line in text_list:
            # first vertical line and the text
            self.print_stdout(
                (lines, cols),
                GeometricalShapes.render_box_component(
                    render_type="vertical_line", render_format=self.drawing_format
                )
                + line,
                color=text_color,
            )
            # cols = cols + max_line_len + 2 when printing full-screen as last col is specifically
            # left for printing it. otherwise 1 as all other text will be printed inside the
            # full-screen box.
            self.print_stdout(
                (
                    lines,
                    cols + max_line_len + (2 if box_position == "full-screen" else 1),
                ),
                GeometricalShapes.render_box_component(
                    render_type="vertical_line", render_format=self.drawing_format
                ),
                color=text_color,
            )
            lines += 1

        draw_box_exteriors("bottom", lines, cols)
        lines += 1

    def get_appearent_disk_count(self, actual_disk_count: int) -> Tuple[int, int, bool]:
        # if actual disk count is renderable on current terminal size
        # then return the actual_disk_count. otherwise calculate the
        # appearent disk count.
        """
        Returns the appearent disk count + optional int
        bool to check whether to render clouds
        , over limit indicator, i.e [^]

        """
        calculation: Tuple[int, int, bool]

        other_items_occupancy: int = (
            11  # 6 for upper boxes + 4 for lower boxes + 1 for Rod
        )
        available_lines: int = self.coordinates.lines - other_items_occupancy
        # disk_width also represent the vertical lenght of the tower
        # as that no of disks will be rendered to stdout.
        disk_width: int = (
            self.disk_width if self.drawing_format == "ansi" else self.disk_width // 2
        )
        if actual_disk_count <= disk_width and actual_disk_count < available_lines:
            return actual_disk_count, 0, False
        # clouds rendering line postion w.r.t bottom
        clouds_pos_line_bottomup: int = (disk_width + available_lines + 2) // 2
        # clouds rendering line postion w.r.t top
        clouds_pos_line_updown: int = self.coordinates.lines - clouds_pos_line_bottomup
        if disk_width >= available_lines:
            calculation = (
                available_lines - 2,
                0,
                True,
            )  # -2 to make it more organic
        elif (
            clouds_pos_line_bottomup + 3 >= available_lines
        ):  # +3 to add vertical length of a cloud
            calculation = disk_width - 2, 0, True
        elif clouds_pos_line_bottomup + 3 < available_lines:
            calculation = disk_width - 2, clouds_pos_line_updown, True
        else:
            raise ValueError("Could not determine the appearent disk count!")
        return calculation

    def get_appearent_rod_count(
        self, appearent_disk_count_generic: int, appearent_disk_count_curr: int
    ) -> int:
        return (appearent_disk_count_generic + 1) - appearent_disk_count_curr

    def draw_scenery(self, lines: int, cols: int, rod_no: int) -> None:
        def draw_cloud(lines, cols):
            self.draw_tower(
                lines,
                cols,
                rod_no=None,
                appearent_disk_count=3,
                rod_component_count=0,
                is_cloud=True,
            )

        def draw_bird(lines, cols):
            self.print_stdout(
                (lines, cols), GeometricalShapes.render_bird(self.drawing_format)
            )

        def calc_bird_rendition_coords(**kwargs) -> Iterator[Tuple[int, int]]:
            cols: int = kwargs.get("cols")
            lines: int = kwargs.get("lines")
            rod_no: int = kwargs.get("rod_no")
            vertical_pos_limit: int = kwargs.get("vertical_pos_limit")
            horizontal_pos_limit: int = kwargs.get("horizontal_pos_limit")
            horizontal_pos_limit = (
                horizontal_pos_limit * 2
                if self.drawing_format == "ansi"
                else horizontal_pos_limit
            )
            assert rod_no in [1, 2, 3], "Invalid Rod number!"
            print_vertical: bool = False if rod_no == 1 else True
            try:
                if print_vertical:
                    for vertical_position in range(vertical_pos_limit):
                        lines = lines + (
                            1
                            if not (
                                rod_no == 3
                                and vertical_position == vertical_pos_limit - 1
                            )
                            else 0
                        )
                        yield lines, cols + random.randint(2, horizontal_pos_limit)
                else:
                    yield lines + 1, cols + random.randint(2, horizontal_pos_limit)
            except ValueError:
                raise TerminalSizeError

        draw_cloud(lines, cols)
        coords_iterator: Iterator[Tuple[int, int]] = calc_bird_rendition_coords(
            lines=lines,
            cols=cols,
            rod_no=rod_no,
            horizontal_pos_limit=self.disk_horizontal(),
            vertical_pos_limit=3,
        )
        bird_rendition_rate: int = 3
        for _ in range(bird_rendition_rate):
            try:
                ln, col = next(coords_iterator)
                draw_bird(ln, col)
            except StopIteration:
                break

    def draw_overlimit_indicator(
        self, disks_overlimit: int, lines: int, cols: int
    ) -> None:
        self.print_stdout(
            (lines, cols), "[\x1b[1;31;5m^\x1b[0m{}]".format(disks_overlimit)
        )

    def prepare_upper_box_elements_string(self, **kwargs) -> str:
        item_list: List[str] = []
        for key, val in kwargs.items():
            if key == "Remaining_Lives":
                continue
            item_list.append(key.replace("_", " ") + ": " + val)
        remaining_lives: int = kwargs.get("Remaining_Lives")
        upper_box_max_len: int = (
            self.draw_box_output("", "top-full", return_only=True)
        )["top-full-box"].get("max_line_len")
        acumulative_items_space: int = (
            sum(
                map(
                    len,
                    item_list,
                )
            )
            + int(remaining_lives) * 2
            + 17
        )  # remaining_lives * 2 as each life indicator will be seperated by a space + 17 for predicate text.

        # padding per item will be calculated by subtracting the max_line_len from
        # acumulative_items_space(space occupied by all the items) then dividing it
        # by 4 to get unit padding
        padding: int = (upper_box_max_len - acumulative_items_space) // 4

        final_str: str = (" " * padding).join(
            item_list
            + [
                "Remaining Lives: "
                + " ".join(
                    [GeometricalShapes.render_life_indicator(self.drawing_format)]
                    * int(remaining_lives)
                ),
            ]
        )

        # Do the text wraping if length of the string is greater than available columns
        # just trunctuate the part of string , that can't be fitted in the box + print
        # ... to show such.
        final_str = (
            final_str[: -(len(final_str) - upper_box_max_len + 4)] + "..."
            if len(final_str) > upper_box_max_len
            else final_str
        )

        return final_str

    def dettach_buffer_cache(sleep_after: int = 0) -> Callable:
        def outer(func) -> Callable:
            def inner(self, *args, **kwargs) -> Any:
                self.hide_buffer_cache = True
                clear_screen()
                return_values = func(self, *args, **kwargs)
                self.hide_buffer_cache = False
                sleep(sleep_after)
                return return_values

            return inner

        return outer

    @dettach_buffer_cache(sleep_after=4)
    def draw_win_screen(
        self,
        used_moves: int,
        disk_count: int,
    ) -> None:
        # clear the buffer cache to avoid printing garbage
        # self.buffer_cache.clear()
        # the minimum amount of moves(minima) required to solve puzzle having
        # n number of disks is: 2^n - 1
        minima: int = pow(2, disk_count) - 1
        playing_efficiency: float = minima / used_moves * 100
        box_text: str = """You have successfully solved the puzzle!
Minimum Moves Required: %d
No of Moves Used: %d
Playing Efficiency: %f%%""" % (
            minima,
            used_moves,
            playing_efficiency,
        )
        self.draw_box_output(
            box_text,
            box_position="center",
            box_title="CONGRATULATION!",
            blink_box_title=True,
        )

    @dettach_buffer_cache(sleep_after=13)
    def draw_death_screen(self, msg: str) -> None:
        self.draw_box_output(
            text=msg,
            box_position="center",
            text_color="red",
            box_title="FAILURE",
            box_title_color="red",
            blink_box_title=True,
        )

    @dettach_buffer_cache(sleep_after=3)
    def draw_warning_screen(self, msg: str) -> None:
        box_text = """
MESSAGE:
    {}
""".format(
            msg
        )
        self.draw_box_output(
            text=box_text,
            box_position="center",
            text_color="yellow",
            box_title="WARNING",
            box_title_color="yellow",
            blink_box_title=True,
        )

    @dettach_buffer_cache(sleep_after=0)
    def draw_info_screen(self, msg: str) -> None:
        box_text = """
MESSAGE:
    {}
""".format(
            msg
        )
        self.draw_box_output(
            text=box_text,
            box_position="center",
            text_color="blue",
            box_title="INFO",
            box_title_color="blue",
            blink_box_title=True,
        )

    @dettach_buffer_cache(sleep_after=3)
    def draw_error_screen(self, msg: str) -> None:
        box_text = """
MESSAGE:
    {}
""".format(
            msg
        )
        self.draw_box_output(
            text=box_text,
            box_position="center",
            text_color="red",
            box_title="ERROR",
            box_title_color="red",
            blink_box_title=True,
        )

    @dettach_buffer_cache(sleep_after=0)
    def draw_confirmation_box(self, msg: str) -> Tuple[int, int]:
        """Afterwards return proper cursor position to transit to, for taking input"""
        box_text = """
MESSAGE:
    {}
=> Continue with the action [Y/n]:   
""".format(
            msg
        )
        msg_len: int = len(msg.split("\n"))
        line = self.coordinates.lines // 2 + msg_len // 2 + 1
        col = self.coordinates.columns // 2 + 18
        self.draw_box_output(
            text=box_text,
            box_position="center",
            text_color="yellow",
            box_title="CONFIRMATION",
            box_title_color="yellow",
            blink_box_title=True,
        )
        return (line, col)
