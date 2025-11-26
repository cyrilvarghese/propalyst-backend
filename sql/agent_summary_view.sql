-- Agent Summary View
-- Aggregates all crea_wapp data by agent_contact
-- One row per agent with all information aggregated

CREATE OR REPLACE VIEW public.crea_agent_summary AS
SELECT
  agent_contact,

  -- Agent Identity
  MIN(agent_name) AS agent_name,
  MIN(company_name) AS company_name,

  -- Activity Metrics
  COUNT(*) AS total_posts,
  MIN(message_date) AS first_seen,
  MAX(message_date) AS last_seen,

  -- Listing Type Breakdown
  COUNT(*) FILTER (WHERE LOWER(listing_type) LIKE '%sale%') AS sale_listings_count,
  COUNT(*) FILTER (WHERE LOWER(listing_type) LIKE '%rent%') AS rent_listings_count,
  COUNT(*) FILTER (WHERE LOWER(listing_type) LIKE '%requirement%') AS requirement_count,

  -- Transaction Type Breakdown
  COUNT(*) FILTER (WHERE LOWER(transaction_type) LIKE '%sell%' OR LOWER(transaction_type) LIKE '%buy%') AS buy_sell_count,
  COUNT(*) FILTER (WHERE LOWER(transaction_type) LIKE '%rent%' OR LOWER(transaction_type) LIKE '%lease%') AS rent_lease_count,

  -- Property Types (aggregated as array)
  ARRAY_AGG(DISTINCT property_type) FILTER (WHERE property_type IS NOT NULL) AS property_types,

  -- Locations (aggregated as array - top locations)
  ARRAY_AGG(DISTINCT location) FILTER (WHERE location IS NOT NULL) AS locations,

  -- Price Statistics
  MIN(price) FILTER (WHERE price IS NOT NULL AND price > 0) AS min_price,
  MAX(price) FILTER (WHERE price IS NOT NULL AND price > 0) AS max_price,
  AVG(price) FILTER (WHERE price IS NOT NULL AND price > 0) AS avg_price,

  -- Size Statistics
  MIN(size_sqft) FILTER (WHERE size_sqft IS NOT NULL AND size_sqft > 0) AS min_size_sqft,
  MAX(size_sqft) FILTER (WHERE size_sqft IS NOT NULL AND size_sqft > 0) AS max_size_sqft,
  AVG(size_sqft) FILTER (WHERE size_sqft IS NOT NULL AND size_sqft > 0) AS avg_size_sqft,

  -- Configuration Breakdown (BHK)
  ARRAY_AGG(DISTINCT configuration) FILTER (WHERE configuration IS NOT NULL) AS configurations,

  -- Status Breakdown
  COUNT(*) FILTER (WHERE LOWER(status) LIKE '%ready%') AS ready_count,
  COUNT(*) FILTER (WHERE LOWER(status) LIKE '%construction%' OR LOWER(status) LIKE '%under construction%') AS under_construction_count,

  -- Furnishing Breakdown
  COUNT(*) FILTER (WHERE LOWER(furnishing) LIKE '%furnished%' AND LOWER(furnishing) NOT LIKE '%unfurnished%') AS furnished_count,
  COUNT(*) FILTER (WHERE LOWER(furnishing) LIKE '%semi%') AS semi_furnished_count,
  COUNT(*) FILTER (WHERE LOWER(furnishing) LIKE '%unfurnished%') AS unfurnished_count,

  -- Sample Raw Messages (first 5 for quick reference)
  ARRAY_AGG(raw_message ORDER BY message_date DESC) FILTER (WHERE raw_message IS NOT NULL) AS all_raw_messages

FROM public.crea_wapp
WHERE agent_contact IS NOT NULL  -- Only agents with contact info
GROUP BY agent_contact
ORDER BY total_posts DESC;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_crea_wapp_agent_contact ON public.crea_wapp(agent_contact);
CREATE INDEX IF NOT EXISTS idx_crea_wapp_message_date ON public.crea_wapp(message_date);

-- Comments
COMMENT ON VIEW public.crea_agent_summary IS 'Aggregated view of all crea_wapp data grouped by agent_contact. One row per agent with comprehensive statistics.';
