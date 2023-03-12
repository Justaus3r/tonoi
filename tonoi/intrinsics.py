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
""" All intrinsics of tower of hanoi """

import random
from typing import List, Union, Dict, Optional
from .exceptions import ProhibitedMove, EmptyRodError


class DiskSizeGenerator:
    disk_size_cache: List[int] = []

    def __call__(self, upper_disk_limit) -> int:
        rand_no: int
        while True:
            rand_no = random.randint(1, upper_disk_limit)
            if rand_no not in DiskSizeGenerator.disk_size_cache:
                DiskSizeGenerator.disk_size_cache.append(rand_no)
                break
            DiskSizeGenerator.disk_size_cache.append(rand_no)
        return rand_no


class Disk:
    def __init__(self, size: int) -> None:
        assert isinstance(size, int)
        self.size: int = size

    def __repr__(self) -> str:
        return "(Disk object, size={})".format(self.size)

    def __str__(self) -> str:
        return str(self.size)

    def __lt__(self, other: Union[int, "Disk"]) -> bool:
        assert isinstance(other, (int, Disk))
        return self.size < other

    def __le__(self, other: Union[int, "Disk"]) -> bool:
        assert isinstance(other, (int, Disk))
        return self.size <= other

    def __gt__(self, other: Union[int, "Disk"]) -> bool:
        assert isinstance(other, (int, Disk))
        return self.size > other

    def __ge__(self, other: Union[int, "Disk"]) -> bool:
        assert isinstance(other, (int, Disk))
        return self.size >= other

    def __eq__(self, other: Union[int, "Disk"]) -> bool:
        assert isinstance(other, (int, Disk))
        return self.size == other

    def __ne__(self, other: Union[int, "Disk"]) -> bool:
        assert isinstance(other, (int, Disk))
        return self.size != other


class Rod(List):
    def __init__(self, **kwargs) -> None:
        self.is_primary: bool = kwargs.get("primary_rod")
        Rod.rod_capacity: int = kwargs.get("rod_capacity") or Rod.rod_capacity
        self.__items: List[Disk] = sorted(
            [
                Disk(size=DiskSizeGenerator()(Rod.rod_capacity + 1))
                for _ in range(Rod.rod_capacity)
            ]
            if self.is_primary
            else [],
            reverse=True,
        )
        super().extend(self.__items)

    def append(self, item: Disk, src_rod: Optional["Rod"] = None) -> None:
        try:
            if item > self[-1]:
                # if an illegal move was attempted, push
                # the src element back to the rod, from
                # where it was popped
                src_rod.append(item)
                raise ProhibitedMove
        except IndexError:
            # means that the dest rod is empty
            pass
        super().append(item)


class RodHandler:
    def __init__(self, rod_capacity: int) -> None:
        self.rod_capacity: int = rod_capacity
        self.primary_rod: Rod = Rod(primary_rod=True, rod_capacity=rod_capacity)
        self.secondary_rod: Rod = Rod()
        self.tertiary_rod: Rod = Rod()
        self.int_to_obj: Dict[int, Rod] = {
            1: self.primary_rod,
            2: self.secondary_rod,
            3: self.tertiary_rod,
        }

    def move_disk(self, source_rod: int, dest_rod: int) -> Optional[bool]:
        assert source_rod in (1, 2, 3) and dest_rod in (
            1,
            2,
            3,
        ), "source_rod/dest_rod must be >=1&&<=3"
        source_rod: Rod = self.int_to_obj.get(source_rod)
        dest_rod: Rod = self.int_to_obj.get(dest_rod)
        try:
            disk: Disk = source_rod.pop()
        except IndexError:
            raise EmptyRodError
        dest_rod.append(disk, source_rod)
        if len(self.tertiary_rod) == self.rod_capacity:
            return True
