"""Initial schema - create all tables.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Users table ===
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("api_requests_today", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_request_date", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])

    # === Combat Runs table ===
    op.create_table(
        "combat_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "player_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("character_name", sa.String(100), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_name", sa.String(255), nullable=False),
        sa.Column("difficulty", sa.String(50), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("group_size", sa.Integer(), nullable=False),
        sa.Column("build_snapshot", postgresql.JSON(), nullable=False),
        sa.Column("metrics", postgresql.JSON(), nullable=False),
        sa.Column("contribution_scores", postgresql.JSON(), nullable=True),
        sa.Column("dps", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("cp_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_combat_runs_player_id", "combat_runs", ["player_id"])
    op.create_index("ix_combat_runs_timestamp", "combat_runs", ["timestamp"])
    op.create_index("ix_combat_runs_content_type", "combat_runs", ["content_type"])
    op.create_index("ix_combat_runs_content_name", "combat_runs", ["content_name"])
    op.create_index("ix_combat_runs_success", "combat_runs", ["success"])
    op.create_index("ix_combat_runs_dps", "combat_runs", ["dps"])
    op.create_index(
        "ix_runs_content_lookup",
        "combat_runs",
        ["content_type", "content_name", "difficulty"],
    )
    op.create_index(
        "ix_runs_player_timestamp",
        "combat_runs",
        ["player_id", "timestamp"],
    )
    op.create_index(
        "ix_runs_percentile_calc",
        "combat_runs",
        ["content_name", "difficulty", "cp_level", "dps"],
    )

    # === Recommendations table ===
    op.create_table(
        "recommendations",
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("combat_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("current_state", sa.Text(), nullable=False),
        sa.Column("recommended_change", sa.Text(), nullable=False),
        sa.Column("expected_improvement", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_recommendations_run_id", "recommendations", ["run_id"])

    # === Features table ===
    op.create_table(
        "features",
        sa.Column("feature_id", sa.String(100), primary_key=True),
        sa.Column("system", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("feature_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_feature", sa.String(100), nullable=True),
        sa.Column("class_restriction", sa.String(50), nullable=True),
        sa.Column("unlock_method", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_cost", sa.Integer(), nullable=True),
        sa.Column("cast_time", sa.String(50), nullable=True),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("range_m", sa.Float(), nullable=True),
        sa.Column("radius_m", sa.Float(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("cooldown_sec", sa.Float(), nullable=True),
        sa.Column("base_effect", sa.Text(), nullable=True),
        sa.Column("scaling_stat", sa.String(100), nullable=True),
        sa.Column("max_ranks", sa.Integer(), nullable=True),
        sa.Column("rank_progression", sa.Text(), nullable=True),
        sa.Column("buff_debuff_granted", sa.String(255), nullable=True),
        sa.Column("synergy", sa.String(255), nullable=True),
        sa.Column("tags", sa.String(255), nullable=True),
        sa.Column("dlc_required", sa.String(100), nullable=True),
        sa.Column("patch_updated", sa.String(20), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_features_system", "features", ["system"])
    op.create_index("ix_features_category", "features", ["category"])
    op.create_index("ix_features_feature_type", "features", ["feature_type"])
    op.create_index("ix_features_name", "features", ["name"])
    op.create_index("ix_features_class_restriction", "features", ["class_restriction"])
    op.create_index("ix_features_patch_updated", "features", ["patch_updated"])
    op.create_index("ix_features_search", "features", ["name", "category", "system"])
    op.create_index("ix_features_class", "features", ["class_restriction", "category"])

    # === Gear Sets table ===
    op.create_table(
        "gear_sets",
        sa.Column("set_id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("set_type", sa.String(50), nullable=False),
        sa.Column("weight", sa.String(50), nullable=False),
        sa.Column("bind_type", sa.String(50), nullable=False),
        sa.Column("tradeable", sa.Boolean(), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("dlc_required", sa.String(100), nullable=True),
        sa.Column("bonuses", postgresql.JSON(), nullable=False),
        sa.Column("pve_tier", sa.String(10), nullable=True),
        sa.Column("role_affinity", postgresql.JSON(), nullable=True),
        sa.Column("tags", sa.String(255), nullable=True),
        sa.Column("patch_updated", sa.String(20), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_gear_sets_name", "gear_sets", ["name"])
    op.create_index("ix_gear_sets_set_type", "gear_sets", ["set_type"])
    op.create_index("ix_gear_sets_pve_tier", "gear_sets", ["pve_tier"])
    op.create_index("ix_gear_sets_patch_updated", "gear_sets", ["patch_updated"])
    op.create_index("ix_sets_search", "gear_sets", ["name", "set_type"])

    # === Rate Limits table ===
    op.create_table(
        "rate_limits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "window_start",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_rate_limits_user_id", "rate_limits", ["user_id"])
    op.create_index(
        "ix_rate_limits_lookup",
        "rate_limits",
        ["user_id", "endpoint", "window_start"],
    )


def downgrade() -> None:
    op.drop_table("rate_limits")
    op.drop_table("gear_sets")
    op.drop_table("features")
    op.drop_table("recommendations")
    op.drop_table("combat_runs")
    op.drop_table("users")
