"""empty message

Revision ID: 3a857d389bf3
Revises: b96ce837edcf
Create Date: 2022-01-15 19:29:27.221619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a857d389bf3'
down_revision = 'b96ce837edcf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('unique_user_peer', 'connections', ['user_id', 'peer_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('unique_user_peer', 'connections', type_='unique')
    # ### end Alembic commands ###