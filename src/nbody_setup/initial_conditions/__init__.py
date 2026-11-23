import typing as T
from pathlib import Path

from sim_engine import Task

from nbody_setup.conversion import IcFormat
from nbody_setup.cosmology import Cosmology

from .twolpt import TwoLPT


class InitialConditions(T.Protocol):
    def setup(
        self,
        ic_dir: Path,
        cosmology: Cosmology,
        seed: int,
        boxsize: float,
        N: int,
        target_formats: list[IcFormat],
    ) -> tuple[IcFormat, list[Task]]:
        """
        Prepare a directory to have the initial conditions code run. The code
        itself should **not** be run here. `ic_dir` is a path to the directory
        where initial conditions should be made. `target_formats` gives a list
        of file formats supported by the selected simulator. The IC code is
        *not* required to ouput an ic file in one of the formats given. However,
        if the IC code is capable of doing so, it ought to. The format which the
        IC code produced should be returned. All other parameters specify the
        cosmology and other parameters which may be necessary for generating
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

__all__ = ["InitialConditions", "TwoLPT"]
