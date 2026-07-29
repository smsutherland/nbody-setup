from .gadget import Gadget
from .sim_class import Simulator

sim_options: dict[str, type[Simulator]] = {"gadget": Gadget}
