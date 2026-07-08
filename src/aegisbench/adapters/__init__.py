# -*- coding: utf-8 -*-
from aegisbench.adapters.dummy import DummyAdapter
from aegisbench.adapters.registry import load_adapter, register_adapter

__all__ = [
    "register_adapter",
    "load_adapter",
    "DummyAdapter",
]
