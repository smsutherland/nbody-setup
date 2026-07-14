import argparse
import os
import sys
from pathlib import Path

import numpy as np
from astropy.table import Table

from . import files
from .run_camb import run_camb


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    new_parser = subparsers.add_parser("new", help="Prepare a single N-body run")
    new_parser.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    new_parser.add_argument(
        "--Om",
        type=float,
        default=0.3,
        help="Ω_m matter density parameter",
    )
    new_parser.add_argument(
        "--Ob",
        type=float,
        default=0.049,
        help="Ω_b baryon density parameter. Only used for finding initial power spectrum.",
    )
    new_parser.add_argument(
        "--sigma8",
        type=float,
        default=0.8,
        help="σ_8 8 Mpc/h matter clustering",
    )
    new_parser.add_argument(
        "--ns",
        type=float,
        default=0.9624,
        help="n_s initial condition spectral index",
    )
    new_parser.add_argument(
        "--h",  # shortening this to -h would conflict with help
        type=float,
        default=0.6711,
        help="reduced hubble constant H_0/(100 km/s/Mpc)",
    )
    new_parser.add_argument(
        "--seed",
        type=int,
        default=12,
        help="Seed for initial conditions",
    )
    new_parser.add_argument(
        "--glass",
        type=Path,
        required=True,
        help="Path to glass file for generating initial conditions",
    )
    new_parser.add_argument(
        "--boxsize",
        type=float,
        default=25,
        help="Side length for the volume in Mpc/h",
    )
    new_parser.add_argument(
        "--N",  # keeping this long for consistency with --h
        type=int,
        default=256,
        help="Cube root of the number of particles in the volume. Must be a multiple of 64.",
    )
    new_parser.add_argument(
        "-y",
        "--no-confirm",
        action="store_true",
        help="Do not prompt for any confirmation",
    )
    new_parser.add_argument(
        "--2lpt",
        type=Path,
        required=True,
        help="Path to 2lpt executable",
    )
    new_parser.add_argument(
        "--gadget",
        type=Path,
        required=True,
        help="Path to gadget executable",
    )
    new_parser.set_defaults(
        func=lambda args: setup_run(
            args.target,
            args.Om,
            args.Ob,
            args.sigma8,
            args.ns,
            args.h,
            args.seed,
            args.boxsize * 1000,
            args.N,
            getattr(args, "2lpt"),
            args.gadget,
            args.glass,
            args.no_confirm,
        ),
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
        "--glass",
        type=Path,
        required=True,
        help="Path to glass file for generating initial conditions",
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
        "--2lpt",
        type=Path,
        required=True,
        help="Path to 2lpt executable",
    )
    ensemble_parser.add_argument(
        "--gadget",
        type=Path,
        required=True,
        help="Path to gadget executable",
    )
    ensemble_parser.add_argument(
        "--engine",
        choices=["none", "disbatch", "array"],
        default="none",
        help="Runner engine to run the ensemble",
    )
    ensemble_parser.set_defaults(
        func=lambda args: ensemble(
            args.basename,
            args.table,
            getattr(args, "2lpt"),
            args.gadget,
            args.glass,
            args.no_confirm,
            args.engine,
        ),
    )

    generate_parser = subparsers.add_parser(
        "generate-table",
        help="Prepare a table of parameters for ensemble",
        description="Prepares a table to be consumed by ensemble.\n"
        "Any column may be safely removed. A suitable default value will be used instead.",
        usage="%(prog)s [-h] > table.txt",
    )
    generate_parser.set_defaults(
        func=lambda _: generate(),
    )

    args = parser.parse_args()
    return args.func(args)


