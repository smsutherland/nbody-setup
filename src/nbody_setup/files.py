import os
from pathlib import Path

__all__ = ["gadget", "output_times", "jobscript"]


def gadget(
    h: float,
    Om: float,
    Ol: float,
    box: float,
):
    return _gadget_file.format(Om=Om, Ol=Ol, h=h, boxsize=box)


def jobscript(num_snaps: int, gadget: Path):
    if "LOADEDMODULES" in os.environ:
        modules = "module --force purge\n" + "".join(
            "module load " + m + "\n" for m in os.environ["LOADEDMODULES"].split(":")
        )
    else:
        modules = ""
    return _job_file.format(
        modules=modules,
        last_snap=num_snaps - 1,
        gadget=gadget,
    )


_gadget_file = """InitCondFile              ./ICs/ics
OutputDir                 ./
OutputListFilename        ./output_list.txt
NumFilesPerSnapshot       1
NumFilesWrittenInParallel 1
CpuTimeBetRestartFile     10800.0
TimeLimitCPU              10000000
ICFormat                  1
SnapFormat                3
TimeBegin                 0.0078125
TimeMax                   1.00
Omega0                    {Om:.6f}
OmegaLambda               {Ol:.6f}
OmegaBaryon               0.0000
HubbleParam               {h:.6f}
BoxSize                   {boxsize}

SofteningGas              0.0
SofteningHalo             0.5
SofteningDisk             0.0
SofteningBulge            0.0
SofteningStars            0.0
SofteningBndry            0.0
SofteningGasMaxPhys       0.0
SofteningHaloMaxPhys      0.5
SofteningDiskMaxPhys      0.0
SofteningBulgeMaxPhys     0.0
SofteningStarsMaxPhys     0.0
SofteningBndryMaxPhys     0.0

PartAllocFactor           2.5
MaxMemSize                15500
BufferSize                300
CoolingOn                 0
StarformationOn           0

TypeOfTimestepCriterion   0
ErrTolIntAccuracy         0.025
MaxSizeTimestep           0.005
MinSizeTimestep           0.0

ErrTolTheta               0.5
TypeOfOpeningCriterion    1
ErrTolForceAcc            0.005
TreeDomainUpdateFrequency 0.01

DesNumNgb                 33
MaxNumNgbDeviation        2
ArtBulkViscConst          1.0
InitGasTemp               273.0
MinGasTemp                10.0
CourantFac                0.15
ComovingIntegrationOn     1
PeriodicBoundariesOn      1
MinGasHsmlFractional      0.1
OutputListOn              1
TimeBetSnapshot           1.
TimeOfFirstSnapshot       1.
TimeBetStatistics         0.5
MaxRMSDisplacementFac     0.25
EnergyFile                energy.txt
InfoFile                  info.txt
TimingsFile               timings.txt
CpuFile                   cpu.txt
TimebinFile               Timebin.txt
SnapshotFileBase          snap
RestartFile               restart
ResubmitOn                0
ResubmitCommand           /dev/null
UnitLength_in_cm          3.085678e21
UnitMass_in_g             1.989e43
UnitVelocity_in_cm_per_s  1e5
GravityConstantInternal   0
"""

output_times = """# Scale Factor
0.0625423207
0.0697435265
0.0770403364
0.0819350757
0.0871408012
0.0935597132
0.0999766069
0.10532572
0.110961031
0.116345263
0.121414094
0.126703761
0.132223883
0.137332233
0.142637941
0.14814863
0.153872219
0.160575993
0.166779702
0.172404243
0.178218468
0.183357906
0.188645553
0.194085686
0.1996827
0.20544112
0.2113656
0.216432969
0.222674431
0.229095883
0.235702516
0.24249967
0.249492839
0.256687676
0.262841616
0.269143094
0.275595646
0.282202894
0.288968547
0.295896403
0.30299035
0.31025437
0.317692541
0.325309039
0.333108137
0.341094214
0.349271753
0.357645343
0.366219686
0.374999594
0.383989995
0.393195935
0.402622583
0.412275229
0.422159292
0.434333459
0.442643994
0.455408895
0.466327063
0.477506988
0.488954945
0.50067736
0.512680813
0.524972043
0.537557948
0.550445592
0.56364221
0.57715521
0.590992177
0.605160876
0.619669262
0.634525479
0.649737864
0.665314958
0.681265504
0.697598455
0.714322979
0.731448464
0.748984523
0.770583627
0.789057929
0.807975142
0.827345884
0.847181028
0.867491709
0.888289327
0.909585556
0.93139235
0.953721949
0.976586888
1.0
"""

_job_file = """#!/bin/bash
#SBATCH --job-name=Nbody
#SBATCH --output="slurm-%A.out"
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1

set -e

{modules}

# IC generation
pushd ICs
bash ./make_ic.sh
popd

# Gadget
# Has the simulation already run?
if [ ! -e snap_{last_snap:03d}.hdf5 ]; then
    # It hasn't! Let's run it!

    echo job id: $SLURM_JOBID | tee -a gadget.log
    if [[ $SLURM_ARRAY_TASK_ID ]]; then 
        echo job array id: $SLURM_ARRAY_TASK_ID | tee -a gadget.log
    fi

    if [ -d restartfiles ]; then
        # restart
        restart=1
    fi

    srun --ntasks=$SLURM_CPUS_ON_NODE --cpus-per-task=1 --cpu_bind=cores --kill-on-bad-exit=1 {gadget} G3.param $restart >> gadget.log 2>> gadget.err
fi
"""
