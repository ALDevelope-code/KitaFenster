import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    data_dir: Path
    nas_root: Path
    scan_seconds: int = 60
    secure_cookie: bool = False
    background_scan: bool = True
    max_upload: int = 40 * 1024 * 1024
    admin_username: str = "admin"
    admin_password: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls):
        return cls(
            Path(os.getenv("DATA_DIR", "data")).resolve(),
            Path(os.getenv("NAS_ROOT", "demo-nas")).resolve(),
            max(10, int(os.getenv("SCAN_SECONDS", "60"))),
            os.getenv("COOKIE_SECURE", "false").lower() == "true",
            admin_username=os.getenv("ADMIN_USERNAME", "admin"),
            admin_password=os.getenv("ADMIN_PASSWORD"),
        )
