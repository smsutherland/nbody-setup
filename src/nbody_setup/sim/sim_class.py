from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path


class Simulator:
    @classmethod
    @abstractmethod
    def args(cls, parser: ArgumentParser):
        """
        If the simulation code requires any additional options to be provided,
        you may specify them here. Arguments can and should be set as "required"
        if they are needed for the initial condition code. This will not
        conflict with other simulation codes, as only the selected code will
        have its arguments added to the parser.
        """
        ...

    @abstractmethod
    def __init__(self, args: Namespace):
        """
        Extract whatever command line options are needed to initialize the
        simulator class.
        """
        ...

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
    ):
        """
        Prepare a directory to have the simulation code run. The code itself
        should **not** be run here. `target` is a path to the directory where
        the code should run. All other parameters specify the cosmology and
        other parameters which may be necessary running the simulation. Here you
        can create parameter files and prepare any other files needed for the
        simulation code to use. The only requirements are:
        1. A bash script named job.sh exists. This is where the script to
            run the simulation code should go.
        2. The bash script should run the initial conditions script make_ic.sh
            in the initial conditions directory "ICs/".
        Optional features which are recommended are:
        1. Don't run the simulation if it is already completed. This can help
            with resuming large array jobs.
        2. If possible, restart a simulation from a restart file (if
            applicable).
        3. Don't run the initial conditions script if ICs already exist.
        4. Pipe simulation stdout and stderr to log files.
        """
        ...
