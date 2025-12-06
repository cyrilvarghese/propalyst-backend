-- View: properties_with_agent
-- =============================
-- Combines properties table with agent details from profiles table
-- This ensures all properties queries automatically include agent information
--
-- Purpose:
--   - Single source of truth for properties + agent JOIN
--   - Cleaner service code (no JOIN logic in Python)
--   - Database-level optimization and caching
--   - Consistent agent data across all queries
--
-- Usage:
--   Instead of: SELECT * FROM properties
--   Use:        SELECT * FROM properties_with_agent
--
-- Fields added from profiles table:
--   - agent_name (profiles.full_name)
--   - agent_contact (profiles.phone)
--   - agent_email (profiles.email)
--   - agent_company (profiles.company_name)
--   - agent_avatar (profiles.avatar_url)
--   - agent_vanity_url (profiles.vanity_url)
--
-- Note: Uses LEFT JOIN to ensure all properties are returned even if
--       agent profile is missing or deleted.

CREATE OR REPLACE VIEW public.properties_with_agent AS
SELECT
    properties.*,
    profiles.full_name as agent_name,
    profiles.phone as agent_contact,
    profiles.email as agent_email,
    profiles.company_name as agent_company,
    profiles.avatar_url as agent_avatar,
    profiles.vanity_url as agent_vanity_url
FROM public.properties
LEFT JOIN public.profiles ON properties.user_id = profiles.id;

-- Add comment for documentation
COMMENT ON VIEW public.properties_with_agent IS
'Properties with agent details from profiles table. Use this view instead of raw properties table to get complete listing information including agent contact details. LEFT JOIN ensures all properties are returned even if agent profile is missing.';
