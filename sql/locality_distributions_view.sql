-- Locality Distribution View
-- Aggregates whatsapp_listings_relevant by location with distribution breakdowns
-- Shows counts for price ranges, area ranges, property types, and BHK configurations

CREATE OR REPLACE VIEW public.locality_distributions AS
SELECT
  LOWER(TRIM(location)) AS location,

  -- Total count
  COUNT(*) AS total_listings,

  -- Price Range Distribution (in rupees - Crores)
  -- 2-5Cr: 20M - 50M
  COUNT(*) FILTER (WHERE price >= 20000000 AND price < 50000000) AS price_2_5cr,
  -- 5-8Cr: 50M - 80M
  COUNT(*) FILTER (WHERE price >= 50000000 AND price < 80000000) AS price_5_8cr,
  -- 8-10Cr: 80M - 100M
  COUNT(*) FILTER (WHERE price >= 80000000 AND price < 100000000) AS price_8_10cr,
  -- 10-12Cr: 100M - 120M
  COUNT(*) FILTER (WHERE price >= 100000000 AND price < 120000000) AS price_10_12cr,
  -- 12-15Cr: 120M - 150M
  COUNT(*) FILTER (WHERE price >= 120000000 AND price < 150000000) AS price_12_15cr,
  -- 15Cr+: 150M and above
  COUNT(*) FILTER (WHERE price >= 150000000) AS price_15cr_plus,

  -- Area Range Distribution (sqft)
  COUNT(*) FILTER (WHERE area_sqft >= 0 AND area_sqft < 500) AS area_0_500,
  COUNT(*) FILTER (WHERE area_sqft >= 500 AND area_sqft < 1000) AS area_500_1000,
  COUNT(*) FILTER (WHERE area_sqft >= 1000 AND area_sqft < 1500) AS area_1000_1500,
  COUNT(*) FILTER (WHERE area_sqft >= 1500 AND area_sqft < 2000) AS area_1500_2000,
  COUNT(*) FILTER (WHERE area_sqft >= 2000 AND area_sqft < 3000) AS area_2000_3000,
  COUNT(*) FILTER (WHERE area_sqft >= 3000 AND area_sqft < 4000) AS area_3000_4000,
  COUNT(*) FILTER (WHERE area_sqft >= 4000 AND area_sqft < 5000) AS area_4000_5000,
  COUNT(*) FILTER (WHERE area_sqft >= 5000) AS area_5000_plus,

  -- Property Type Distribution (case-insensitive)
  COUNT(*) FILTER (WHERE LOWER(property_type) LIKE '%apartment%') AS type_apartment,
  COUNT(*) FILTER (WHERE LOWER(property_type) LIKE '%villa%') AS type_villa,
  COUNT(*) FILTER (WHERE LOWER(property_type) LIKE '%independent%') AS type_independent_house,
  COUNT(*) FILTER (WHERE LOWER(property_type) LIKE '%plot%') AS type_plot,

  -- BHK Distribution (from bedroom_count)
  COUNT(*) FILTER (WHERE bedroom_count = 1) AS bhk_1,
  COUNT(*) FILTER (WHERE bedroom_count = 2) AS bhk_2,
  COUNT(*) FILTER (WHERE bedroom_count = 3) AS bhk_3,
  COUNT(*) FILTER (WHERE bedroom_count = 4) AS bhk_4,

  -- Summary Statistics
  AVG(price) FILTER (WHERE price IS NOT NULL AND price > 0) AS avg_price,
  AVG(area_sqft) FILTER (WHERE area_sqft IS NOT NULL AND area_sqft > 0) AS avg_area_sqft,
  MIN(price) FILTER (WHERE price IS NOT NULL AND price > 0) AS min_price,
  MAX(price) FILTER (WHERE price IS NOT NULL AND price > 0) AS max_price

FROM public.whatsapp_listings_relevant
WHERE location IS NOT NULL
GROUP BY LOWER(TRIM(location))
ORDER BY total_listings DESC;

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_whatsapp_listing_price ON public.whatsapp_listing_data(price);
CREATE INDEX IF NOT EXISTS idx_whatsapp_listing_area_sqft ON public.whatsapp_listing_data(area_sqft);
CREATE INDEX IF NOT EXISTS idx_whatsapp_listing_bedroom_count ON public.whatsapp_listing_data(bedroom_count);
CREATE INDEX IF NOT EXISTS idx_whatsapp_listing_location ON public.whatsapp_listing_data(location);

-- Add comment
COMMENT ON VIEW public.locality_distributions IS
'Pre-computed distribution statistics per locality. Groups whatsapp_listings_relevant by location with counts for price ranges (5-8Cr to 15Cr+), area ranges (0-500 to 2000+ sqft), property types (Apartment, Villa, Independent House, Plot), and BHK configurations (1-4). Normalized location names (lowercase, trimmed). Used for /api/distributions/localities endpoint.';
