from enum import Enum, auto


class MpiMode(Enum):
    NoMpi = auto()
    PerCore = auto()
    PerSocket = auto()
    PerNode = auto()

    def mpi_command(self) -> str:
        match self:
            case MpiMode.NoMpi:
                return ""
            case MpiMode.PerCore:
                return "mpirun"
            case MpiMode.PerSocket:
                return "mpirun --npersocket 1"
            case MpiMode.PerNode:
                return "mpirun --npernode 1"

    def srun_command(self) -> str:
        match self:
            case MpiMode.NoMpi:
                return ""
            case MpiMode.PerCore:
                return "srun --cpus-per-task=1 --cpu-bind=cores --kill-on-bad-exit=1"
            case MpiMode.PerSocket:
                return (
                    "srun --ntasks-per-socket=1 --cpu-bind=sockets --kill-on-bad-exit=1"
                )
            case MpiMode.PerNode:
                return "srun --ntasks-per-node=1 --cpu-bind=cores --kill-on-bad-exit=1"
