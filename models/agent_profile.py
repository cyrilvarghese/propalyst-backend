"""
Pydantic models for Agent Profiling
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AgentMessage(BaseModel):
    """Single message from an agent"""
    message_date: datetime
    raw_message: str


class TopAgentGrouped(BaseModel):
    """Model representing grouped messages for a top agent from the view"""
    agent_contact: str
    agent_name: str
    company_name: Optional[str] = None
    total_posts: int
    last_seen: datetime
    messages: List[AgentMessage]


class AgentProfileLLMInput(BaseModel):
    """Input payload sent to LLM for agent profiling"""
    agent_contact: str
    agent_name: str
    company_name: Optional[str] = None
    total_posts_last_3_months: int
    sample_messages: List[str] = Field(..., description="List of raw message texts")


class AgentProfileLLMOutput(BaseModel):
    """Expected output from LLM for agent profiling"""
    agent_contact: str
    primary_locations: List[str] = Field(default_factory=list, description="3-5 key areas or micro markets")
    primary_property_types: List[str] = Field(default_factory=list, description="Standard property type labels")
    sale_price_min: Optional[float] = Field(None, description="Minimum sale price in rupees")
    sale_price_max: Optional[float] = Field(None, description="Maximum sale price in rupees")
    rent_price_min: Optional[float] = Field(None, description="Minimum rent price in rupees per month")
    rent_price_max: Optional[float] = Field(None, description="Maximum rent price in rupees per month")
    bhk_min: Optional[int] = Field(None, description="Minimum BHK configuration")
    bhk_max: Optional[int] = Field(None, description="Maximum BHK configuration")
    supply_sale_count: int = Field(0, description="Count of supply sale messages")
    supply_rent_count: int = Field(0, description="Count of supply rent messages")
    demand_buy_count: int = Field(0, description="Count of demand buy messages")
    demand_rent_count: int = Field(0, description="Count of demand rent messages")
    summary_text: str = Field(..., description="Human-readable summary of agent specialization")


class AgentProfileClean(BaseModel):
    """Model representing stored agent profile"""
    agent_contact: str
    agent_name: str
    company_name: Optional[str] = None
    sale_price_min: Optional[float] = None
    sale_price_max: Optional[float] = None
    rent_price_min: Optional[float] = None
    rent_price_max: Optional[float] = None
    bhk_min: Optional[int] = None
    bhk_max: Optional[int] = None
    supply_sale_count: int = 0
    supply_rent_count: int = 0
    demand_buy_count: int = 0
    demand_rent_count: int = 0
    primary_locations: List[str] = Field(default_factory=list)
    primary_property_types: List[str] = Field(default_factory=list)
    profile_json: dict
    summary_text: str
    total_posts: int
    lookback_months: int = 3
    messages_sampled: int = 20
    generated_at: datetime


class AgentProfilingResponse(BaseModel):
    """Response model for agent profiling operations"""
    success: bool
    profiles_processed: int = 0
    profiles_created: int = 0
    profiles_updated: int = 0
    errors: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    data: Optional[List[AgentProfileClean]] = None
