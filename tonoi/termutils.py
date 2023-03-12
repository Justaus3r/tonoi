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
""" terminal utils """

import os
import platform
import threading
import subprocess
from time import sleep
from typing import Optional


def clear_screen() -> None:
    print("\x1b[2J", end="")


def get_platform() -> str:
    return platform.system()


def ansi_controlcode_supported() -> Optional[bool]:
    if os.getenv("ANSI_SUPPORTED"):
        return True
    if platform.system() == "Windows":
        reg_get_cmd: str = 'powershell "$(Get-ItemProperty HKCU:\Console VirtualTerminalLevel).VirtualTerminalLevel"'
        reg_set_cmd: str = (
            "Set-ItemProperty HKCU:\Console VirtualTerminalLevel -Type DWORD 1"
        )
        platform_version: List[str] = platform.version().split(".")
        if platform_version[0] == "10" and int(platform_version[2]) > 14393:
            if not subprocess.getoutput(reg_get_cmd) == "1":
                print(
                    "Your Windows build supports Ansi Escape Sequences but it is not enabled.\nIt can be done by creating a DWORD named `VirtualTerminalLevel` with `1` stored.\nFollowing command can also be used in an administrative powershell instance to do so:\n{}".format(
                        reg_set_cmd
                    )
                )
                return None
        else:
            return False
    return True


class ThreadedEventsAdaptor(threading.Thread):
    # 2 -> pause the execution status of the thread ; 1 -> default, normal run ; 0 -> halt the execution of
    # thread

    signal: int = 1

    def __init__(
        self,
        event_handle: "EventHandler",
        screen_data: "ScreenData",
        canvas: "Canvas",
        tonoi: "Tonoi",
    ) -> None:
        self.event_handle: "EventHandler" = event_handle
        self.screen_data: "ScreenData" = screen_data
        self.tonoi_obj: "Tonoi" = tonoi
        self.canvas_obj: "Canvas" = canvas
        super().__init__()

    def run(self) -> None:
        self.overwatch(self.event_handle)

    def overwatch(self, event_handle: "EventHandler") -> None:
        while self.signal:
            # Ewwwk! busywaiting.....
            # Reference: https://en.wikipedia.org/wiki/Busy_waiting
            # removing the sleep will cause your pc to go into jihad mode.
            sleep(0.3)
            if self.signal == 2:
                continue
            lines: int
            columns: int
            columns, lines = os.get_terminal_size()

            if columns != self.screen_data.columns and lines == self.screen_data.lines:
                self.screen_data.columns = columns
                event_handle.handle_event("elict_term_width_warning")

            elif (lines, columns) != (self.screen_data.lines, self.screen_data.columns):
                self.screen_data.lines, self.screen_data.columns = lines, columns
                (
                    self.screen_data.appearent_max_disk_count_nrod,
                    *_,
                ) = self.canvas_obj.get_appearent_disk_count(
                    self.canvas_obj.disk_horizontal()
                )
                event_handle.handle_event("redraw")

            elif self.tonoi_obj.time_limit and not self.tonoi_obj.no_tl_dialog:
                time_limit: int = self.tonoi_obj.get_time_limit(value_only=True)
                self.event_handle.handle_event(
                    "time_limit_indicator",
                    callback_args={"time_remaining": time_limit},
                )
