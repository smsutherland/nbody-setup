import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pydoe
from astropy.table import Table
from tqdm import tqdm

from .cosmology import Cosmology
from .initial_conditions import InitialConditions
from .sim import Simulator


def setup_run(
    target: Path,
    cosmology: Cosmology,
    seed: int,
    boxsize: float,
    N: int,
    skip_confirmation: bool,
    no_slurm: bool,
    simulator: Simulator,
    ic: InitialConditions,
) -> int:
    if target.exists() and not target.is_dir():
        print(target, "exists, but is not a directory", file=sys.stderr)
        return 1

    print(f"This will create an N-body run in {target}")
    if target.exists() and next(target.iterdir(), None) is not None:
        print("    This directory exists and is not empty!")
    print("The run will have the following parameters")
    print(f"    Ω_m  = {cosmology.Om}")
    print(f"    Ω_b  = {cosmology.Ob} (for initial power spectrum)")
    print(f"    Ω_Λ  = {1 - cosmology.Om}")
    print(f"    H_0  = {cosmology.h * 100} km/s/Mpc")
    print(f"    σ_8  = {cosmology.sigma8}")
    print(f"    n_s  = {cosmology.ns}")
    print(f"    N    = {N} (total = {N * N * N})")
    print(f"    L    = {boxsize} kpc/h")
    print(f"    seed = {seed}")
    if not skip_confirmation and not confirm():
        return 1

    create_run(
        target,
        cosmology,
        seed,
        boxsize,
        N,
        simulator,
        ic,
        no_slurm,
    )
    return 0


def ensemble(
    basename: Path | None,
    table: Path,
    skip_confirmation: bool,
    no_slurm: bool,
    engine: str,
    simulator: Simulator,
    ic: InitialConditions,
) -> int:
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
        print(
            "ERROR: basename not specified and simname not provided and table",
            file=sys.stderr,
        )
        return 1

    for k, v in defaults.items():
        if k not in parameter_table.colnames:
            parameter_table[k] = np.full(len(parameter_table), v)

    if len(parameter_table) == 0:
        print("table", table, "is empty!", file=sys.stderr)
        return -1

    # convert to kpc
    parameter_table["boxsize"] *= 1000

    if basename is not None:
        print(
            f"This will create {len(parameter_table)} N-body run{'' if len(parameter_table) == 1 else 's'} in {basename.parent}"
        )
        if (
            basename.parent.exists()
            and next(basename.parent.iterdir(), None) is not None
        ):
            print("    This directory exists and is not empty!")
    else:
        print(
            f"This will create {len(parameter_table)} N-body run{'' if len(parameter_table) == 1 else 's'} in ."
        )
        if next(Path.cwd().iterdir(), None) is not None:
            print("    This directory exists and is not empty!")

    print("The runs will have the following parameters")
    parameters = [
        ("Om", "Ω_m", ""),
        ("Ob", "Ω_b", "(for initial power spectrum)"),
        (1 - parameter_table["Om"], "Ω_Λ", ""),
        (parameter_table["h"] * 100, "H_0", "km/s/Mpc"),
        ("sigma8", "σ_8", ""),
        ("ns", "n_s", ""),
        ("N", "N", ""),
        ("boxsize", "L", "kpc/h"),
        ("seed", "seed", ""),
    ]
    maxwidth = max(len(s) for _, s, _ in parameters)
    for name, display, post in parameters:
        s = "    {display:<{width}} ".format(display=display, width=maxwidth)
        if isinstance(name, str):
            values = parameter_table[name]
        else:
            values = name
        max_val = np.max(values)
        min_val = np.min(values)
        if max_val == min_val:
            s += f"= {min_val}"
        else:
            s += f"∈ [{min_val}, {max_val}]"

        if post:
            s += " " + post
        print(s)

    if not skip_confirmation and not confirm():
        return 1

    for i, row in enumerate(tqdm(parameter_table)):
        if basename is not None:
            target = basename.with_name(basename.name + f"_{i}")
        else:
            target = Path.cwd() / row["simname"]
        create_run(
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
            simulator,
            ic,
            no_slurm,
        )

    if engine == "disbatch":
        print(
            "WARNING: disbatch engine hasn't been tested yet! It almost certainly doesn't work!",
            file=sys.stderr,
        )
        with open("disbatch_tasks", "w") as f:
            f.write("#DISBATCH PREFIX cd \n")
            f.write("#DISBATCH SUFFIX ; bash job.sh &>> log\n")
            for i in range(len(parameter_table)):
                # TODO: Do we want to try and put the simnames in the table so we're not duplicating this work?
                if basename is not None:
                    target = basename.with_name(basename.name + f"_{i}")
                else:
                    target = Path.cwd() / row["simname"]
                f.write(str(target) + "\n")
        with open("job.sh", "w") as f:
            f.write("""#!/bin/bash
#SBATCH --job-name=Nbody
#SBATCH --output="slurm-%A.out"
#SBATCH --ntasks=16
#SBATCH --cpus-per-task=64
disBatch disbatch_tasks
""")

    elif engine == "array":
        with open("job.sh", "w") as f:
            f.write(f"""#!/bin/bash
#SBATCH --job-name=Nbody
#SBATCH --output="logs/slurm-%A_%a.out"
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1
#SBATCH --array=0-{len(parameter_table) - 1}

""")
            if basename is not None:
                f.write(f'cd "{basename}_${{SLURM_ARRAY_TASK_ID}}" || exit\n')
            else:
                f.write("names=(")
                for s in parameter_table["simname"]:
                    f.write(f"'{s}' ")
                f.write(")\n")
                f.write('cd "${names[${SLURM_ARRAY_TASK_ID}]}" || exit\n')
            f.write("bash job.sh\n")

    return 0


