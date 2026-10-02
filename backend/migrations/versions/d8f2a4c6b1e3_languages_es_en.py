"""podcasts in Spanish or English only: move other saved languages to English

Revision ID: d8f2a4c6b1e3
Revises: c3d1e7a9f2b4
Create Date: 2026-10-02 19:55:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd8f2a4c6b1e3'
down_revision: Union[str, Sequence[str], None] = 'c3d1e7a9f2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Data only. Those listeners already had the English voices (no native ones existed).
    op.execute("""UPDATE users SET preferences = jsonb_set(preferences, '{language}', '"en"')
                  WHERE preferences ? 'language' AND preferences->>'language' NOT IN ('es', 'en')""")
    op.execute("""UPDATE episodes SET prefs_snapshot = jsonb_set(prefs_snapshot, '{language}', '"en"')
                  WHERE prefs_snapshot ? 'language'
                    AND prefs_snapshot->>'language' NOT IN ('es', 'en')""")


def downgrade() -> None:
    pass  # "en" is valid in both versions
