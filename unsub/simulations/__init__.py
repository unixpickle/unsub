from typing import Callable

from .base import Simulation
from .goldbelly import GoldbellySimulation
from .honeywell import HoneywellSimulation
from .single_step import SingleStepSimulation
from .static import StaticSimulation

Simulations: dict[str, Callable[[], Simulation]] = {
    "simple_1": lambda: StaticSimulation("simple_1.html"),
    "click_to_unsub": lambda: SingleStepSimulation("click_to_unsub.html"),
    "enter_email": lambda: SingleStepSimulation("enter_email.html"),
    "bryant_park": lambda: SingleStepSimulation("bryant_park.html"),
    "goldbelly": lambda: GoldbellySimulation(),
    "honeywell": lambda: HoneywellSimulation(),
}

__all__ = ["Simulation", "Simulations"]