def generate(
    kind: str,
    number: int,
    parameters: str,
    seed: int,
    precision: int | None,
    cosmoseed: str | None,
    boxsize: float | None,
    N: int | None,
) -> int:

    # print header
    print("# This is all the columns suppored by nbody-setup ensemble.")
    print("# Columns may be safely removed.")
    print("# Removed columns will be replaced by a suitable default for all runs.")
    print("# Om      | float | Ω_m total matter density")
    print(
        "# Ob      | float | Ω_b baryonic matter density (only used for initial power spectra)"
    )
    print("# sigma8  | float | σ_8 8 Mpc/h matter clustering")
    print("# ns      | float | Spectral index of initial power spectra")
    print("# h       | float | Reducede hubble constant H_0 / (100 km/s/Mpc)")
    print("# seed    | int   | Random seed for initial conditions")
    print("# boxsize | float | Box side length in Mpc/h")
    print(
        "# N       | int   | cube root of the number of particles. Must be a multiple of 64"
    )

    if kind == "empty":
        items = ["Om", "Ob", "sigma8", "ns", "h", "seed", "boxsize", "N"]
        maxwidth = max(len(i) for i in items)
        print(
            " ".join("{i:<{width}}".format(i=i, width=maxwidth) for i in items).strip()
        )
        return 0

    if parameters == "-":
        lines = sys.stdin.readlines()
        table = Table.read(
            lines,
            names=["parameter", "low", "high", "logflag"],
            format="ascii.fast_no_header",
            delimiter=",",
            guess=False,
        )
    else:
        table = Table.read(
            parameters,
            names=["parameter", "low", "high", "logflag"],
            format="ascii.fast_no_header",
            delimiter=",",
            guess=False,
        )

    parameter_names = ["Om", "Ob", "sigma8", "ns", "h"]
    bad_parameters = [p for p in table["parameter"] if p not in parameter_names]
    if bad_parameters:
        print("Unknown parameters:", ", ".join(bad_parameters), file=sys.stderr)
        return 1

    if kind == "lh":
        unscaled = pydoe.lhs(len(table), number, criterion="maximin", seed=seed)
        new_table = Table(unscaled, names=table["parameter"])
    elif kind == "sobol":
        if number.bit_count() != 1:
            print(
                "Sobol' Sequences have to be made with a power-of-2 number of points.",
                file=sys.stderr,
            )
            return 1
        unscaled = pydoe.sobol_sequence(number, len(table), seed=seed, scramble=True)
        new_table = Table(unscaled, names=table["parameter"])

    for row in table:
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
        if cosmoseed.endswith(".."):
            starting_seed = int(cosmoseed[:-2])
            new_table["seed"] = np.arange(starting_seed, starting_seed + number)
        else:
            new_table["seed"] = int(cosmoseed)
    if boxsize is not None:
        new_table["boxsize"] = boxsize
    if N is not None:
        new_table["N"] = N

    new_table.write(
        sys.stdout,
        format="ascii.fixed_width",
        bookend=False,
        delimiter=None,
        formats={}
        if precision is None
        else {p: f"%.{precision}g" for p in table["parameter"]},
    )
    return 0


def create_run(
    target: Path,
    cosmology: Cosmology,
    seed: int,
    boxsize: float,
    N: int,
    simulator: Simulator,
    ic: InitialConditions,
    no_slurm: bool,
):
    target.mkdir(parents=True, exist_ok=True)

    use_slurm = (shutil.which("srun") is not None) and not no_slurm

    # Prepare ICs
    ic_dir = target / "ICs"
    ic_dir.mkdir(exist_ok=True)
    ic_format = ic.setup(
        ic_dir,
        cosmology,
        seed,
        boxsize,
        N,
        simulator.supported_ic_formats,
        ic.mpi_mode.srun_command() if use_slurm else ic.mpi_mode.mpi_command(),
    )

    if ic_format in simulator.supported_ic_formats:
        convert_to = ic_format
    else:
        convert_to = simulator.supported_ic_formats[0]

    simulator.setup(
        target,
        cosmology,
        seed,
        boxsize,
        N,
        convert_to,
        simulator.mpi_mode.srun_command()
        if use_slurm
        else simulator.mpi_mode.mpi_command(),
    )

    if "LOADEDMODULES" in os.environ:
        modules = "module --force purge\n" + "".join(
            "module load " + m + "\n" for m in os.environ["LOADEDMODULES"].split(":")
        )
    else:
        modules = ""

    with open(target / "job.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(modules)
        f.write("pushd ICs\n")
        f.write("bash ./make_ic.sh >> ic.log 2>> ic.err\n")
        # NOTE: We always convert regardless of whether ic_format == convert_to
        # or not because conversion will link files to the proper location.
        # The reason conversion has to do this is because the IC code puts its
        # results in its own directory and we have to move them somehow.
        # The ic code can't put ics in the simulation directory itself because
        # the unconverted and converted ICs might have the same name
        # ex. ic.hdf5 (gadget units) -> ic.hdf5 (swift units)
        # If there's a cleaner way to do this, I don't see it.
        f.write(f"{sys.argv[0]} convert {ic_format} ics {convert_to} ../ics\n")
        f.write("popd\n")
        f.write("bash ./run.sh >> sim.log 2>> sim.err\n")


def confirm():
    while True:
        print("Is this all correct? (Y/n) ", end="")
        try:
            answer = input()
        except EOFError:
            print("\nCanceling operation")
            return False

        if answer == "" or answer == "y" or answer == "Y":
            return True
        if answer == "n" or answer == "N":
            print("Canceling operation")
            return False
