-- Agent Profiles Clean Table
-- Stores one clean profile row per agent, derived from LLM output
-- Based on the last 3 months of WhatsApp messages from crea_wapp

create table if not exists public.agent_profiles_clean (
  agent_contact text primary key,
  agent_name text,
  company_name text,

  -- numeric bands inferred by LLM for this agent
  sale_price_min numeric null,    -- rupees
  sale_price_max numeric null,    -- rupees
  rent_price_min numeric null,    -- rupees per month
  rent_price_max numeric null,    -- rupees per month
  bhk_min integer null,
  bhk_max integer null,

  -- supply vs demand orientation across sampled messages
  supply_sale_count integer not null default 0,   -- supply sale
  supply_rent_count integer not null default 0,   -- supply rent
  demand_buy_count integer not null default 0,    -- demand buy
  demand_rent_count integer not null default 0,   -- demand rent

  -- non numeric profile features
  primary_locations text[] null,        -- list of main areas
  primary_property_types text[] null,   -- standard labels

  -- full LLM response and summary
  profile_json jsonb not null,
  summary_text text not null,

  -- meta
  total_posts integer not null,
  lookback_months integer not null default 3,
  messages_sampled integer not null default 20,
  generated_at timestamptz not null default now()
);

-- Create indexes for common queries
create index if not exists idx_agent_profiles_sale_price on public.agent_profiles_clean (sale_price_min, sale_price_max);
create index if not exists idx_agent_profiles_rent_price on public.agent_profiles_clean (rent_price_min, rent_price_max);
create index if not exists idx_agent_profiles_bhk on public.agent_profiles_clean (bhk_min, bhk_max);
create index if not exists idx_agent_profiles_locations on public.agent_profiles_clean using gin (primary_locations);
create index if not exists idx_agent_profiles_property_types on public.agent_profiles_clean using gin (primary_property_types);
create index if not exists idx_agent_profiles_generated_at on public.agent_profiles_clean (generated_at);

-- Comments for documentation
comment on table public.agent_profiles_clean is 'Stores agent profiles generated from WhatsApp message analysis using LLM';
comment on column public.agent_profiles_clean.agent_contact is 'Agent phone number (primary key)';
comment on column public.agent_profiles_clean.sale_price_min is 'Minimum sale price in rupees inferred from messages';
comment on column public.agent_profiles_clean.sale_price_max is 'Maximum sale price in rupees inferred from messages';
comment on column public.agent_profiles_clean.rent_price_min is 'Minimum rent price in rupees per month inferred from messages';
comment on column public.agent_profiles_clean.rent_price_max is 'Maximum rent price in rupees per month inferred from messages';
comment on column public.agent_profiles_clean.supply_sale_count is 'Count of supply sale listings in sampled messages';
comment on column public.agent_profiles_clean.supply_rent_count is 'Count of supply rent listings in sampled messages';
comment on column public.agent_profiles_clean.demand_buy_count is 'Count of demand buy requirements in sampled messages';
comment on column public.agent_profiles_clean.demand_rent_count is 'Count of demand rent requirements in sampled messages';
comment on column public.agent_profiles_clean.primary_locations is 'List of 3-5 key areas/micro-markets the agent operates in';
comment on column public.agent_profiles_clean.primary_property_types is 'List of property types the agent specializes in';
comment on column public.agent_profiles_clean.profile_json is 'Full JSON response from LLM for debugging/reference';
comment on column public.agent_profiles_clean.summary_text is 'Human-readable summary of agent specialization';
comment on column public.agent_profiles_clean.generated_at is 'Timestamp when this profile was generated/updated';
