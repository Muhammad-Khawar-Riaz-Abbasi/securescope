"""initial TrustLedger schema"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("vendors", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("website", sa.String(300)), sa.Column("owner", sa.String(160)), sa.Column("review_status", sa.Enum("NOT_STARTED", "IN_REVIEW", "APPROVED", "NEEDS_ATTENTION", name="reviewstatus"), nullable=False), sa.Column("review_deadline", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("documents", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("document_type", sa.Enum("CONTRACT", "QUESTIONNAIRE", "POLICY", "OTHER", name="documenttype"), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("content_text", sa.Text(), nullable=False), sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("vendor_id", "content_hash", name="uq_vendor_document_hash"))
    op.create_table("findings", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False), sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL")), sa.Column("category", sa.String(80), nullable=False), sa.Column("severity", sa.String(20), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("detail", sa.Text(), nullable=False), sa.Column("evidence", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("qa_events", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False), sa.Column("question", sa.String(500), nullable=False), sa.Column("answer", sa.Text(), nullable=False), sa.Column("citations", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

def downgrade():
    op.drop_table("qa_events")
    op.drop_table("findings")
    op.drop_table("documents")
    op.drop_table("vendors")
