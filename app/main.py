from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.customer_addresses import (
    router as customer_addresses_router,
)
from app.api.v1.customers import router as customers_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.product_variants import router as product_variants_router
from app.api.v1.purchases import router as purchases_router
from app.api.v1.recipes import router as recipes_router


app = FastAPI(
    title="Order Business Platform API",
    version="1.0.0",
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    purchases_router,
    prefix="/api/v1",
)

app.include_router(
    inventory_router,
    prefix="/api/v1",
)

app.include_router(
    customers_router,
    prefix="/api/v1",
)

app.include_router(
    customer_addresses_router,
    prefix="/api/v1",
)

app.include_router(
    orders_router,
    prefix="/api/v1"
)

app.include_router(
    categories_router,
    prefix="/api/v1"
)

app.include_router(
    products_router,
    prefix="/api/v1"
)

app.include_router(
    product_variants_router,
    prefix="/api/v1"
)

app.include_router(
    recipes_router,
    prefix="/api/v1"
)