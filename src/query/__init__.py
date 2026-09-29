"""
Open-World Query Package — StandSpec AI (Phase P1-E)
Defines strict query contracts ensuring the engine can ingest any arbitrary
natural-language procurement query without dependency on benchmark artifacts.
"""

from src.query.open_world_contract import OpenWorldQuery

__all__ = ["OpenWorldQuery"]
