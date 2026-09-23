from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductFilters:
    categoria: Optional[str] = None
    marca: Optional[str] = None
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None
    solo_stock: bool = False
    texto: Optional[str] = None