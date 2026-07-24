from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path


class InitialConditions:
    @classmethod
    @abstractmethod
    def args(cls, parser: ArgumentParser): ...

    @classmethod
    @abstractmethod
    def is_selected(cls, args: Namespace) -> bool: ...

    @abstractmethod
    def __init__(self, args: Namespace): ...

    @abstractmethod
    def setup(
        self,
        ic_dir: Path,
        Om: float,
        Ob: float,
        sigma8: float,
        ns: float,
        h: float,
        seed: int,
        boxsize: float,
        N: int,
    ): ...
