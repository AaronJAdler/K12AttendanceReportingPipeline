"""Invented map positions for the fictional schools.

These points are made up. They sit in open farmland west of Sacramento so the map has
a real basemap to draw on, but no real school is at any of them.
"""

from typing import Final

# school_code -> (longitude, latitude, level)
SCHOOL_POINTS: Final[dict[str, tuple[float, float, str]]] = {
    "9000011": (-121.842, 38.662, "Elementary"),
    "9000012": (-121.801, 38.689, "Elementary"),
    "9000013": (-121.888, 38.628, "Elementary"),
    "9000014": (-121.764, 38.641, "Elementary"),
    "9000021": (-121.832, 38.701, "Middle"),
    "9000022": (-121.781, 38.611, "Middle"),
    "9000031": (-121.866, 38.684, "High"),
    "9000032": (-121.748, 38.672, "High"),
}
MAP_CENTER: Final = (-121.815, 38.656)
