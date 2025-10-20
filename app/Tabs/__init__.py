"""Tab modules for TAB Energy Dashboard."""

from .fuel_mix import render_fuel_mix_tab
from .price_map import render_price_map_tab
from .generation_map import render_generation_map_tab
from .ercot_queue import render_ercot_queue_tab

__all__ = [
    'render_fuel_mix_tab',
    'render_price_map_tab',
    'render_generation_map_tab',
    'render_ercot_queue_tab'
]
