from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path

from nbody_setup.conversion import IcFormat
from nbody_setup.cosmology import Cosmology


class Simulator:
    supported_ic_formats: list[IcFormat]

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

    @abstractmethod
    def __init__(self, args: Namespace):
        """
        Extract whatever command line options are needed to initialize the
        simulator class.
        """

    @abstractmethod
    def setup(
        self,
        target: Path,
        cosmology: Cosmology,
        seed: int,
        boxsize: float,
        N: int,
        ic_format: IcFormat,
    ):
        """
        Prepare a directory to have the simulation code run. The code itself
        should **not** be run here. `target` is a path to the directory where
        the code should run. All other parameters specify the cosmology and
        other parameters which may be necessary running the simulation. Here you
        can create parameter files and prepare any other files needed for the
        simulation code to use. The only requirements are:
        1. A bash script named run.sh exists. This is where the script to
            run the simulation code should go.
        Optional features which are recommended are:
        1. Don't run the simulation if it is already completed. This can help
            with resuming large array jobs.
        2. If possible, restart a simulation from a restart file (if
            applicable).
        3. Don't run the initial conditions script if ICs already exist.
        4. Pipe simulation stdout and stderr to log files.
        The script should NOT:
        1. Load any modules.
        """
