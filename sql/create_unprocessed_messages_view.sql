-- Create view for unprocessed WhatsApp messages
-- This view returns messages from crea_wapp that don't have corresponding entries in whatsapp_listing_data
-- Uses LEFT JOIN for efficient filtering at database level

CREATE OR REPLACE VIEW unprocessed_whatsapp_messages AS
SELECT
    cw.id,
    cw.message_date,
    cw.agent_contact,
    cw.agent_name,
    cw.company_name,
    cw.raw_message,
    cw.created_at
FROM
    crea_wapp cw
LEFT JOIN
    whatsapp_listing_data wld ON cw.id = wld.source_message_id
WHERE
    wld.source_message_id IS NULL
ORDER BY
    cw.message_date DESC;

-- Usage examples:
--
-- Get all unprocessed messages:
-- SELECT * FROM unprocessed_whatsapp_messages;
--
-- Get first 100 unprocessed messages:
-- SELECT * FROM unprocessed_whatsapp_messages LIMIT 100;
--
-- Get count of unprocessed messages:
-- SELECT COUNT(*) FROM unprocessed_whatsapp_messages;
--
-- Get unprocessed messages with pagination:
-- SELECT * FROM unprocessed_whatsapp_messages LIMIT 100 OFFSET 0;
