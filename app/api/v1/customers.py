from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.services.customer import create_customer


router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


@router.post(
    "",
    response_model=CustomerResponse,
)
def create_customer_endpoint(
    customer_data: CustomerCreate,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    """Create a customer."""

    customer = create_customer(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=customer_data,
    )

    return customer