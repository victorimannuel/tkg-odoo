import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """Migrate old product_grid_position field to new swap_panes boolean."""
    env.cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pos_config' AND column_name = 'product_grid_position'
    """)
    if env.cr.fetchone():
        _logger.info("Migrating product_grid_position → swap_panes")
        env.cr.execute("""
            ALTER TABLE pos_config ADD COLUMN IF NOT EXISTS swap_panes BOOLEAN DEFAULT FALSE;
            UPDATE pos_config SET swap_panes = TRUE WHERE product_grid_position = 'left';
            ALTER TABLE pos_config DROP COLUMN IF EXISTS product_grid_position;
        """)
