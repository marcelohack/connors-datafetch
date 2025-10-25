from typing import Any, Callable, Dict, List, Type


class DataSourceRegistry:
    """Registry for data sources"""

    def __init__(self) -> None:
        self._datasources: Dict[str, Type] = {}

    def register_datasource(self, name: str) -> Callable[[Type], Type]:
        """
        Register a datasource class

        Args:
            name: Unique name for the datasource

        Returns:
            Decorator function

        Example:
            @registry.register_datasource("yfinance")
            class YfinanceDataSource:
                def fetch(self, symbol, start, end, interval="1d"):
                    ...
        """
        def decorator(cls: Type) -> Type:
            self._datasources[name] = cls
            cls._registry_name = name
            return cls

        return decorator

    def create_datasource(self, name: str, **kwargs: Any) -> Any:
        """
        Create an instance of a registered datasource

        Args:
            name: Name of the datasource to create
            **kwargs: Arguments to pass to the datasource constructor

        Returns:
            Instance of the datasource

        Raises:
            ValueError: If datasource is not registered
        """
        if name not in self._datasources:
            raise ValueError(
                f"Datasource '{name}' not found. Available: {list(self._datasources.keys())}"
            )
        return self._datasources[name](**kwargs)

    def get_datasource(self, name: str) -> Type:
        """
        Get the datasource class by name

        Args:
            name: Name of the datasource

        Returns:
            The datasource class

        Raises:
            ValueError: If datasource is not registered
        """
        if name not in self._datasources:
            raise ValueError(
                f"DataSource '{name}' not found. Available: {list(self._datasources.keys())}"
            )
        return self._datasources[name]

    def list_datasources(self) -> List[str]:
        """
        List all registered datasource names

        Returns:
            List of datasource names
        """
        return list(self._datasources.keys())


# Global registry instance
registry = DataSourceRegistry()
