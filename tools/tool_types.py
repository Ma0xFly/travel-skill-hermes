from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ApiResult:
    ok: bool
    source: str
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WeatherCurrent:
    weather: str
    temperature: str
    humidity: str
    wind_direction: str
    wind_power: str
    report_time: str


@dataclass
class WeatherForecastItem:
    date: str
    day_weather: str
    night_weather: str
    day_temp: str
    night_temp: str
    day_wind: str
    day_power: str


@dataclass
class WeatherResult:
    city: str
    current: Optional[WeatherCurrent] = None
    forecast: List[WeatherForecastItem] = field(default_factory=list)
    travel_advice: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "city": self.city,
            "current": asdict(self.current) if self.current else None,
            "forecast": [asdict(item) for item in self.forecast],
            "travel_advice": self.travel_advice,
        }


@dataclass
class PoiItem:
    name: str
    address: str
    location: str
    district: str
    poi_type: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouteResult:
    mode: str
    origin: str
    destination: str
    distance_m: int
    duration_s: int
    summary: str
    cost: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResultItem:
    title: str
    snippet: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResultBundle:
    query: str
    items: List[SearchResultItem] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "items": [item.to_dict() for item in self.items],
            "summary": self.summary,
        }


@dataclass
class SnapshotMeta:
    version: str
    created_at: str
    note: str
    files: List[str]

    @classmethod
    def create(cls, version: str, note: str, files: List[str]) -> "SnapshotMeta":
        return cls(
            version=version,
            created_at=datetime.utcnow().isoformat(),
            note=note,
            files=files,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
