import argparse
import os
import sys
from pathlib import Path

import numpy as np

from . import files
from .run_camb import run_camb


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)
    setup_parser = subparsers.add_parser("new", help="Prepare a single N-body run.")
    setup_parser.add_argument("target", nargs="?", type=Path, default=Path.cwd())
    setup_parser.add_argument(
        "--Om",
        type=float,
        default=0.3,
        help="Ω_m matter density parameter",
    )
    setup_parser.add_argument(
        "--Ob",
        type=float,
        default=0.049,
        help="Ω_b baryon density parameter. Only used for finding initial power spectrum.",
    )
    setup_parser.add_argument(
        "--sigma8",
        type=float,
        default=0.8,
        help="σ_8 8 Mpc/h matter clustering",
    )
    setup_parser.add_argument(
        "--ns",
        type=float,
        default=0.9624,
        help="n_s initial condition spectral index",
    )
    setup_parser.add_argument(
        "--h",  # shortening this to -h would conflict with help
        type=float,
        default=0.6711,
        help="reduced hubble constant H_0/(100 km/s/Mpc)",
    )
    setup_parser.add_argument(
        "--seed",
        type=int,
        default=12,
        help="Seed for initial conditions",
    )
    setup_parser.add_argument(
        "--glass",
        type=Path,
        required=True,
        help="Path to glass file for generating initial conditions",
    )
    setup_parser.add_argument(
        "--boxsize",
        type=float,
        default=25,
        help="Side length for the volume in Mpc/h",
    )
    setup_parser.add_argument(
        "--N",  # keeping this long for consistency with --h
        type=int,
        default=256,
        help="Cube root of the number of particles in the volume. Must be a multiple of 64.",
    )
    setup_parser.add_argument(
        "-y",
        "--no-confirm",
        action="store_true",
        help="Do not prompt for any confirmation",
    )
    setup_parser.add_argument(
        "--2lpt",
        type=Path,
        required=True,
        help="Path to 2lpt executable",
    )
    setup_parser.add_argument(
        "--gadget",
        type=Path,
        required=True,
        help="Path to gadget executable",
    )
    setup_parser.set_defaults(
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

    args = parser.parse_args()
    args.func(args)


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
) -> None:
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
        return

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
    print(f"    L    = {boxsize} kpc")
    print(f"    seed = {seed}")
    if not skip_confirmation:
        while True:
            print("Is this all correct? (Y/n) ", end="")
            try:
                answer = input()
            except EOFError:
                print("\nCanceling operation")
                return

            if answer == "" or answer == "y" or answer == "Y":
                break
            if answer == "n" or answer == "N":
                print("Canceling operation")
                return

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
