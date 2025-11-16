"""Category endpoints for category management.

This module provides CRUD operations for categories.
"""

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore[import-untyped]

from time_audit.api.auth import verify_token
from time_audit.api.dependencies import get_storage
from time_audit.api.models import (
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)
from time_audit.core.models import Category
from time_audit.core.storage import StorageManager

router = APIRouter()


@router.get("/", response_model=list[CategoryResponse])
async def list_categories(
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),
) -> list[CategoryResponse]:
    """List all categories.

    Args:
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        List of categories

    Example:
        >>> GET /api/v1/categories
        [
            {
                "id": "development",
                "name": "Development",
                "color": "#007bff"
            }
        ]
    """
    categories = storage.load_categories()
    return [CategoryResponse.from_category(c) for c in categories]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),
) -> CategoryResponse:
    """Get a specific category by ID.

    Args:
        category_id: Category identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Category

    Raises:
        HTTPException: If category not found

    Example:
        >>> GET /api/v1/categories/development
    """
    category = storage.get_category(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )
    return CategoryResponse.from_category(category)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CreateCategoryRequest,
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),
) -> CategoryResponse:
    """Create a new category.

    Args:
        request: Create category request
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Created category

    Raises:
        HTTPException: If category already exists

    Example:
        >>> POST /api/v1/categories
        {
            "id": "development",
            "name": "Development",
            "color": "#007bff"
        }
    """
    # Check if category already exists
    existing = storage.get_category(request.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category {request.id} already exists",
        )

    category = Category(
        id=request.id,
        name=request.name,
        color=request.color,
    )
    storage.save_category(category)
    return CategoryResponse.from_category(category)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    request: UpdateCategoryRequest,
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),
) -> CategoryResponse:
    """Update an existing category.

    Args:
        category_id: Category identifier
        request: Update category request
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Returns:
        Updated category

    Raises:
        HTTPException: If category not found

    Example:
        >>> PUT /api/v1/categories/development
        {
            "name": "Software Development",
            "color": "#0056b3"
        }
    """
    category = storage.get_category(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )

    # Update only provided fields
    if request.name is not None:
        category.name = request.name
    if request.color is not None:
        category.color = request.color

    storage.update_category(category)
    return CategoryResponse.from_category(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    storage: StorageManager = Depends(get_storage),
    _: dict = Depends(verify_token),
) -> None:
    """Delete a category.

    Args:
        category_id: Category identifier
        storage: Storage manager (injected)
        _: Authentication token (injected)

    Raises:
        HTTPException: If category not found

    Example:
        >>> DELETE /api/v1/categories/development
    """
    category = storage.get_category(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )

    storage.delete_category(category_id)
