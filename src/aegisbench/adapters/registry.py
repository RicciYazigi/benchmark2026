# -*- coding: utf-8 -*-
"""
Registro y carga dinámica de adaptadores para AegisBench.
Soporta adaptadores pre-registrados y la carga de clases arbitrarias
a través del formato de ruta de módulo python 'modulo.submodulo:NombreClase'.
"""

import importlib
from typing import Any, Dict, Type

from aegisbench.interfaces.v1 import TargetSystem

# Diccionario interno de adaptadores registrados por nombre
_REGISTRY: Dict[str, Type[TargetSystem]] = {}


def register_adapter(name: str):
    """
    Decorador para registrar una clase de adaptador.
    """

    def decorator(cls: Type[TargetSystem]):
        if not issubclass(cls, TargetSystem):
            raise TypeError(f"La clase {cls.__name__} debe heredar de TargetSystem")
        _REGISTRY[name.lower()] = cls
        return cls

    return decorator


def load_adapter(identifier: str, **kwargs: Any) -> TargetSystem:
    """
    Carga e instancia un adaptador por su identificador.
    Soporta:
      - Nombres registrados (ej. 'dummy').
      - Rutas de clase dinámicas en formato 'modulo:Clase' o 'modulo.submodulo:Clase'.
    """
    identifier_clean = identifier.strip()

    # Si está registrado por nombre
    if identifier_clean.lower() in _REGISTRY:
        adapter_cls = _REGISTRY[identifier_clean.lower()]
        return adapter_cls(**kwargs)

    # Intentar cargar dinámicamente si contiene ':'
    if ":" in identifier_clean:
        try:
            module_name, class_name = identifier_clean.split(":", 1)
            module = importlib.import_module(module_name)
            adapter_cls = getattr(module, class_name)
            if not issubclass(adapter_cls, TargetSystem):
                raise TypeError(
                    f"La clase cargada {class_name} no hereda de TargetSystem"
                )
            return adapter_cls(**kwargs)
        except (ImportError, AttributeError, ValueError) as e:
            raise ImportError(
                f"No se pudo cargar el adaptador dinámico '{identifier_clean}': {e}"
            ) from e

    raise ValueError(
        f"Adaptador '{identifier_clean}' no encontrado. "
        f"Asegúrese de que esté registrado o use el formato 'modulo:Clase'."
    )


# Importar y registrar adaptadores integrados
from aegisbench.adapters.dummy import DummyAdapter  # noqa: E402

register_adapter("dummy")(DummyAdapter)
