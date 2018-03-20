"""Create base database tables

Revision ID: cc0056c7d405
Revises: 
Create Date: 2018-03-20 18:46:42.127294

"""
from alembic import op
import sqlalchemy as sa

from deckhand.db.sqlalchemy import models


# revision identifiers, used by Alembic.
revision = 'cc0056c7d405'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(models.Bucket.__tablename__, *tables.Bucket.__schema__)


def downgrade():
    op.drop_table(models.Bucket.__tablename__)
