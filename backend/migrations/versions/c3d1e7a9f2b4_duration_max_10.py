"""episodes last 5 or 10 minutes: move saved 20-minute choices to 10

Revision ID: c3d1e7a9f2b4
Revises: 0b10cd8294bc
Create Date: 2026-10-02 19:40:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c3d1e7a9f2b4'
down_revision: Union[str, Sequence[str], None] = '0b10cd8294bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Data only: the 20-minute option is gone; production capped it at 10 anyway.
    op.execute("""UPDATE users SET preferences = jsonb_set(preferences, '{duration_min}', '10')
                  WHERE preferences->>'duration_min' = '20'""")
    op.execute("""UPDATE episodes SET prefs_snapshot = jsonb_set(prefs_snapshot, '{duration_min}', '10')
                  WHERE prefs_snapshot->>'duration_min' = '20'""")


def downgrade() -> None:
    pass  # nothing to undo: 10 is valid in both versions
