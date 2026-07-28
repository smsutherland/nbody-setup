from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path


class InitialConditions:
    @classmethod
    @abstractmethod
    def args(cls, parser: ArgumentParser):
        """
        If the initial condition code requires any additional options to be
        provided, you may specify them here. Arguments can and should be set as
        "required" if they are needed for the initial condition code. This will
        not conflict with other initial condition codes, as only the selected
        code will have its arguments added to the parser.
        """
        ...

    @abstractmethod
    def __init__(self, args: Namespace):
        """
        Extract whatever command line options are needed to initialize the
        initial conditions class.
        """
        ...

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
    ):
        """
        Prepare a directory to have the initial conditions code run. The code
        itself should **not** be run here. `ic_dir` is a path to the directory
        where initial conditions should be made. All other parameters specify
        the cosmology and other parameters which may be necessary for generating
        initial conditions. Here you can prepare power spectra and create
        parameter files for the initial conditions code to use. The only
        requirements are:
        1. A bash script named make_ic.sh exists. This is where the script to
            run the initial conditions code should go.
        2. make_ic.sh should move, link, or otherwise make the generated initial
            conditions available in the parent directory for the simulation code
            to read.
        Optional features which are recommended are:
        1. Pipe stdout and stderr to log files.
        The script should NOT:
        1. Load any modules.
        """
        ...
