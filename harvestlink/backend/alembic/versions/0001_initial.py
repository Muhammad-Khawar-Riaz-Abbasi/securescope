"""Initial HarvestLink schema (runtime metadata creates SQLite dev DB)."""
from alembic import op
import sqlalchemy as sa
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    # The canonical schema is maintained by SQLAlchemy metadata; this scaffold is ready for revisions.
    pass
def downgrade():
    pass
