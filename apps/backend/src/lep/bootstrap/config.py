"""Environment-backed runtime settings for the foundation application."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "lep-api"
    environment: str = "development"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        defaults = cls()
        return cls(
            service_name=os.getenv("LEP_SERVICE_NAME", defaults.service_name),
            environment=os.getenv("LEP_ENV", defaults.environment),
            log_level=os.getenv("LEP_LOG_LEVEL", defaults.log_level).upper(),
        )
