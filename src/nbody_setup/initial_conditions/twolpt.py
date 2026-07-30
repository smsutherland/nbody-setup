import os
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

import numpy as np

from nbody_setup.conversion import IcFormat
from nbody_setup.cosmology import Cosmology
from nbody_setup.initial_conditions.ic_class import InitialConditions
from nbody_setup.run_camb import run_camb


class TwoLPT(InitialConditions):
    twolpt_path: Path
    glass_file: Path

    @classmethod
    def args(cls, parser: ArgumentParser):
        twolpt_path = shutil.which("2LPTic")

        parser.add_argument(
            "--2lpt",
            type=Path,
            default=twolpt_path,
            help="Path to 2lpt executable. May be omitted if 2LPTic is in PATH.",
            required=twolpt_path is None,
        )

        parser.add_argument(
            "--glass",
            type=Path,
            help="Path to glass file for generating initial conditions",
            required=True,
        )

    def __init__(self, args: Namespace):
        self.twolpt_path: Path = getattr(args, "2lpt").expanduser().resolve()
        self.glass_file: Path = args.glass.expanduser().resolve()

        if not self.twolpt_path.exists():
            raise RuntimeError(f"{self.twolpt_path} does not exist")
        if not os.access(self.twolpt_path, os.X_OK):
            raise RuntimeError(f"{self.twolpt_path} is not executable")
        if not self.glass_file.is_file():
            raise RuntimeError(f"{self.glass_file} is not a file")

    def setup(
        self,
        ic_dir: Path,
        cosmology: Cosmology,
        seed: int,
        boxsize: float,
        N: int,
        target_formats: list[IcFormat],
    ) -> IcFormat:

        twolpt_params = {
            "Nsample": N,
            "Box": boxsize,
            "FileBase": "ic",
            "OutputDir": "./",
            "GlassFile": self.glass_file,
            "GlassTileFac": N // 64,
            "Omega": cosmology.Om,
            "OmegaLambda": 1 - cosmology.Om,
            "OmegaBaryon": 0.0,
            "OmegaDM_2ndSpecies": 0.0,
            "HubbleParam": cosmology.h,
            "Redshift": 127,
            "Sigma8": cosmology.sigma8,
            "SphereMode": 0,
            "WhichSpectrum": 2,
            "FileWithInputSpectrum": "./Pk_m_z=0.000.txt",
            "InputSpectrum_UnitLength_in_cm": 3.085678e24,
            "ShapeGamma": 0.201,
            "PrimordialIndex": 1.0,
            "Phase_flip": 0,
            "RayleighSampling": 1,
            "Seed": seed,
            "NumFilesWrittenInParallel": 8,
            "UnitLength_in_cm": 3.085678e21,
            "UnitMass_in_g": 1.989e43,
            "UnitVelocity_in_cm_per_s": 1e5,
            "WDM_On": 0,
            "WDM_Vtherm_On": 0,
            "WDM_PartMass_in_kev": 10.0,
        }

        max_key_len = max(len(k) for k in twolpt_params)
        with open(ic_dir / "2LPT.param", "w") as f:
            for k, v in twolpt_params.items():
                f.write(k.ljust(max_key_len + 2))
                if isinstance(v, str):
                    f.write(v)
                else:
                    f.write(str(v))
                f.write("\n")

        pk, params = run_camb(
            Omega_b=cosmology.Ob,
            Omega_cdm=cosmology.Om - cosmology.Ob,
            h=cosmology.h,
            ns=cosmology.ns,
        )
        with open(ic_dir / "CAMB.params", "w") as f:
            f.write(str(params))
        np.savetxt(ic_dir / "Pk_m_z=0.000.txt", pk)

        with open(ic_dir / "make_ic.sh", "w") as f:
            f.write(_ic_script.format(twolpt=self.twolpt_path))

        return IcFormat.Gadget1


_twolpt_file = """Nmesh                           {Nmesh}
Nsample                         {N}
Box                             {box}
FileBase                        ic
OutputDir                       ./
GlassFile                       {glass}
GlassTileFac                    {tile}
Omega                           {Omega_m:.4f}
OmegaLambda                     {Omega_l:.4f}
OmegaBaryon                     0.0
OmegaDM_2ndSpecies              0.0
HubbleParam                     {h}
Redshift                        127
Sigma8                          {sigma_8:.4f}
SphereMode                      0
WhichSpectrum                   2
FileWithInputSpectrum           ./Pk_m_z=0.000.txt
InputSpectrum_UnitLength_in_cm  3.085678e24
ShapeGamma                      0.201
PrimordialIndex                 1.0

Phase_flip                      0
RayleighSampling                1
Seed                            {seed}

NumFilesWrittenInParallel       8
UnitLength_in_cm                3.085678e21
UnitMass_in_g                   1.989e43
UnitVelocity_in_cm_per_s        1e5

WDM_On                          0
WDM_Vtherm_On                   0
WDM_PartMass_in_kev             10.0
"""

_ic_script = """
#!/bin/bash
if [ ! -e ../ics.0 ]; then
    srun --ntasks=8 --cpus-per-task=1 {twolpt} 2LPT.param >> logIC
fi
"""
