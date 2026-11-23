import functools
from pathlib import Path

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
