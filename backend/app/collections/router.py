"""
Collections CRUD, scoped to the authenticated user's ownership.

The core invariant this router exists to enforce:

    User A must not be able to read, modify, or delete Collection B,
    even if User A knows Collection B's id.

Every single-resource query below filters by `owner_id == current_user.id`
*in the same database query* that filters by `id` — never "fetch by id,
then check ownership in Python." A resource that exists but isn't
owned by the caller returns 404, identical to a resource that doesn't
exist at all. This is deliberate: a 403 would leak that the id is
valid, letting an attacker enumerate other tenants' resource ids by
probing for 403-vs-404. See docs/architecture.md for the read of this
project's tenant-isolation invariant.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.collections.models import Collection
from app.collections.schemas import CollectionCreate, CollectionResponse, CollectionUpdate
from app.db.session import get_db

router = APIRouter(prefix="/collections", tags=["collections"])

_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Collection not found",
)


def _get_owned_collection_or_404(
    collection_id: uuid.UUID, current_user: User, db: Session
) -> Collection:
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.owner_id == current_user.id)
        .first()
    )
    if collection is None:
        raise _not_found_error
    return collection


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Collection:
    collection = Collection(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.get("", response_model=list[CollectionResponse])
def list_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Collection]:
    return (
        db.query(Collection)
        .filter(Collection.owner_id == current_user.id)
        .order_by(Collection.created_at.desc())
        .all()
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Collection:
    return _get_owned_collection_or_404(collection_id, current_user, db)


@router.patch("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: uuid.UUID,
    payload: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Collection:
    collection = _get_owned_collection_or_404(collection_id, current_user, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(collection, field, value)

    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    collection = _get_owned_collection_or_404(collection_id, current_user, db)
    db.delete(collection)
    db.commit()
