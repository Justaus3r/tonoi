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
""" Misc stuff """

import os
import pprint
import random
import subprocess
from time import sleep
from typing import Dict, Optional, Union, Callable, Type

no_requests: bool = False

try:
    import requests
    from requests.exceptions import ConnectionError
except ImportError:
    import json
    from urllib.request import urlopen
    from urllib.error import HTTPError

    no_requests = True

    class ConnectionError(Exception):
        """dummpy exception class when requests isn't available"""


class Misc:
    util_name: str = "tonoi"
    util_version: str = "0.2.0"
    util_usage: str = "{} [options]".format(util_name)
    util_description: str = "A playable implementation of towers of hanoi"
    util_epilog: str = """Notes:
(1)Most configuration switches specified here can also be specified in '{}/player_config.konf'.
(2)Disk count can't be greater than maxima value provided by --get-maxima/-gm option.""".format(
        os.getenv("HOME")
    )
    util_howtoplay: str = """Welcome to Tonoi
This is a playable implementation of a mathematical
puzzle called Towers of hanoi. the game is pretty simple,
one has to move disks from first rod to third abiding by 
following two rules:
1: Only one disk can be moved at a time.
2: A bigger disk may not be put over a smaller disk.
Wiki link: https://en.wikipedia.org/wiki/Tower_of_Hanoi). 

You can use `list-commands` command to list all the 
valid commands.

Press Enter to Continue"""
    default_config: int = {
        "disk_capacity": 3,
        "render_ascii": False,
        "interface_type": "graphics",
        "debug": False,
    }


class ReturnCode:
    SUCCESS: int = 0
    FAILURE: int = 1


def inject_debugger(
    absorbed_obj: Union[object, Callable, int], dump_debug: bool = False
) -> Union[object, Callable]:

    if isinstance(absorbed_obj, type):

        class innercls(absorbed_obj):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)

            def recon(self) -> Dict[str, str]:
                recon_data: Dict[str, str] = {}
                self.recon_data.update({"instance_vars: ": {self.__dict__}})
                self.recon_data.update(
                    {
                        "class_vars: ": dict(
                            [
                                (key, val)
                                for key, val in self.__class__.__dict__.items
                                if not key.startswith("__")
                            ]
                        )
                    }
                )
                return recon_data

            def dump_debug_data(self) -> None:
                pp = pprint.PrettyPrinter(indent=4)  # vewy sus
                recon_data: Dict[str, str] = self.recon()
                pp.pprint(recon_data["instance_vars"])
                print("\n\n")
                pp.pprint(recon_data["class_vars"])

        return innercls
    elif isinstance(absorbed_obj, (Callable, int)):

        def innerfunc(func):
            # incase the decorator is used on a function,
            # absorb the integer delay value and delay
            # after executing the function.
            def inside_inner(*args, **kwargs):
                kwargs.update({"dump_debug": dump_debug})
                if dump_debug:
                    print(
                        "**DEBUG**: After-func-exec delay time: {}".format(absorbed_obj)
                    )
                func(*args, **kwargs)
                sleep(int(absorbed_obj))

            return inside_inner

        return innerfunc
    else:
        raise AssertionError("es no décorateur..")


def version_validator() -> Optional[Union[str, Type]]:
    try:
        new_ver: str
        endpoint: str = "https://api.github.com/repos/justaus3r/tonoi/releases/latest"
        if not no_requests:
            new_ver = requests.get(endpoint).json().get("name")
        else:
            response: str = urlopen(endpoint).read().decode()
            response_json: Dict = json.loads(response)
            new_ver = response_json.get("name")
        if "v{}".format(Misc.util_version) != new_ver and new_ver is not None:
            return new_ver
        elif new_ver is None:
            return requests.exceptions.HTTPError
    except ConnectionError:
        return ConnectionError
    except HTTPError:

        class UrllibHTTPError(HTTPError):
            def __init__(self, msg=None) -> None:
                self.msg = msg
                super().__init__(code=404, msg=msg, hdrs=None, fp=None, url=endpoint)

        return UrllibHTTPError


def gen_player_name(seed: int) -> str:
    return "player_{}".format(seed + 1)
