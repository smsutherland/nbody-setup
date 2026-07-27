from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path


class Simulator:
    @classmethod
    @abstractmethod
    def args(cls, parser: ArgumentParser): ...

    @abstractmethod
    def __init__(self, args: Namespace): ...

    @abstractmethod
    def setup(
        self,
        target: Path,
        Om: float,
        Ob: float,
        sigma8: float,
        ns: float,
        h: float,
        seed: int,
        boxsize: float,
        N: int,
    ): ...
