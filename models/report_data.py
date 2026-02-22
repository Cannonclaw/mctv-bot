"""Data models for traction and performance reports."""

from dataclasses import dataclass, field


@dataclass
class PlayRecord:
    """A single play record from NTV360 data."""
    host_name: str
    content_name: str = ""
    play_count: int = 0
    play_duration_str: str = ""
    play_duration_seconds: int = 0
    playlist: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass
class VenueRecord:
    """Enriched venue data with network metadata."""
    host_name: str
    business_category: str = ""
    general_category: str = ""
    address: str = ""
    city: str = ""
    screen_count: int = 1
    monthly_traffic: float = 0.0
    dwell_time_minutes: float = 0.0
    monthly_impressions: float = 0.0
    total_plays: int = 0
    total_air_time: str = ""
    first_aired: str = ""
    last_aired: str = ""
    pct_of_total: float = 0.0


@dataclass
class TractionReportInput:
    """Input data for generating a traction report."""
    advertiser_name: str
    report_type: str = "advertiser"  # "advertiser" or "venue"
    campaign_period: str = ""
    campaign_start: str = ""
    campaign_end: str = ""
    network_name: str = ""
    venue_records: list = field(default_factory=list)  # list of VenueRecord
    total_plays: int = 0
    total_screen_count: int = 0
    total_air_time: str = ""
    total_impressions: float = 0.0
    avg_dwell_time: float = 0.0
    total_monthly_traffic: float = 0.0
    sales_rep: str = "Mary Michael Cannon"
    include_insights: bool = False
    additional_notes: str = ""


@dataclass
class CategoryBreakdown:
    """Performance breakdown by venue category."""
    category: str
    host_count: int = 0
    total_plays: int = 0
    monthly_impressions: float = 0.0
    avg_dwell_minutes: float = 0.0
    pct_of_total: float = 0.0
