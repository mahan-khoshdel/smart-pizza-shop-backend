from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.branch import BranchRepository


def update_kitchen_capacity(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    kitchen_capacity: int,
):
    """
    Update kitchen capacity for a tenant-owned branch.
    """

    branch_repository = BranchRepository(db)

    branch = branch_repository.get_by_id(
        branch_id=branch_id,
        tenant_id=tenant_id,
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    return branch_repository.update_kitchen_capacity(
        branch=branch,
        kitchen_capacity=kitchen_capacity,
    )