def setup_run(
    target: Path,
    Om: float,
    Ob: float,
    sigma8: float,
    ns: float,
    h: float,
    seed: int,
    boxsize: float,
    N: int,
    twolpt: Path,
    gadget: Path,
    glass: Path,
    skip_confirmation: bool,
) -> int:
    bad = False
    if not os.access(twolpt, os.X_OK):
        bad = True
        print(twolpt, "is not executable", file=sys.stderr)
    if not os.access(gadget, os.X_OK):
        bad = True
        print(gadget, "is not executable", file=sys.stderr)
    if target.exists() and not target.is_dir():
        print(target, "exists, but is not a directory", file=sys.stderr)
        bad = True
    if not glass.is_file():
        print(glass, "is not a file", file=sys.stderr)
        bad = True
    if bad:
        return 1

    print(f"This will create an N-body run in {target}")
    if target.exists() and next(target.iterdir(), None) is not None:
        print("    This directory exists and is not empty!")
    print("The run will have the following parameters")
    print(f"    Ω_m  = {Om}")
    print(f"    Ω_b  = {Ob} (for initial power spectrum)")
    print(f"    Ω_Λ  = {1 - Om}")
    print(f"    H_0  = {h * 100} km/s/Mpc")
    print(f"    σ_8  = {sigma8}")
    print(f"    n_s  = {ns}")
    print(f"    N    = {N} (total = {N * N * N})")
    print(f"    L    = {boxsize} kpc/h")
    print(f"    seed = {seed}")
    if not skip_confirmation:
        if not confirm():
            return 1

    twolpt = twolpt.resolve()
    gadget = gadget.resolve()
    glass = glass.resolve()

    create_run(
        target,
        Om,
        Ob,
        sigma8,
        ns,
        h,
        seed,
        boxsize,
        N,
        twolpt,
        gadget,
        glass,
    )


def ensemble(
    basename: Path,
    table: Path,
    twolpt: Path,
    gadget: Path,
    glass: Path,
    skip_confirmation: bool,
    engine: str,
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
    for k in parameter_table.keys():
        if k not in defaults:
            print("Warning: unrecognized column:", k, file=sys.stderr)

    for k, v in defaults.items():
        if k not in parameter_table.colnames:
            parameter_table[k] = np.full(len(parameter_table), v)

    if len(parameter_table) == 0:
        print("table", table, "is empty!", file=sys.stderr)
        return -1

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

    if not skip_confirmation:
        if not confirm():
            return 1

    for i, row in enumerate(parameter_table):
        target = basename.with_name(basename.name + f"_{i}")
        create_run(
            target,
            row["Om"],
            row["Ob"],
            row["sigma8"],
            row["ns"],
            row["h"],
            row["seed"],
            row["boxsize"],
            row["N"],
            twolpt,
            gadget,
            glass,
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
    Om: float,
    Ob: float,
    sigma8: float,
    ns: float,
    h: float,
    seed: int,
    boxsize: float,
    N: int,
    twolpt: Path,
    gadget: Path,
    glass: Path,
):
    target.mkdir(parents=True, exist_ok=True)

    # Prepare ICs
    ic_dir = target / "ICs"
    ic_dir.mkdir(exist_ok=True)
    twolpt_params = files.twolpt(h, Om, 1 - Om, seed, sigma8, glass, N, boxsize)
    with open(ic_dir / "2LPT.param", "w") as f:
        f.write(twolpt_params)

    pk, params = run_camb(Omega_b=Ob, Omega_cdm=Om - Ob, h=h, ns=ns)
    with open(ic_dir / "CAMB.params", "w") as f:
        f.write(str(params))
    np.savetxt(ic_dir / "Pk_m_z=0.000.txt", pk)

    gadget_params = files.gadget(h, Om, 1 - Om, boxsize)
    with open(target / "G3.param", "w") as f:
        f.write(gadget_params)
    with open(target / "output_list.txt", "w") as f:
        f.write(files.output_times)
    jobscript = files.jobscript(
        twolpt,
        91,  # TODO: better handling of output times
        gadget,
    )
    with open(target / "job.sh", "w") as f:
        f.write(jobscript)


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
