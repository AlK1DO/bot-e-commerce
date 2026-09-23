from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.product_service import ProductService
from app.domain.product_filters import ProductFilters


router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)

product_service = ProductService()


@router.get("")
def get_products(
    categoria: Optional[str] = Query(default=None),
    marca: Optional[str] = Query(default=None),
    precio_min: Optional[float] = Query(
        default=None,
        ge=0
    ),
    precio_max: Optional[float] = Query(
        default=None,
        ge=0
    ),
    solo_stock: bool = Query(default=False),
    texto: Optional[str] = Query(default=None)
):
    filters = ProductFilters(
        categoria=categoria,
        marca=marca,
        precio_min=precio_min,
        precio_max=precio_max,
        solo_stock=solo_stock,
        texto=texto
    )

    return product_service.search_products(filters)


@router.get("/{product_id}")
def get_product(product_id: str):
    try:
        return product_service.get_product(product_id)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )