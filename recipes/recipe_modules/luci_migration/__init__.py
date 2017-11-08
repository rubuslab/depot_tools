DEPS = [
  'recipe_engine/path',
  'recipe_engine/properties',
]

from recipe_engine.recipe_api import Property
from recipe_engine.config import ConfigGroup, Single

PROPERTIES = {
  '$depot_tools/luci_migration': Property(
    help='Properties specifically for the luci_migration module',
    param_name='migration_properties',
    kind=ConfigGroup(
      # Whether builder runs on LUCI stack.
      on_luci=Single(bool),
    ),
    default={},
  ),
}
