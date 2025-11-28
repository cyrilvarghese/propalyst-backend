"""
Check for Duplicate Listings in whatsapp_listing_data

Analyzes extracted listings and shows duplicates based on raw_message hash.

Run with: python check_listing_duplicates.py
"""

import hashlib
from collections import defaultdict
from services.supabase_service import SupabaseService


def calculate_message_hash(raw_message: str) -> str:
    """Calculate MD5 hash of raw message text"""
    return hashlib.md5(raw_message.encode('utf-8')).hexdigest()


def main():
    print("="*80)
    print("WhatsApp Listing Data - Duplicate Checker")
    print("="*80)

    # Get Supabase client
    client = SupabaseService._get_client()
    print("✓ Connected to Supabase\n")

    # Read all listings (fetch in batches to avoid default 1000 limit)
    print("Reading all listings from whatsapp_listing_data...")
    all_listings = []
    batch_size = 1000
    offset = 0

    while True:
        response = client.table("whatsapp_listing_data")\
            .select("id, raw_message, message_type, location, price, agent_name, created_at, source_raw_message_id")\
            .range(offset, offset + batch_size - 1)\
            .execute()

        batch = response.data or []
        if not batch:
            break

        all_listings.extend(batch)
        offset += batch_size
        print(f"  Fetched {len(all_listings)} listings so far...")

        if len(batch) < batch_size:
            break  # Last batch

    print(f"✓ Found {len(all_listings)} total listings\n")

    if len(all_listings) == 0:
        print("No listings found")
        return

    # Group by raw_message hash
    print("Grouping by raw_message hash...")
    hash_groups = defaultdict(list)

    for listing in all_listings:
        raw_message = listing.get('raw_message', '')
        message_hash = calculate_message_hash(raw_message)

        hash_groups[message_hash].append(listing)

    # Find duplicate groups
    duplicate_groups = {h: listings for h, listings in hash_groups.items() if len(listings) > 1}

    print(f"✓ Found {len(duplicate_groups)} groups with duplicates\n")

    if len(duplicate_groups) == 0:
        print("✅ No duplicates found!")
        return

    # Show first 5 duplicate groups
    print("="*80)
    print(f"Showing First 5 Duplicate Groups (out of {len(duplicate_groups)} total)")
    print("="*80)

    for idx, (hash_val, listings) in enumerate(list(duplicate_groups.items())[:5], 1):
        print(f"\n{'='*80}")
        print(f"DUPLICATE GROUP #{idx} (Hash: {hash_val[:16]}...)")
        print(f"{'='*80}")
        print(f"Found {len(listings)} listings with identical raw_message:\n")

        for listing_idx, listing in enumerate(listings, 1):
            print(f"  Listing {listing_idx}/{len(listings)}:")
            print(f"    ID:                  {listing.get('id')}")
            print(f"    Source Raw Msg ID:   {listing.get('source_raw_message_id')}")
            print(f"    Message Type:        {listing.get('message_type')}")
            print(f"    Location:            {listing.get('location')}")
            print(f"    Price:               {listing.get('price')}")
            print(f"    Agent:               {listing.get('agent_name')}")
            print(f"    Created At:          {listing.get('created_at')}")
            print(f"    Raw Message Preview: {listing.get('raw_message', '')[:150]}...")
            print()

        # Show if texts are truly identical
        texts = [listing.get('raw_message', '') for listing in listings]
        if len(set(texts)) == 1:
            print(f"  ✓ Confirmed: All {len(listings)} listings have IDENTICAL raw_message")
        else:
            print(f"  ⚠️  Warning: Listings have DIFFERENT raw_message (hash collision?)")

        # Check if duplicates are from same source (expected from splitting)
        source_ids = [listing.get('source_raw_message_id') for listing in listings]
        unique_sources = set(filter(None, source_ids))

        if len(unique_sources) == 1:
            print(f"  ℹ️  Same source_raw_message_id: {list(unique_sources)[0][:16]}...")
            print(f"  → This is EXPECTED (message was split into {len(listings)} listings)")
        elif len(unique_sources) > 1:
            print(f"  ⚠️  Different source_raw_message_id values!")
            print(f"  → This is UNEXPECTED (real duplicate, not from splitting)")
            print(f"  → Source IDs: {[s[:16] + '...' for s in unique_sources]}")
        else:
            print(f"  ⚠️  No source_raw_message_id (legacy data?)")

        print(f"\n  Full raw_message of first listing:")
        print(f"  {'-'*76}")
        print(f"  {listings[0].get('raw_message', '')[:500]}")
        print(f"  {'-'*76}")

    # Summary
    print(f"\n{'='*80}")
    print("Summary")
    print("="*80)
    print(f"Total listings:        {len(all_listings)}")
    print(f"Unique listings:       {len(hash_groups)}")
    print(f"Duplicate groups:      {len(duplicate_groups)}")

    # Count total duplicates to delete (if needed)
    total_duplicates = sum(len(listings) - 1 for listings in duplicate_groups.values())
    print(f"Duplicates found:      {total_duplicates}")
    print(f"Listings after cleanup: {len(all_listings) - total_duplicates}")
    print("="*80)

    # Categorize duplicates: expected (from splitting) vs unexpected (real duplicates)
    print(f"\nDuplicate Analysis:")
    expected_duplicates = 0
    unexpected_duplicates = 0

    for listings in duplicate_groups.values():
        source_ids = [l.get('source_raw_message_id') for l in listings]
        unique_sources = set(filter(None, source_ids))

        if len(unique_sources) == 1:
            # Same source = expected (from splitting)
            expected_duplicates += len(listings) - 1
        else:
            # Different sources = unexpected (real duplicates)
            unexpected_duplicates += len(listings) - 1

    print(f"  Expected (from splitting):  {expected_duplicates}")
    print(f"  Unexpected (real duplicates): {unexpected_duplicates}")

    # Breakdown by message type
    print(f"\nDuplicates by message type:")
    type_counts = defaultdict(int)
    for listings in duplicate_groups.values():
        for listing in listings[1:]:  # Count duplicates only
            msg_type = listing.get('message_type', 'unknown')
            type_counts[msg_type] += 1

    for msg_type, count in sorted(type_counts.items()):
        print(f"  {msg_type}: {count}")

    if unexpected_duplicates > 0:
        print(f"\n⚠️  Warning: {unexpected_duplicates} REAL duplicates found (different source_raw_message_id)")
        print("These should be investigated and potentially removed.")
    else:
        print(f"\n✅ All duplicates are expected (from message splitting)")
        print("No action needed.")


if __name__ == "__main__":
    main()
