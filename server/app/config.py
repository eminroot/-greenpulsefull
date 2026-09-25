"""Runtime configuration, read from the environment (see .env.example)."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="GP_", extra="ignore", case_sensitive=False
    )

    # --- core -------------------------------------------------------------
    env: str = "development"
    # Signs access tokens. Generate with: python -c "import secrets;print(secrets.token_urlsafe(48))"
    # A generated value is fine in development; production refuses to start without one.
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))

    # postgresql+asyncpg://user:pass@host/db in production,
    # sqlite+aiosqlite:///./greenpulse.db for local work.
    database_url: str = "sqlite+aiosqlite:///./greenpulse.db"

    # --- tokens -----------------------------------------------------------
    access_token_minutes: int = 30
    refresh_token_days: int = 60

    # --- Google sign in (optional) ---------------------------------------
    # The OAuth client id the mobile app uses. Empty disables Google sign in.
    google_client_id: str = ""
    # Extra client ids accepted on the id_token audience (ios/android/web variants).
    google_extra_client_ids: str = ""

    # --- rate limits ------------------------------------------------------
    # Tunable because the right numbers depend on the deployment: a co-op
    # signing several growers up from one office connection is not an attack.
    login_rate_limit: int = 8
    login_rate_window_seconds: int = 300
    signup_rate_limit: int = 10
    signup_rate_window_seconds: int = 3600
    assistant_rate_limit: int = 30
    assistant_rate_window_seconds: int = 600
    scan_rate_limit: int = 40
    scan_rate_window_seconds: int = 600

    # --- assistant --------------------------------------------------------
    # The model key. It lives only here: the app and the panel call our own
    # /assistant/chat, so the key is never shipped to a client. Empty disables
    # the assistant, which then reports itself as unavailable.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # --- storage ----------------------------------------------------------
    data_dir: Path = Path("data")
    max_image_bytes: int = 8 * 1024 * 1024

    # --- device / liveness ------------------------------------------------
    # A node is considered online if it reported within this many seconds.
    device_online_seconds: int = 900
    # How long a phone-submitted scan waits for a node before it is failed.
    scan_job_timeout_seconds: int = 180

    # --- http -------------------------------------------------------------
    cors_origins: str = ""

    @field_validator("data_dir")
    @classmethod
    def _abs_data_dir(cls, v: Path) -> Path:
        return v if v.is_absolute() else (Path.cwd() / v).resolve()

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}

    @property
    def assistant_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def google_audiences(self) -> list[str]:
        ids = [self.google_client_id, *self.google_extra_client_ids.split(",")]
        return [i.strip() for i in ids if i.strip()]

    @property
    def cors_list(self) -> list[str]:
        """Origins allowed to call the API from a browser.

        Empty is the right answer for this deployment: Caddy serves the panel
        from the same origin as the API, so no cross origin request needs to be
        allowed at all. The phone app is not a browser and is unaffected.
        """
        raw = self.cors_origins.strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def captures_dir(self) -> Path:
        return self.data_dir / "captures"


# HS256 wants at least as much key material as the digest it produces.
MIN_SECRET_BYTES = 32


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    generate = 'Generate one with: python -c "import secrets;print(secrets.token_urlsafe(48))"'

    if s.is_production:
        if "secret_key" not in s.model_fields_set:
            raise RuntimeError(f"GP_SECRET_KEY must be set in production. {generate}")
        if len(s.secret_key.encode()) < MIN_SECRET_BYTES:
            raise RuntimeError(
                f"GP_SECRET_KEY is too short: it needs at least {MIN_SECRET_BYTES} "
                f"bytes to sign tokens safely. {generate}"
            )
        if s.cors_list == ["*"]:
            raise RuntimeError(
                "GP_CORS_ORIGINS must not be * in production. The panel is served "
                "from the same origin as the API, so leave it empty unless another "
                "site needs access, in which case list that site explicitly."
            )

    s.captures_dir.mkdir(parents=True, exist_ok=True)
    return s


settings = get_settings()
