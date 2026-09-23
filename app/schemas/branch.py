from uuid import UUID

from pydantic import BaseModel, Field


class KitchenCapacityUpdate(BaseModel):
    """
    Request schema for updating branch kitchen capacity.
    """

    kitchen_capacity: int = Field(
        ...,
        ge=1,
    )


class BranchKitchenCapacityResponse(BaseModel):
    """
    Represents the kitchen capacity configuration of a branch.
    """

    branch_id: UUID
    name: str
    kitchen_capacity: int