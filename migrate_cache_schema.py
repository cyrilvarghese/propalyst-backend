#!/usr/bin/env python3
"""
Migrate existing cache file to new array-based schema
Old: { "url": [ properties ] } or { "url": { "type": "provider", "source_url": "url", "scraped_at": "timestamp", "data": [ properties ] } }
New: [ { "type": "provider", "source_url": "url", "scraped_at": "timestamp", "data": [ properties ] }, ... ]
"""

import json
from datetime import datetime
from pathlib import Path

def migrate_cache():
    cache_path = Path(__file__).parent / "data" / "scraped_properties.json"

    if not cache_path.exists():
        print(f"Cache file not found: {cache_path}")
        return

    print(f"Reading cache file: {cache_path}")
    with open(cache_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    # If already an array, it's already migrated
    if isinstance(old_data, list):
        print(f"Cache file is already in array format with {len(old_data)} entries")
        print("No migration needed.")
        return

    print(f"Found {len(old_data)} URLs to migrate")

    # Migrate to new array-based schema
    new_data = []
    timestamp = datetime.now().isoformat()

    for url, entry in old_data.items():
        # Determine source based on URL
        if "squareyards" in url.lower():
            source = "squareyards"
        elif "magicbricks" in url.lower():
            source = "magicbricks"
        else:
            source = "unknown"

        # Handle both old and intermediate formats
        if isinstance(entry, dict) and "data" in entry:
            # Already has metadata structure
            properties = entry.get("data", [])
        elif isinstance(entry, list):
            # Old format without metadata
            properties = entry
        else:
            properties = []

        # Create new entry with metadata
        new_entry = {
            "type": source,
            "source_url": url,
            "scraped_at": entry.get("scraped_at", timestamp) if isinstance(entry, dict) else timestamp,
            "data": properties
        }

        new_data.append(new_entry)
        print(f"  ✓ Migrated {source}: {url[:60]}...")

    # Backup old file
    backup_path = cache_path.with_suffix('.backup.json')
    print(f"\nBacking up old file to: {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(old_data, f, indent=2, ensure_ascii=False)

    # Write new file as array
    print(f"Writing migrated cache to: {cache_path}")
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Migration complete!")
    print(f"  - Old entries: {len(old_data)}")
    print(f"  - New entries: {len(new_data)}")
    print(f"  - Backup saved to: {backup_path}")

if __name__ == "__main__":
    migrate_cache()
