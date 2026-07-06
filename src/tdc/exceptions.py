class TDCBaseError(Exception):
    """Base class for all TDC exceptions."""
    pass

class ConfigError(TDCBaseError):
    """Raised when there is an issue with the configuration (e.g. invalid YAML, missing keys)."""
    pass

class DataFetchError(TDCBaseError):
    """Raised when Yahoo Finance fails to fetch data or returns invalid data."""
    pass

class AlgorithmError(TDCBaseError):
    """Raised when a mathematical anomaly occurs during simulation or density calculation."""
    pass

class RenderError(TDCBaseError):
    """Raised when there is an issue rendering the plot."""
    pass

class ExportError(TDCBaseError):
    """Raised when exporting features or charts fails (e.g. disk full, missing permissions)."""
    pass
