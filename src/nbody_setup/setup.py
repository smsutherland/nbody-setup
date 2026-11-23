import functools
import sys
import typing as T
from pathlib import Path

import numpy as np
import pydoe
from astropy.table import Table
from sim_engine import PyTask, Task

from nbody_setup.cosmology import Cosmology
from nbody_setup.initial_conditions import InitialConditions
from nbody_setup.sim import Simulator


def setup_run(
    target: Path,
    cosmology: Cosmology,
    boxsize: float,
    seed: int,
    N: int,
    ic: InitialConditions,
    simulator: Simulator,
) -> list[Task]:
    target.mkdir(parents=True, exist_ok=True)

    # Prepare ICs
    ic_dir = target / "ICs"
    ic_dir.mkdir(exist_ok=True)
    ic_format, ic_tasks = ic.setup(
        ic_dir,
        cosmology,
        seed,
        boxsize,
        N,
        simulator.supported_ic_formats,
    )
    if ic_format in simulator.supported_ic_formats:
        convert_to = ic_format
    else:
        convert_to = simulator.supported_ic_formats[0]
    convert_task = PyTask(
        functools.partial(
            ic_format.convert_to, convert_to, Path("ics"), Path("../ics")
        ),
        1,
        ic_tasks,
        cwd=ic_dir,
    )
    sim_tasks = simulator.setup(target, cosmology, seed, boxsize, N, convert_to)
    for t in sim_tasks:
        t.add_deps(ic_tasks)
        t.add_deps(convert_task)

    return [*ic_tasks, convert_task, *sim_tasks]


@T.overload
def ensemble(
    basename: Path | None,
    table: Path,
    simulator: Simulator,
    ic: InitialConditions,
    flatten: T.Literal[True],
) -> list[Task]: ...
@T.overload
def ensemble(
    basename: Path | None,
    table: Path,
    simulator: Simulator,
    ic: InitialConditions,
    flatten: T.Literal[False],
) -> list[list[Task]]: ...
def ensemble(
    basename: Path | None,
    table: Path,
    simulator: Simulator,
    ic: InitialConditions,
    flatten: bool = True,
) -> list[Task] | list[list[Task]]:
    parameter_table: Table = Table.read(table, format="ascii")
    defaults = {
        "Om": 0.3,
        "Ob": 0.049,
        "sigma8": 0.8,
        "ns": 0.9624,
        "h": 0.6711,
        "seed": 12,
        "boxsize": 25.0,
        "N": 256,
        "simname": "",
    }
    for k in parameter_table.colnames:
        if k not in defaults:
            print("Warning: unrecognized column:", k, file=sys.stderr)

    if basename is None and "simname" not in parameter_table.colnames:
        raise RuntimeError(
            "ERROR: basename not specified and simname not provided and table",
        )

    for k, v in defaults.items():
        if k not in parameter_table.colnames:
            parameter_table[k] = np.full(len(parameter_table), v)

    if len(parameter_table) == 0:
        raise RuntimeError("table", table, "is empty!")

    # convert to kpc
    parameter_table["boxsize"] *= 1000

    tasks = []
    for i, row in enumerate(parameter_table[:]):
        if basename is not None:
            target = basename.with_name(basename.name + f"_{i}")
        else:
            target = Path.cwd() / row["simname"]
        tasks.append(
            setup_run(
                target,
                Cosmology(
                    row["Om"],
                    row["Ob"],
                    row["sigma8"],
                    row["ns"],
                    row["h"],
                ),
                row["seed"],
                row["boxsize"],
                row["N"],
                ic,
                simulator,
            )
        )
    if flatten:
        return [t for ts in tasks for t in ts]
    else:
        return tasks


@T.overload
def generate(
    kind: T.Literal["empty"],
    to: Path,
) -> Table: ...
@T.overload
def generate(
    kind: T.Literal["lh", "sobol"],
    to: Path,
    number: int,
    parameter_table: Table,
    seed: int,
    precision: int | None,
    cosmoseed: int | T.Sequence[int],
    boxsize: float | None,
    N: int | None,
) -> Table: ...
def generate(
    kind: T.Literal["empty", "lh", "sobol"],
    to: Path,
    number: int | None = None,
    parameter_table: Table | None = None,
    seed: int | None = None,
    precision: int | None = None,
    cosmoseed: int | T.Sequence[int] | None = None,
    boxsize: float | None = None,
    N: int | None = None,
) -> Table:
    with open(to, "w") as f:
        # print header
        f.write("# This is all the columns suppored by nbody-setup ensemble.")
        f.write("# Columns may be safely removed.")
        f.write(
            "# Removed columns will be replaced by a suitable default for all runs."
        )
        f.write("# Om      | float | Ω_m total matter density")
        f.write(
            "# Ob      | float | Ω_b baryonic matter density (only used for initial power spectra)"
        )
        f.write("# sigma8  | float | σ_8 8 Mpc/h matter clustering")
        f.write("# ns      | float | Spectral index of initial power spectra")
        f.write("# h       | float | Reducede hubble constant H_0 / (100 km/s/Mpc)")
        f.write("# seed    | int   | Random seed for initial conditions")
        f.write("# boxsize | float | Box side length in Mpc/h")
        f.write(
            "# N       | int   | cube root of the number of particles. Must be a multiple of 64"
        )

        if kind == "empty":
            new_table = Table(
                names=["Om", "Ob", "sigma8", "ns", "h", "seed", "boxsize", "N"]
            )
        else:
            assert number is not None
            assert parameter_table is not None
            assert seed is not None
            parameter_names = ["Om", "Ob", "sigma8", "ns", "h"]
            bad_parameters = [
                p for p in parameter_table["parameter"] if p not in parameter_names
            ]
            if bad_parameters:
                raise ValueError("Unknown parameters:", ", ".join(bad_parameters))

            if kind == "lh":
                unscaled = pydoe.lhs(
                    len(parameter_table), number, criterion="maximin", seed=seed
                )
                new_table = Table(unscaled, names=parameter_table["parameter"])
            elif kind == "sobol":
                if number.bit_count() != 1:
                    raise ValueError(
                        "Sobol' Sequences have to be made with a power-of-2 number of points."
                    )
                unscaled = pydoe.sobol_sequence(
                    number, len(parameter_table), seed=seed, scramble=True
                )
                new_table = Table(unscaled, names=parameter_table["parameter"])

            for row in parameter_table:
                col = new_table[row["parameter"]]
                if row["logflag"]:
                    low = np.log(row["low"])
                    high = np.log(row["high"])
                    col *= high - low
                    col += low
                    col[:] = np.exp(col[:])
                else:
                    low = row["low"]
                    high = row["high"]
                    col *= high - low
                    col += low

            if cosmoseed is not None:
                new_table["seed"] = cosmoseed
            if boxsize is not None:
                new_table["boxsize"] = boxsize
            if N is not None:
                new_table["N"] = N

        new_table.write(
            f,
            format="ascii.fixed_width",
            bookend=False,
            delimiter=None,
            formats={}
            if precision is None or parameter_table is None
            else {p: f"%.{precision}g" for p in parameter_table["parameter"]},
        )
        return new_table
