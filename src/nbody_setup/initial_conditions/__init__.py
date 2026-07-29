from .ic_class import InitialConditions
from .twolpt import TwoLPT

ic_options: dict[str, type[InitialConditions]] = {"2lpt": TwoLPT}
