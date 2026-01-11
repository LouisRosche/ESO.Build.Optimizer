"""
Feature routes for ESO Build Optimizer API.

Handles retrieval of skills, gear sets, and other game features.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.security import CurrentUser
from api.models.database import Feature, GearSet, get_db
from api.models.schemas import (
    ESOClass,
    ErrorResponse,
    FeatureCategory,
    FeatureFilters,
    FeatureListResponse,
    FeatureResponse,
    FeatureSystem,
    FeatureType,
    FeatureUpdate,
    FeatureUpdatesResponse,
    GearSetFilters,
    GearSetListResponse,
    GearSetResponse,
    PVETier,
    SetType,
    SetWeight,
)

router = APIRouter(prefix="/features", tags=["Features"])


# =============================================================================
# List Features (Skills, etc.)
# =============================================================================

@router.get(
    "",
    response_model=FeatureListResponse,
    responses={
        200: {"description": "List of features"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="List features",
    description="Get a paginated list of game features (skills, passives, etc.) with optional filtering.",
)
async def list_features(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    system: FeatureSystem | None = Query(None, description="Filter by system (PLAYER, COMPANION, CHAMPION)"),
    category: FeatureCategory | None = Query(None, description="Filter by category (Class, Weapon, etc.)"),
    feature_type: FeatureType | None = Query(None, description="Filter by type (ACTIVE, PASSIVE, etc.)"),
    class_restriction: ESOClass | None = Query(None, description="Filter by class restriction"),
    search: str | None = Query(None, min_length=2, description="Search in name and effects"),
    limit: int = Query(100, ge=1, le=500, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> FeatureListResponse:
    """
    List game features with optional filtering.

    Features include skills, passives, morphs, and other player abilities.
    Use filters to narrow down results.
    """
    # Build query with filters
    query = select(Feature)

    if system:
        query = query.where(Feature.system == system.value)
    if category:
        query = query.where(Feature.category == category.value)
    if feature_type:
        query = query.where(Feature.feature_type == feature_type.value)
    if class_restriction:
        query = query.where(Feature.class_restriction == class_restriction.value)
    if search:
        # Escape SQL LIKE special characters to prevent pattern injection
        search_escaped = search.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{search_escaped}%"
        query = query.where(
            or_(
                Feature.name.ilike(search_pattern),
                Feature.base_effect.ilike(search_pattern),
                Feature.tags.ilike(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(Feature.category, Feature.name)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    features = result.scalars().all()

    return FeatureListResponse(
        features=[FeatureResponse.model_validate(f) for f in features],
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# List Gear Sets
# =============================================================================

@router.get(
    "/sets",
    response_model=GearSetListResponse,
    responses={
        200: {"description": "List of gear sets"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="List gear sets",
    description="Get a paginated list of gear sets with optional filtering.",
)
async def list_gear_sets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    set_type: SetType | None = Query(None, description="Filter by set type (Dungeon, Trial, etc.)"),
    weight: SetWeight | None = Query(None, description="Filter by armor weight"),
    pve_tier: PVETier | None = Query(None, description="Filter by PvE tier rating"),
    search: str | None = Query(None, min_length=2, description="Search in name and effects"),
    limit: int = Query(100, ge=1, le=500, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> GearSetListResponse:
    """
    List gear sets with optional filtering.

    Includes dungeon sets, trial sets, overland sets, monster sets, etc.
    """
    # Build query with filters
    query = select(GearSet)

    if set_type:
        query = query.where(GearSet.set_type == set_type.value)
    if weight:
        query = query.where(GearSet.weight == weight.value)
    if pve_tier:
        query = query.where(GearSet.pve_tier == pve_tier.value)
    if search:
        # Escape SQL LIKE special characters to prevent pattern injection
        search_escaped = search.replace("%", r"\%").replace("_", r"\_")
        search_pattern = f"%{search_escaped}%"
        query = query.where(
            or_(
                GearSet.name.ilike(search_pattern),
                GearSet.location.ilike(search_pattern),
                GearSet.tags.ilike(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(GearSet.set_type, GearSet.name)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    sets = result.scalars().all()

    return GearSetListResponse(
        sets=[GearSetResponse.model_validate(s) for s in sets],
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# Get Single Gear Set
# =============================================================================

@router.get(
    "/sets/{set_id}",
    response_model=GearSetResponse,
    responses={
        200: {"description": "Gear set details"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        404: {"description": "Gear set not found", "model": ErrorResponse},
    },
    summary="Get gear set details",
    description="Get detailed information about a specific gear set.",
)
async def get_gear_set(
    set_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GearSetResponse:
    """
    Get details of a specific gear set by ID.

    Returns complete information including all bonuses and role affinity.
    """
    result = await db.execute(
        select(GearSet).where(GearSet.set_id == set_id)
    )
    gear_set = result.scalar_one_or_none()

    if not gear_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gear set '{set_id}' not found",
        )

    return GearSetResponse.model_validate(gear_set)


# =============================================================================
# Feature Updates (Changes Since Patch)
# =============================================================================

# Patch ordering for comparison
# NOTE: This list must be updated each ESO quarterly patch release.
# Consider moving to a configuration file or database table for easier maintenance.
# ESO releases updates quarterly: Q1 (March), Q2 Chapter (June), Q3 (September), Q4 (December)
PATCH_ORDER = [
    "U35", "U36", "U37", "U38", "U39", "U40",
    "U41", "U42", "U43", "U44", "U45", "U46",
    "U47", "U48", "U49", "U50",
]


def patch_is_newer(patch_a: str, patch_b: str) -> bool:
    """Check if patch_a is newer than or equal to patch_b."""
    try:
        idx_a = PATCH_ORDER.index(patch_a)
        idx_b = PATCH_ORDER.index(patch_b)
        return idx_a >= idx_b
    except ValueError:
        # Unknown patch, assume newer
        return True


@router.get(
    "/updates",
    response_model=FeatureUpdatesResponse,
    responses={
        200: {"description": "Features updated since the specified patch"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        400: {"description": "Invalid patch version", "model": ErrorResponse},
    },
    summary="Get feature updates since patch",
    description="Get a list of features that were added or modified since a specific patch.",
)
async def get_feature_updates(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    since: str = Query(
        ...,
        description="Patch version to compare from (e.g., 'U47')",
        pattern=r"^U\d+$",
    ),
) -> FeatureUpdatesResponse:
    """
    Get features updated since a specific patch.

    Useful for keeping local data in sync with game updates.
    Returns all features where patch_updated is newer than the specified patch.
    """
    # Validate patch format
    if since not in PATCH_ORDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown patch version: {since}. Valid patches: {', '.join(PATCH_ORDER[-5:])}",
        )

    # Get all patches newer than 'since'
    since_idx = PATCH_ORDER.index(since)
    newer_patches = PATCH_ORDER[since_idx + 1:]

    if not newer_patches:
        # No newer patches
        return FeatureUpdatesResponse(
            since_patch=since,
            current_patch=settings.current_patch,
            updates=[],
            total_changes=0,
        )

    # Query features updated in newer patches
    feature_query = select(Feature).where(
        Feature.patch_updated.in_(newer_patches)
    ).order_by(Feature.patch_updated.desc(), Feature.name)

    result = await db.execute(feature_query)
    updated_features = result.scalars().all()

    # Query gear sets updated in newer patches
    set_query = select(GearSet).where(
        GearSet.patch_updated.in_(newer_patches)
    ).order_by(GearSet.patch_updated.desc(), GearSet.name)

    set_result = await db.execute(set_query)
    updated_sets = set_result.scalars().all()

    # Convert to update objects
    updates = []

    for feature in updated_features:
        updates.append(
            FeatureUpdate(
                feature_id=feature.feature_id,
                name=feature.name,
                category=FeatureCategory(feature.category),
                change_type="modified",  # We don't track adds vs modifies currently
                patch_updated=feature.patch_updated,
                previous_patch=since,
                changes=None,
            )
        )

    for gear_set in updated_sets:
        updates.append(
            FeatureUpdate(
                feature_id=gear_set.set_id,
                name=gear_set.name,
                category=FeatureCategory.SET,
                change_type="modified",
                patch_updated=gear_set.patch_updated,
                previous_patch=since,
                changes=None,
            )
        )

    return FeatureUpdatesResponse(
        since_patch=since,
        current_patch=settings.current_patch,
        updates=updates,
        total_changes=len(updates),
    )


# =============================================================================
# Search Features and Sets
# =============================================================================

class SearchResult(FeatureResponse):
    """Search result with type indicator."""
    result_type: str  # "feature" or "set"


class SearchResponse(FeatureListResponse):
    """Search response with combined results."""
    pass


@router.get(
    "/search",
    response_model=SearchResponse,
    responses={
        200: {"description": "Search results"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="Search features and sets",
    description="Search across all features and gear sets by name or effect.",
)
async def search_features(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
) -> SearchResponse:
    """
    Search across features and gear sets.

    Searches in names, effects, tags, and locations.
    Returns combined results ordered by relevance.
    """
    # Escape SQL LIKE special characters to prevent pattern injection
    search_escaped = q.replace("%", r"\%").replace("_", r"\_")
    search_pattern = f"%{search_escaped}%"

    # Search features
    feature_query = (
        select(Feature)
        .where(
            or_(
                Feature.name.ilike(search_pattern),
                Feature.base_effect.ilike(search_pattern),
                Feature.tags.ilike(search_pattern),
            )
        )
        .limit(limit // 2)
    )

    feature_result = await db.execute(feature_query)
    features = feature_result.scalars().all()

    # Search gear sets
    set_query = (
        select(GearSet)
        .where(
            or_(
                GearSet.name.ilike(search_pattern),
                GearSet.location.ilike(search_pattern),
                GearSet.tags.ilike(search_pattern),
            )
        )
        .limit(limit // 2)
    )

    set_result = await db.execute(set_query)
    sets = set_result.scalars().all()

    # Combine results
    # Note: For a proper implementation, we'd want a unified search model
    combined = [FeatureResponse.model_validate(f) for f in features]

    # Convert sets to feature-like response (simplified)
    for s in sets:
        # Create a feature-like representation for sets
        combined.append(
            FeatureResponse(
                feature_id=s.set_id,
                system=FeatureSystem.PLAYER,
                category=FeatureCategory.SET,
                feature_type=FeatureType.SET_BONUS,
                name=s.name,
                base_effect=str(s.bonuses),
                tags=s.tags,
                patch_updated=s.patch_updated,
                source_url=s.source_url,
            )
        )

    return SearchResponse(
        features=combined[:limit],
        total=len(combined),
        limit=limit,
        offset=0,
    )


# =============================================================================
# Get Features by Class
# =============================================================================

@router.get(
    "/class/{class_name}",
    response_model=FeatureListResponse,
    responses={
        200: {"description": "Class-specific features"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        400: {"description": "Invalid class name", "model": ErrorResponse},
    },
    summary="Get features by class",
    description="Get all features available to a specific class.",
)
async def get_features_by_class(
    class_name: ESOClass,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_universal: bool = Query(
        True,
        description="Include skills available to all classes",
    ),
) -> FeatureListResponse:
    """
    Get all features available to a specific class.

    Includes class-specific skills and optionally universal skills
    (weapon, guild, world, etc.).
    """
    # Build query for class features
    if include_universal:
        query = select(Feature).where(
            or_(
                Feature.class_restriction == class_name.value,
                Feature.class_restriction.is_(None),
            )
        )
    else:
        query = select(Feature).where(
            Feature.class_restriction == class_name.value
        )

    query = query.order_by(Feature.category, Feature.subcategory, Feature.name)

    result = await db.execute(query)
    features = result.scalars().all()

    return FeatureListResponse(
        features=[FeatureResponse.model_validate(f) for f in features],
        total=len(features),
        limit=len(features),
        offset=0,
    )


# =============================================================================
# Get Single Feature
# =============================================================================
# NOTE: This route MUST be defined AFTER all static routes like /sets, /updates,
# /search, and /class/{class_name} to prevent those paths from being matched
# as feature_id values.

@router.get(
    "/{feature_id}",
    response_model=FeatureResponse,
    responses={
        200: {"description": "Feature details"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        404: {"description": "Feature not found", "model": ErrorResponse},
    },
    summary="Get feature details",
    description="Get detailed information about a specific feature.",
)
async def get_feature(
    feature_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureResponse:
    """
    Get details of a specific feature by ID.

    Returns complete information including effects, scaling, and unlock requirements.
    """
    result = await db.execute(
        select(Feature).where(Feature.feature_id == feature_id)
    )
    feature = result.scalar_one_or_none()

    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{feature_id}' not found",
        )

    return FeatureResponse.model_validate(feature)
