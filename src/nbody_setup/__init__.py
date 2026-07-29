import argparse
import os
import sys
from pathlib import Path

import numpy as np
from astropy.table import Table
from tqdm import tqdm

from nbody_setup.conversion import IcFormat

from .cosmology import Cosmology
from .initial_conditions import ic_options
from .initial_conditions.ic_class import InitialConditions
from .sim import sim_options
from .sim.sim_class import Simulator


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True, dest="command")

    new_parser = subparsers.add_parser("new", help="Prepare a single N-body run")
    new_parser.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    Cosmology.args(new_parser)
    new_parser.add_argument(
        "--seed",
        type=int,
        default=12,
        help="Seed for initial conditions",
    )
    new_parser.add_argument(
        "--boxsize",
        type=float,
        default=25,
        help="Side length for the volume in Mpc/h",
        metavar="L",
    )
    new_parser.add_argument(
        "--N",  # keeping this long for consistency with --h
        type=int,
        default=256,
        help="Cube root of the number of particles in the volume.",
    )
    new_parser.add_argument(
        "-y",
        "--no-confirm",
        action="store_true",
        help="Do not prompt for any confirmation",
    )
    new_parser.set_defaults(
        func=lambda args: setup_run(
            args.target,
            Cosmology(args.Om, args.Ob, args.sigma8, args.ns, args.h),
            args.seed,
            args.boxsize,
            args.N,
            args.no_confirm,
            simulator=sim_options[args.sim](args),
            ic=ic_options[args.ics](args),
        ),
    )
    new_parser.add_argument(
        "--ics",
        choices=ic_options.keys(),
        required=True,
        help="Which IC generation to use",
    )
    new_parser.add_argument(
        "--sim",
        choices=sim_options.keys(),
        required=True,
        help="Which simulation code to use",
    )

    ensemble_parser = subparsers.add_parser(
        "ensemble",
        help="Prepare an ensemble of N-body runs",
    )
    ensemble_parser.add_argument(
        "basename",
        type=Path,
        help="Base name for simulation directories. ex. LH -> LH_0, LH_1, …",
    )
    ensemble_parser.add_argument(
        "table",
        type=Path,
        help="Table with parameters for each simulation. See generate-table",
    )
    ensemble_parser.add_argument(
        "--boxsize",
        type=float,
        default=25,
        help="Side length for the volume in Mpc/h",
    )
    ensemble_parser.add_argument(
        "--N",  # keeping this long for consistency with --h
        type=int,
        default=256,
        help="Cube root of the number of particles in the volume. Must be a multiple of 64.",
    )
    ensemble_parser.add_argument(
        "-y",
        "--no-confirm",
        action="store_true",
        help="Do not prompt for any confirmation",
    )
    ensemble_parser.add_argument(
        "--engine",
        choices=["none", "disbatch", "array"],
        default="none",
        help="Runner engine to run the ensemble",
    )
    ensemble_parser.add_argument(
        "--sim",
        choices=sim_options.keys(),
        required=True,
        help="Which simulation code to use",
    )
    ensemble_parser.set_defaults(
        func=lambda args: ensemble(
            args.basename,
            args.table,
            args.no_confirm,
            args.engine,
            simulator=sim_options[args.sim](args),
            ic=ic_options[args.ics](args),
        ),
    )

    ensemble_parser.add_argument(
        "--ics",
        choices=ic_options.keys(),
        required=True,
        help="Which IC generation to use",
    )

    generate_parser = subparsers.add_parser(
        "generate-table",
        help="Prepare a table of parameters for ensemble",
        description="Prepares a table to be consumed by ensemble.\n"
        "Any column may be safely removed. A suitable default value will be used instead.",
        usage="%(prog)s [-h] > table.txt",
    )
    generate_parser.set_defaults(func=lambda _: generate())

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert between different initial condition formats",
    )
    convert_parser.add_argument(
        "input_format",
        type=IcFormat,
        choices=[x.value for x in IcFormat],
        help="Format the ICs are currently in",
    )
    convert_parser.add_argument("input_name", type=Path, help="Path to ICs")
    convert_parser.add_argument(
        "output_format",
        type=IcFormat,
        choices=[x.value for x in IcFormat],
        help="Format you want the ICs to be changed to",
    )
    convert_parser.add_argument(
        "output_name",
        type=Path,
        help="Path to put converted ICs at",
    )
    convert_parser.set_defaults(
        func=lambda args: args.input_format.convert_to(
            args.output_format,
            args.input_name,
            args.output_name,
        )
    )

    args, _ = parser.parse_known_args()
    if args.command == "new":
        ic_options[args.ics].args(new_parser)
        sim_options[args.sim].args(new_parser)
    if args.command == "ensemble":
        ic_options[args.ics].args(ensemble_parser)
        sim_options[args.sim].args(ensemble_parser)

    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1


def setup_run(
    target: Path,
    cosmology: Cosmology,
    seed: int,
    boxsize: float,
    N: int,
    skip_confirmation: bool,
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
    )
    return 0


def ensemble(
    basename: Path,
    table: Path,
    skip_confirmation: bool,
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
    }
    for k in parameter_table:
        if k not in defaults:
            print("Warning: unrecognized column:", k, file=sys.stderr)

    for k, v in defaults.items():
        if k not in parameter_table.colnames:
            parameter_table[k] = np.full(len(parameter_table), v)

    if len(parameter_table) == 0:
        print("table", table, "is empty!", file=sys.stderr)
        return -1

    # convert to kpc
    parameter_table["boxsize"] *= 1000

    print(
        f"This will create {len(parameter_table)} N-body run{'' if len(parameter_table) == 1 else 's'} in {basename.parent}"
    )
    if basename.parent.exists() and next(basename.parent.iterdir(), None) is not None:
        print("    This directory exists and is not empty!")
    print("The run will have the following parameters")
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
        target = basename.with_name(basename.name + f"_{i}")
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
                target = basename.with_name(basename.name + f"_{i}").resolve()
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

cd {basename}_${{SLURM_ARRAY_TASK_ID}}
bash job.sh
""")

    return 0


def generate() -> int:
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
    items = ["Om", "Ob", "sigma8", "ns", "h", "seed", "boxsize", "N"]
    maxwidth = max(len(i) for i in items)
    print(" ".join("{i:<{width}}".format(i=i, width=maxwidth) for i in items).strip())
    return 0


def create_run(
    target: Path,
    cosmology: Cosmology,
    seed: int,
    boxsize: float,
    N: int,
    simulator: Simulator,
    ic: InitialConditions,
):
    target.mkdir(parents=True, exist_ok=True)

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
    )

    if ic_format in simulator.supported_ic_formats:
        convert_to = ic_format
    else:
        convert_to = simulator.supported_ic_formats[0]

    simulator.setup(target, cosmology, seed, boxsize, N, convert_to)

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
        f.write(f"{sys.argv[0]} convert {ic_format} ic {convert_to} ../ic\n")
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
