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
""" exceptions for tonoi """


class ProhibitedMove(Exception):
    """Raised on a Prohhibited Move"""


class EmptyRodError(Exception):
    """Raised when attempted to move disk from empty rod"""


class TerminalSizeError(Exception):
    """Raised when terminal size is below threashold"""


class ConfigParseError:
    """Raised on parsing a bad config"""

    class BadSectionDefinition(Exception):
        """Raised when a section is defined using a bad syntax"""

        def __init__(self, msg: str) -> None:
            self.msg: str = msg

        def __str__(self) -> str:
            return "\x1b[31m<BadSectionDefinition Error>: {}\x1b[m".format(self.msg)

    class BadBlockDefinition(Exception):
        """Raised when a block is defined using bad syntax"""

        def __init__(self, msg: str) -> None:
            self.msg: str = msg

        def __str__(self) -> str:
            return "\x1b[31m<BadBlockDefinition Error>: {}\x1b[m".format(self.msg)

    class SectionUndefinedError(Exception):
        """Raised when an inquired section is not defined"""

        def __init__(self, msg: str) -> None:
            self.msg: str = msg

        def __str__(self) -> str:
            return "\x1b[31m<SectionUndefinedError>: {}\x1b[m".format(self.msg)

    class BadAssignmentError(Exception):
        """Raised when an assignment operation is done poorly"""

        def __init__(self, msg: str) -> None:
            self.msg: str = msg

        def __str__(self) -> str:
            return "\x1b[31m<BadAssignmentError>: {}\x1b[m".format(self.msg)

    class BadKeyValuePair(Exception):
        def __init__(self, msg: str) -> None:
            self.msg: str = msg

        def __str__(self) -> None:
            return "\x1b[31m<BadKeyValuePair>: {}\x1b[m".format(self.msg)


class BadCommandError(Exception):
    """Raised upon receiving a bad command"""


class SubArgumentError(Exception):
    """Raised when given insufficient sub-arguments"""

    def __init__(self, responsible_callback: str) -> None:
        self.callback: str = responsible_callback


class DisksOverLimitError(Exception):
    def __init__(self, msg) -> None:
        self.msg = msg

    def __str__(self) -> str:
        return "\x1b[31m<DisksOverLimitError> {}\x1b[m".format(self.msg)
