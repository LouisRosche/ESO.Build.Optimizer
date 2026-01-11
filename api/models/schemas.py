"""
Pydantic schemas for ESO Build Optimizer API.

These schemas are based on the data models defined in CLAUDE.md sections 4.1-4.4.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# Enums
# =============================================================================

class ESOClass(str, Enum):
    DRAGONKNIGHT = "Dragonknight"
    NIGHTBLADE = "Nightblade"
    SORCERER = "Sorcerer"
    TEMPLAR = "Templar"
    WARDEN = "Warden"
    NECROMANCER = "Necromancer"
    ARCANIST = "Arcanist"


class ContentType(str, Enum):
    DUNGEON = "dungeon"
    TRIAL = "trial"
    ARENA = "arena"
    OVERWORLD = "overworld"
    PVP = "pvp"


class Difficulty(str, Enum):
    NORMAL = "normal"
    VETERAN = "veteran"
    HARDMODE = "hardmode"


class FeatureSystem(str, Enum):
    PLAYER = "PLAYER"
    COMPANION = "COMPANION"
    CHAMPION = "CHAMPION"


class FeatureCategory(str, Enum):
    CLASS = "Class"
    WEAPON = "Weapon"
    ARMOR = "Armor"
    GUILD = "Guild"
    WORLD = "World"
    ALLIANCE_WAR = "AllianceWar"
    RACIAL = "Racial"
    CRAFTING = "Crafting"
    SCRIBING = "Scribing"
    SET = "Set"


class FeatureType(str, Enum):
    ULTIMATE = "ULTIMATE"
    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    MORPH_A = "MORPH_A"
    MORPH_B = "MORPH_B"
    SET_BONUS = "SET_BONUS"


class SetType(str, Enum):
    DUNGEON = "Dungeon"
    TRIAL = "Trial"
    OVERLAND = "Overland"
    MONSTER = "Monster"
    CRAFTABLE = "Craftable"
    MYTHIC = "Mythic"
    ARENA = "Arena"
    PVP = "PvP"


class SetWeight(str, Enum):
    LIGHT = "Light"
    MEDIUM = "Medium"
    HEAVY = "Heavy"
    JEWELRY = "Jewelry"
    WEAPON = "Weapon"


class BindType(str, Enum):
    BOP = "Bind on Pickup"
    BOE = "Bind on Equip"
    CRAFTABLE = "Craftable"


class ResourceType(str, Enum):
    MAGICKA = "Magicka"
    STAMINA = "Stamina"
    ULTIMATE = "Ultimate"
    HEALTH = "Health"
    NONE = "None"


class RecommendationCategory(str, Enum):
    GEAR = "gear"
    SKILL = "skill"
    EXECUTION = "execution"
    BUILD = "build"


class PVETier(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    F = "F"


# =============================================================================
# Authentication Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response (no password)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    is_active: bool = True


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""
    sub: UUID
    exp: datetime
    iat: datetime


# =============================================================================
# Combat Metrics Schemas
# =============================================================================

class BuffUptime(BaseModel):
    """Buff/debuff uptime tracking."""
    name: str
    uptime: float = Field(..., ge=0.0, le=1.0)


class CombatMetrics(BaseModel):
    """Per-encounter combat metrics."""
    # Damage
    damage_done: int = Field(0, ge=0)
    dps: float = Field(0.0, ge=0.0)
    crit_rate: float = Field(0.0, ge=0.0, le=1.0)
    dot_uptime: list[BuffUptime] = Field(default_factory=list)

    # Healing
    healing_done: int = Field(0, ge=0)
    hps: float = Field(0.0, ge=0.0)
    overhealing: int = Field(0, ge=0)

    # Tanking
    damage_taken: int = Field(0, ge=0)
    damage_blocked: int = Field(0, ge=0)
    damage_mitigated: int = Field(0, ge=0)

    # Buffs/Debuffs
    buff_uptime: list[BuffUptime] = Field(default_factory=list)
    debuff_uptime: list[BuffUptime] = Field(default_factory=list)

    # Mechanics
    interrupts: int = Field(0, ge=0)
    synergies_used: int = Field(0, ge=0)
    synergies_provided: int = Field(0, ge=0)
    deaths: int = Field(0, ge=0)
    time_dead: float = Field(0.0, ge=0.0)

    # Resources
    magicka_spent: int = Field(0, ge=0)
    stamina_spent: int = Field(0, ge=0)
    ultimate_spent: int = Field(0, ge=0)
    potion_uses: int = Field(0, ge=0)


class ContributionScores(BaseModel):
    """Contribution model scores (0.0-1.0 for each category)."""
    damage_dealt: float = Field(0.0, ge=0.0, le=1.0)
    damage_taken: float = Field(0.0, ge=0.0, le=1.0)
    healing_done: float = Field(0.0, ge=0.0, le=1.0)
    buff_uptime: float = Field(0.0, ge=0.0, le=1.0)
    debuff_uptime: float = Field(0.0, ge=0.0, le=1.0)
    mechanic_execution: float = Field(0.0, ge=0.0, le=1.0)
    resource_efficiency: float = Field(0.0, ge=0.0, le=1.0)


# =============================================================================
# Build Schemas
# =============================================================================

class ChampionPoints(BaseModel):
    """Champion point allocation."""
    warfare: dict[str, int] = Field(default_factory=dict)
    fitness: dict[str, int] = Field(default_factory=dict)
    craft: dict[str, int] = Field(default_factory=dict)


class BuildSnapshot(BaseModel):
    """Snapshot of character build at time of run."""
    player_class: ESOClass = Field(..., alias="class")
    subclass: Optional[ESOClass] = None
    race: str
    cp_level: int = Field(..., ge=0, le=3600)
    sets: list[str] = Field(..., max_length=10)
    skills_front: list[str] = Field(..., max_length=6)
    skills_back: list[str] = Field(..., max_length=6)
    champion_points: Optional[ChampionPoints] = None

    model_config = ConfigDict(populate_by_name=True)


# =============================================================================
# Combat Run Schemas
# =============================================================================

class ContentInfo(BaseModel):
    """Information about the content being run."""
    content_type: ContentType = Field(..., alias="type")
    name: str
    difficulty: Difficulty

    model_config = ConfigDict(populate_by_name=True)


class CombatRunBase(BaseModel):
    """Base combat run schema."""
    character_name: str = Field(..., min_length=1, max_length=100)
    content: ContentInfo
    duration_sec: int = Field(..., ge=0)
    success: bool
    group_size: int = Field(..., ge=1, le=24)
    build_snapshot: BuildSnapshot
    metrics: CombatMetrics


class CombatRunCreate(CombatRunBase):
    """Schema for creating a combat run."""
    pass


class CombatRunResponse(CombatRunBase):
    """Schema for combat run response."""
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    player_id: UUID
    timestamp: datetime
    contribution_scores: Optional[ContributionScores] = None


class CombatRunListItem(BaseModel):
    """Simplified combat run for list views."""
    model_config = ConfigDict(from_attributes=True)

    run_id: UUID
    character_name: str
    content_name: str
    content_type: ContentType
    difficulty: Difficulty
    timestamp: datetime
    duration_sec: int
    success: bool
    dps: float


class CombatRunFilters(BaseModel):
    """Filters for listing combat runs."""
    content_type: Optional[ContentType] = None
    content_name: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    character_name: Optional[str] = None
    success: Optional[bool] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_dps: Optional[float] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


# =============================================================================
# Recommendation Schemas
# =============================================================================

class RecommendationBase(BaseModel):
    """Base recommendation schema."""
    category: RecommendationCategory
    priority: int = Field(..., ge=1, le=10)
    current_state: str
    recommended_change: str
    expected_improvement: str
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class RecommendationResponse(RecommendationBase):
    """Schema for recommendation response."""
    model_config = ConfigDict(from_attributes=True)

    recommendation_id: UUID
    run_id: UUID


class RecommendationsListResponse(BaseModel):
    """Schema for list of recommendations."""
    run_id: UUID
    recommendations: list[RecommendationResponse]
    percentiles: Optional[dict[str, float]] = None
    sample_size: int
    confidence: str = Field(..., description="low, medium, or high")


# =============================================================================
# Feature Schemas (Skills, Sets, etc.)
# =============================================================================

class FeatureBase(BaseModel):
    """Base feature schema matching CLAUDE.md section 4.1."""
    feature_id: str
    system: FeatureSystem
    category: FeatureCategory
    subcategory: Optional[str] = None
    feature_type: FeatureType
    name: str
    parent_feature: Optional[str] = None
    class_restriction: Optional[ESOClass] = None
    unlock_method: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    resource_cost: Optional[int] = None
    cast_time: Optional[str] = None
    target_type: Optional[str] = None
    range_m: Optional[float] = None
    radius_m: Optional[float] = None
    duration_sec: Optional[float] = None
    cooldown_sec: Optional[float] = None
    base_effect: Optional[str] = None
    scaling_stat: Optional[str] = None
    max_ranks: Optional[int] = None
    rank_progression: Optional[str] = None
    buff_debuff_granted: Optional[str] = None
    synergy: Optional[str] = None
    tags: Optional[str] = None
    dlc_required: Optional[str] = None
    patch_updated: str
    source_url: Optional[str] = None


class FeatureResponse(FeatureBase):
    """Schema for feature response."""
    model_config = ConfigDict(from_attributes=True)


class FeatureListResponse(BaseModel):
    """Schema for list of features."""
    features: list[FeatureResponse]
    total: int
    limit: int
    offset: int


class FeatureFilters(BaseModel):
    """Filters for listing features."""
    system: Optional[FeatureSystem] = None
    category: Optional[FeatureCategory] = None
    feature_type: Optional[FeatureType] = None
    class_restriction: Optional[ESOClass] = None
    search: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


# =============================================================================
# Gear Set Schemas
# =============================================================================

class SetBonusEffect(BaseModel):
    """Individual set bonus effect."""
    stat: Optional[str] = None
    value: Optional[int] = None
    effect: Optional[str] = None
    uptime: Optional[str] = None
    proc_condition: Optional[str] = None
    buff_granted: Optional[str] = None
    duration_sec: Optional[float] = None
    cooldown_sec: Optional[float] = None


class RoleAffinity(BaseModel):
    """Role affinity scores for a gear set."""
    damage_dealt: float = Field(0.0, ge=0.0, le=1.0)
    buff_uptime: float = Field(0.0, ge=0.0, le=1.0)
    healing_done: float = Field(0.0, ge=0.0, le=1.0)
    damage_taken: float = Field(0.0, ge=0.0, le=1.0)


class GearSetBase(BaseModel):
    """Base gear set schema matching CLAUDE.md section 4.4."""
    set_id: str
    name: str
    set_type: SetType
    weight: SetWeight
    bind_type: BindType
    tradeable: bool
    location: str
    dlc_required: Optional[str] = None
    bonuses: dict[str, SetBonusEffect]
    pve_tier: Optional[PVETier] = None
    role_affinity: Optional[RoleAffinity] = None
    tags: Optional[str] = None
    patch_updated: str
    source_url: Optional[str] = None


class GearSetResponse(GearSetBase):
    """Schema for gear set response."""
    model_config = ConfigDict(from_attributes=True)


class GearSetListResponse(BaseModel):
    """Schema for list of gear sets."""
    sets: list[GearSetResponse]
    total: int
    limit: int
    offset: int


class GearSetFilters(BaseModel):
    """Filters for listing gear sets."""
    set_type: Optional[SetType] = None
    weight: Optional[SetWeight] = None
    pve_tier: Optional[PVETier] = None
    search: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


# =============================================================================
# Feature Updates Schema
# =============================================================================

class FeatureUpdate(BaseModel):
    """Schema for feature update information."""
    feature_id: str
    name: str
    category: FeatureCategory
    change_type: str = Field(..., description="added, modified, or removed")
    patch_updated: str
    previous_patch: Optional[str] = None
    changes: Optional[str] = None


class FeatureUpdatesResponse(BaseModel):
    """Schema for feature updates since a patch."""
    since_patch: str
    current_patch: str
    updates: list[FeatureUpdate]
    total_changes: int


# =============================================================================
# Common Response Schemas
# =============================================================================

class PaginatedResponse(BaseModel):
    """Base paginated response."""
    total: int
    limit: int
    offset: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    status_code: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    database: str = "connected"
