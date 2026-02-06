"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings populated from environment variables."""

    tif_directory: str
    index_directory: str
    cache_max_size: int
    max_workers: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables.

        Returns:
            A frozen Settings instance with values from the environment.
        """
        tif_directory = os.getenv("TIF_DIRECTORY", "/app/tif_files/")
        return cls(
            tif_directory=tif_directory,
            index_directory=os.getenv("INDEX_DIRECTORY", os.path.join(tif_directory, "index")),
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "100000")),
            max_workers=int(os.getenv("MAX_WORKERS", "100")),
        )
