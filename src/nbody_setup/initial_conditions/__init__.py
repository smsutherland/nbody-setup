from .ic_class import InitialConditions
import typing as T
from .twolpt import TwoLPT

ic_options: dict[str, T.Type[InitialConditions]] = {"2lpt": TwoLPT}
