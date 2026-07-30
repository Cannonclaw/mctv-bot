# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Data models for proposal inputs."""

from dataclasses import dataclass, field


@dataclass
class ProposalInput:
    """Input data for an Elite Advertiser proposal."""
    business_name: str
    contact_name: str
    contact_email: str = ""
    industry: str = ""
    city: str = "Oxford"
    selected_markets: list = field(default_factory=lambda: ["Oxford"])
    recommended_tier: int = 0  # Index into elite_tiers
    custom_pricing: bool = False
    custom_screen_count: int = 0
    custom_monthly_rate: float = 0.0
    custom_per_slot_rate: float = 0.0
    sales_rep: str = "Mary Michael Cannon"
    additional_notes: str = ""


@dataclass
class HostInput:
    """Input data for a Host Media Kit proposal."""
    venue_name: str
    contact_name: str
    contact_email: str = ""
    venue_category: str = ""
    venue_address: str = ""
    city: str = "Oxford"
    estimated_foot_traffic: int = 0
    proposed_screen_count: int = 1
    free_outside_screens: int = 10
    sales_rep: str = "Mary Michael Cannon"
    additional_notes: str = ""


@dataclass
class BundleBusiness:
    """One business within a multi-brand bundle."""
    name: str
    industry: str = ""
    city: str = "Oxford"
    description: str = ""
    phone: str = ""
    website: str = ""


@dataclass
class BundleInput:
    """Input data for a Multi-Brand Bundle proposal."""
    owner_name: str
    owner_email: str = ""
    businesses: list = field(default_factory=list)  # list of BundleBusiness
    custom_monthly_rate: float = 0.0
    sales_rep: str = "Mary Michael Cannon"
    additional_notes: str = ""


@dataclass
class VenuePartnerInput:
    """Input data for a Venue Partner / Revenue Share proposal."""
    venue_name: str
    contact_name: str
    contact_email: str = ""
    venue_type: str = ""
    venue_address: str = ""
    city: str = ""
    proposed_screen_count: int = 5
    estimated_monthly_traffic: int = 0
    revenue_split_pct: float = 15.0
    premium_slot_rate: float = 1750.0
    standard_slot_rate: float = 1000.0
    sales_rep: str = "T. Creed Cannon"
    additional_notes: str = ""


@dataclass
class ExclusivityInput:
    """Input data for a Category Exclusivity proposal."""
    business_name: str
    contact_name: str
    contact_email: str = ""
    industry: str = ""
    exclusive_category: str = ""
    city: str = "Oxford"
    selected_markets: list = field(default_factory=lambda: ["Oxford"])
    base_tier: int = 0
    monthly_rate: float = 0.0
    sales_rep: str = "Mary Michael Cannon"
    additional_notes: str = ""


@dataclass
class RealEstateBoardInput:
    """Input data for a Real Estate Feeds Board proposal.

    The board is a dynamic creative format, not a static ad: agent/brokerage
    branding plus rotating listings plus a market mortgage-rate strip. Four
    sell modes share one generator because the board itself is the same
    product -- only who pays for it (and the disclosure burden) changes.

    board_mode is one of:
      "agent"     -- one agent buys their own board
      "brokerage" -- firm-level buy, usually with category exclusivity
      "cosponsor" -- agent + lender split one board (RESPA-sensitive)
      "lender"    -- lender-branded rate board (Reg Z / TILA-sensitive)
    """
    business_name: str
    contact_name: str
    contact_email: str = ""
    board_mode: str = "agent"
    brokerage_name: str = ""
    city: str = "Oxford"
    selected_markets: list = field(default_factory=lambda: ["Oxford"])
    board_tier: int = 0            # index into config real_estate_board.tiers
    monthly_rate: float = 0.0      # 0 = show tier table instead of a set rate
    listing_count: int = 0         # 0 = use the tier default
    agent_count: int = 1           # agents featured (brokerage mode)
    include_exclusivity: bool = False
    exclusive_category: str = "Real Estate"
    # Lender co-sponsorship. lender_share_pct splits the SAME board between
    # two separately-invoiced parties -- see the generator's _compliance
    # section for why that split is stated explicitly in the document.
    lender_name: str = ""
    lender_contact: str = ""
    lender_nmls_id: str = ""
    lender_share_pct: float = 0.0
    show_rate_strip: bool = True
    sales_rep: str = "T. Creed Cannon"
    additional_notes: str = ""


@dataclass
class RenewalInput:
    """Input data for a Renewal/Upgrade proposal."""
    business_name: str
    contact_name: str
    contact_email: str = ""
    current_tier: str = ""
    months_as_client: int = 6
    total_plays: int = 0
    total_venues: int = 0
    total_impressions: float = 0.0
    suggested_upgrade_tier: str = ""
    traction_data: dict = field(default_factory=dict)
    sales_rep: str = "Mary Michael Cannon"
    additional_notes: str = ""
