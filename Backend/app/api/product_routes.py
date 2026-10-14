import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.product_service import ProductService
from app.domain.product_filters import ProductFilters

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)

product_service = ProductService()


@router.get("")
def get_products(
    categoria: Optional[str] = Query(default=None),
    marca: Optional[str] = Query(default=None),
    precio_min: Optional[float] = Query(default=None, ge=0),
    precio_max: Optional[float] = Query(default=None, ge=0),
    solo_stock: bool = Query(default=False),
    texto: Optional[str] = Query(default=None),
):
    """Busca productos del catálogo con filtros opcionales."""
    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        raise HTTPException(
            status_code=400,
            detail="precio_min no puede ser mayor que precio_max"
        )

    try:
        filters = ProductFilters(
            categoria=categoria,
            marca=marca,
            precio_min=precio_min,
            precio_max=precio_max,
            solo_stock=solo_stock,
            texto=texto,
        )
        return product_service.search_products(filters)
    except Exception as error:
        logger.error("Error buscando productos: %s", error)
        raise HTTPException(
            status_code=503,
            detail="No se pudo acceder al catálogo de productos. Intenta de nuevo en unos momentos."
        )


@router.get("/{product_id}")
def get_product(product_id: str):
    """Devuelve un producto por su ID de Firestore."""
    try:
        return product_service.get_product(product_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except Exception as error:
        logger.error("Error obteniendo producto %s: %s", product_id, error)
        raise HTTPException(
            status_code=503,
            detail="No se pudo obtener el producto. Intenta de nuevo en unos momentos."
        )