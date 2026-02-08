"""Data source registry — delegates to the unified ComponentRegistry in connors-core.

All datasource registrations are stored in connors-core's central storage backend.
"""

from connors_core.core.registry import ComponentRegistry, registry

# Backward-compatible alias: ``DataSourceRegistry()`` creates a ComponentRegistry
# that has register_datasource, get_datasource, list_datasources, etc.
DataSourceRegistry = ComponentRegistry

__all__ = ["DataSourceRegistry", "registry"]
