# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Data models for the audience & package simulator."""

from dataclasses import dataclass, field, asdict


@dataclass
class VenueScenario:
    """Per-venue computed metrics inside a scenario."""
    venue_key: str
    host_name: str
    category: str
    general_category: str
    address: str
    city: str
    zip_code: str
    license_count: int
    lat: float = 0.0
    lon: float = 0.0
    monthly_traffic: float = 0.0
    dwell_time_minutes: float = 0.0
    monthly_impressions: float = 0.0
    monthly_plays: int = 0
    plays_source: str = "modeled"
    age_pct: dict = field(default_factory=dict)
    income_pct: dict = field(default_factory=dict)
    education_pct: dict = field(default_factory=dict)
    audience_tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DemographicBlend:
    """Aggregate demographic profile across selected venues, weighted by impressions."""
    age_pct: dict = field(default_factory=dict)
    income_pct: dict = field(default_factory=dict)
    education_pct: dict = field(default_factory=dict)
    median_household_income_blended: int = 0
    audience_tags: list = field(default_factory=list)
    cities_covered: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TierRecommendation:
    """Pricing-tier recommendation for the selected scenario."""
    tier_index: int
    tier_name: str
    screen_count: int
    monthly_rate: float
    cost_per_screen: float
    cpm: float
    plays_per_month_label: str
    custom_override_rate: float = 0.0  # 0 means no override

    @property
    def effective_rate(self) -> float:
        return self.custom_override_rate if self.custom_override_rate > 0 else self.monthly_rate

    def to_dict(self) -> dict:
        d = asdict(self)
        d["effective_rate"] = self.effective_rate
        return d


@dataclass
class ScenarioResult:
    """Top-level simulator output."""
    venues: list = field(default_factory=list)            # list[VenueScenario]
    total_screens: int = 0
    total_monthly_impressions: float = 0.0
    total_monthly_plays: int = 0
    total_monthly_traffic: float = 0.0
    cities: list = field(default_factory=list)
    blend: DemographicBlend = field(default_factory=DemographicBlend)
    recommendation: TierRecommendation | None = None

    def to_dict(self) -> dict:
        return {
            "venues": [v.to_dict() for v in self.venues],
            "total_screens": self.total_screens,
            "total_monthly_impressions": self.total_monthly_impressions,
            "total_monthly_plays": self.total_monthly_plays,
            "total_monthly_traffic": self.total_monthly_traffic,
            "cities": self.cities,
            "blend": self.blend.to_dict(),
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
        }
