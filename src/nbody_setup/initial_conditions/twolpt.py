import os
from pathlib import Path

from sim_engine import Task

from nbody_setup.conversion import Format
from nbody_setup.cosmology import Cosmology
from nbody_setup.run_camb import camb_task


class TwoLPT:
    twolpt_path: Path
    glass_file: Path
    modules: list[str]

    def __init__(self, twolpt: Path, glass: Path, modules: list[str] | None = None):
        self.twolpt_path: Path = twolpt.resolve()
        self.glass_file: Path = glass.resolve()

        if not self.twolpt_path.exists():
            raise RuntimeError(f"{self.twolpt_path} does not exist")
        if not os.access(self.twolpt_path, os.X_OK):
            raise RuntimeError(f"{self.twolpt_path} is not executable")
        if not self.glass_file.is_file():
            raise RuntimeError(f"{self.glass_file} is not a file")
        self.modules = modules or []

    def setup(
        self,
        ic_dir: Path,
        cosmology: Cosmology,
        seed: int,
        boxsize: float,
        N: int,
        target_formats: list[Format],
    ) -> tuple[Format, list[Task]]:
        twolpt_params = {
            "Nmesh": N * 2,
            "Nsample": N,
            "Box": boxsize,
            "FileBase": "ics",
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

        camb = camb_task(
            ic_dir,
            Omega_b=cosmology.Ob,
            Omega_cdm=cosmology.Om - cosmology.Ob,
            h=cosmology.h,
            ns=cosmology.ns,
        )

        twolpt_task = Task(
            [str(self.twolpt_path), "2LPT.param"],
            1,
            8,
            [camb],
            cwd=ic_dir,
            modules=self.modules,
        )

        return Format.Gadget1, [camb, twolpt_task]
