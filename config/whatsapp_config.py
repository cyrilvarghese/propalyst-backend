"""
WhatsApp Processing Configuration

Centralized configuration for WhatsApp message processing.
"""

# ============================================================================
# Date Filtering Configuration
# ============================================================================

# Number of days to look back for "recent" messages
# Only messages within this window are processed by LLM
# Older messages are kept in DB but not sent to LLM
RECENT_MESSAGES_CUTOFF_DAYS = 180  # 1year

# ============================================================================
# Processing Configuration
# ============================================================================

# Batch size for chunked database operations
QUERY_CHUNK_SIZE = 200  # For hash lookups
INSERT_CHUNK_SIZE = 100  # For message inserts
