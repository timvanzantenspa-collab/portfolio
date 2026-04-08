#!/usr/bin/env python3
"""Sync captions.json with carousels.json filenames"""

import json
from pathlib import Path

CAPTIONS_FILE = Path(__file__).parent / 'captions.json'
CAROUSELS_FILE = Path(__file__).parent / 'carousels.json'

# Load both files
with open(CAPTIONS_FILE, 'r', encoding='utf-8') as f:
    captions = json.load(f)

with open(CAROUSELS_FILE, 'r', encoding='utf-8') as f:
    carousels = json.load(f)

carousel_filenames = set(carousels.keys())
caption_filenames = set(captions.keys())

print("Checking for mismatches...")
print(f"\nCarousel entries: {len(carousel_filenames)}")
print(f"Caption entries: {len(caption_filenames)}")

# Find captions that don't have corresponding carousel entries
orphaned_captions = caption_filenames - carousel_filenames
if orphaned_captions:
    print(f"\n⚠️  Captions with no carousel entry ({len(orphaned_captions)}):")
    for filename in sorted(orphaned_captions):
        print(f"  - {filename}")

# Find carousel entries that don't have captions
missing_captions = carousel_filenames - caption_filenames
if missing_captions:
    print(f"\n⚠️  Carousel entries without captions ({len(missing_captions)}):")
    for filename in sorted(missing_captions):
        print(f"  - {filename}")

# Update captions to only include carousel entries
synced_captions = {k: v for k, v in captions.items() if k in carousel_filenames}

# Save synced captions
with open(CAPTIONS_FILE, 'w', encoding='utf-8') as f:
    json.dump(synced_captions, f, indent=4, ensure_ascii=False)

print(f"\n✓ Synced captions.json - removed {len(orphaned_captions)} orphaned entries")
if missing_captions:
    print(f"\n⚠️  Add captions for {len(missing_captions)} new carousel entries:")
    for filename in sorted(missing_captions):
        print(f'    "{filename}": {{"title": "...", "date": "...", "type": "...", ...}},')
