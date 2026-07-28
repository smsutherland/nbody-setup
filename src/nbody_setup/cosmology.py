from argparse import ArgumentParser
from dataclasses import dataclass


@dataclass(slots=True)
class Cosmology:
    Om: float
    Ob: float
    sigma8: float
    ns: float
    h: float

    @classmethod
    def args(cls, parser: ArgumentParser):
        group = parser.add_argument_group("Cosmology")
        group.add_argument(
            "--Om",
            type=float,
            default=0.3,
            help="Ω_m matter density parameter",
            metavar="Ω_m",
        )
        group.add_argument(
            "--Ob",
            type=float,
            default=0.049,
            help="Ω_b baryon density parameter. Only used for finding initial power spectrum.",
            metavar="Ω_b",
        )
        group.add_argument(
            "--sigma8",
            type=float,
            default=0.8,
            help="σ_8 8 Mpc/h matter clustering",
            metavar="σ_8",
        )
        group.add_argument(
            "--ns",
            type=float,
            default=0.9624,
            help="n_s initial condition spectral index",
            metavar="n_s",
        )
        group.add_argument(
            "--h",  # shortening this to -h would conflict with help
            type=float,
            default=0.6711,
            help="reduced hubble constant H_0/(100 km/s/Mpc)",
            metavar="h",
        )
