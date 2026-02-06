"""Custom exception hierarchy for the application."""


class AppError(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ElevationNotFoundError(AppError):
    """Raised when elevation data is not available for given coordinates."""

    def __init__(self, latitude: float, longitude: float) -> None:
        super().__init__(
            f"Elevation data not found for coordinates ({latitude}, {longitude})",
            code="ELEVATION_NOT_FOUND",
        )
        self.latitude = latitude
        self.longitude = longitude


class ElevationReadError(AppError):
    """Raised when reading elevation data from a TIF file fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="ELEVATION_READ_ERROR")


class InvalidCoordinateError(AppError):
    """Raised when coordinate input is malformed or out of range."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_COORDINATE")


class IndexBuildError(AppError):
    """Raised when the spatial index cannot be built or loaded."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INDEX_BUILD_ERROR")
