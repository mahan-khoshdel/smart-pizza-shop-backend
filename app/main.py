from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.customer_addresses import (
    router as customer_addresses_router,
)
from app.api.v1.customers import router as customers_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.purchases import router as purchases_router


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