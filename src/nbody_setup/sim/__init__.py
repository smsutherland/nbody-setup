import typing as T

from .gadget import Gadget
from .sim_class import Simulator

sim_options: dict[str, T.Type[Simulator]] = {"gadget": Gadget}
