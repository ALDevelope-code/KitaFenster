from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Mode = Literal["photos", "plan", "messages", "mixed"]
Area = Literal["main", "secondary"]
Clock = str


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def timestamp(value):
    if value:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("Zeitpunkt benötigt eine Zeitzone")
        return d.isoformat()
    return None


class Window(Model):
    days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], min_length=1, max_length=7)
    start: Clock = "07:00"
    end: Clock = "18:00"

    @field_validator("days")
    @classmethod
    def valid_days(cls, values):
        if any(d < 0 or d > 6 for d in values):
            raise ValueError("Wochentage müssen zwischen 0 und 6 liegen")
        return sorted(set(values))

    @field_validator("start", "end")
    @classmethod
    def valid_clock(cls, value):
        parsed = datetime.strptime(value, "%H:%M")
        if parsed.strftime("%H:%M") != value:
            raise ValueError("Uhrzeit als HH:MM angeben")
        return value


class DisplayWindow(Window):
    area: Area = "main"
    name: str = Field(default="", max_length=80)
    mode: Mode | None = None
    document_id: str | None = Field(default=None, max_length=80)


class PlaylistEntry(Model):
    mode: Literal["photos", "plan", "messages"]
    seconds: int = Field(default=15, ge=3, le=3600)
    document_id: str | None = Field(default=None, max_length=80)


class MotionSettings(Model):
    enabled: bool = False
    idle_minutes: int = Field(default=5, ge=1, le=240)
    power_mode: Literal["hdmi", "black"] = "hdmi"


class ContentSettings(Model):
    default_mode: Mode = "photos"
    document_id: str | None = Field(default=None, max_length=80)
    interval: int = Field(default=12, ge=3, le=3600)
    playlist: list[PlaylistEntry] = Field(
        default_factory=lambda: [
            PlaylistEntry(mode="photos", seconds=12),
            PlaylistEntry(mode="plan", seconds=20),
            PlaylistEntry(mode="messages", seconds=15),
        ],
        min_length=1,
        max_length=12,
    )


class SplitSettings(Model):
    enabled: bool = False
    direction: Literal["auto", "horizontal", "vertical"] = "auto"
    secondary_percent: Literal[33, 40, 50] = 33
    main_position: Literal["first", "second"] = "first"
    secondary: ContentSettings = Field(
        default_factory=lambda: ContentSettings(
            default_mode="messages",
            interval=15,
            playlist=[PlaylistEntry(mode="messages", seconds=15), PlaylistEntry(mode="photos", seconds=12)],
        )
    )


class OperatingHours(Model):
    enabled: bool = False
    timezone: str = "Europe/Berlin"
    windows: list[Window] = Field(default_factory=list, max_length=14)

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError("Unbekannte Zeitzone")
        return value


class Settings(ContentSettings):
    operating_hours_override: OperatingHours | None = None
    split: SplitSettings = Field(default_factory=SplitSettings)
    order: Literal["name", "shuffle"] = "name"
    fit: Literal["contain", "cover"] = "contain"
    transition: Literal["none", "fade", "slide"] = "fade"
    transition_seconds: float = Field(default=0.6, ge=0, le=3)
    rotation: Literal[0, 90, 180, 270] = 0
    timezone: str = "Europe/Berlin"
    content_windows_enabled: bool = True
    content_windows: list[DisplayWindow] = Field(default_factory=list, max_length=14)
    motion: MotionSettings = Field(default_factory=MotionSettings)

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError("Unbekannte Zeitzone")
        return value


class GroupInput(Model):
    name: str = Field(min_length=1, max_length=60)
    folder: str = Field(min_length=1, max_length=240)
    plan_path: str = Field(default="", max_length=240)
    plan_public: bool = False


class DeviceInput(Model):
    name: str = Field(min_length=1, max_length=60)
    group_id: str
    allow_internal: bool = False
    settings: Settings = Field(default_factory=Settings)


class Target(Model):
    kind: Literal["all", "group", "device"] = "all"
    id: str = ""

    @model_validator(mode="after")
    def valid_target(self):
        if self.kind != "all" and not self.id:
            raise ValueError("Ziel fehlt")
        return self


class Period(Model):
    starts_at: str | None = None
    ends_at: str | None = None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def valid_timestamp(cls, value):
        return timestamp(value)

    @model_validator(mode="after")
    def valid_period(self):
        if (
            self.starts_at
            and self.ends_at
            and datetime.fromisoformat(self.ends_at) <= datetime.fromisoformat(self.starts_at)
        ):
            raise ValueError("Ende muss nach dem Start liegen")
        return self


class NoticeInput(Period):
    title: str = Field(min_length=1, max_length=100)
    text: str = Field(default="", max_length=1400)
    target: Target = Field(default_factory=Target)
    internal: bool = False
    urgent: bool = False
    theme: Literal["ocean", "sun", "berry"] = "ocean"
    image_id: str | None = None


class Control(Model):
    area: Area = "main"
    target: Target
    mode: Mode | None = None
    until: str | None = None

    @field_validator("until")
    @classmethod
    def valid_until(cls, value):
        return timestamp(value)


class Login(Model):
    username: str = Field(max_length=80)
    password: str


class BrandingInput(Model):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value):
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Bitte einen gültigen Namen der Einrichtung angeben.")
        return value


class Pair(Model):
    code: str = Field(min_length=6, max_length=80)


class PlanAssignment(Model):
    plan_public: bool = False


class DocumentListInput(Model):
    all_groups: bool = False
    group_ids: list[str] = Field(default_factory=list, max_length=1000)


class DocumentInput(Model):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    public: bool = False
    revoke_group_release: bool = False

    @field_validator("name", "category")
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Bitte einen gültigen Namen und eine Dokumentart angeben")
        return value


class StorageStatus(Model):
    total_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    reserved_bytes: int = Field(ge=0)
    cache_limit_bytes: int = Field(ge=0)


class Heartbeat(Model):
    mode: str = Field(default="starting", max_length=30)
    reason: str = Field(default="", max_length=160)
    revision: str = Field(default="", max_length=100)
    last_sync: str | None = None
    error: str = Field(default="", max_length=160)
    ack: list[str] = Field(default_factory=list, max_length=100)
    storage: StorageStatus | None = None

    @field_validator("last_sync")
    @classmethod
    def valid_last_sync(cls, value):
        return timestamp(value)


class MotionEvent(Model):
    signal: bool
    initial: bool
    ago_seconds: float = Field(ge=0, allow_inf_nan=False)
    previous_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class MotionSample(Model):
    enabled: bool
    phase: Literal["disabled", "error", "warmup", "urgent", "high", "hold", "idle"]
    signal: bool | None
    signal_seconds: float | None = Field(ge=0, allow_inf_nan=False)
    warmup_seconds: int = Field(ge=0, le=60)
    remaining_seconds: int | None = Field(ge=0)
    idle_minutes: int = Field(ge=1, le=240)
    power_mode: Literal["hdmi", "black"]
    retry_seconds: int = Field(ge=0, le=30)
    sensor_error: str = Field(max_length=400)
    events: list[MotionEvent] = Field(max_length=20)
    display: Literal["on", "standby", "black"]
    display_error: str = Field(max_length=400)
    mode: str = Field(max_length=30)
    reason: str = Field(max_length=160)
    sample_age_seconds: float = Field(ge=0, allow_inf_nan=False)


class MotionReport(Model):
    sample: MotionSample | None = None
