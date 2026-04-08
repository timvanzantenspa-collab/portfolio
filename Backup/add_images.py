#!/usr/bin/env python3
"""
Helper script to add images to your portfolio.
Usage: python add_images.py /path/to/image1.jpg /path/to/image2.png
"""

import sys
import shutil
from pathlib import Path

STATIC_FOLDER = Path(__file__).parent / 'static'

def add_image(image_path):
    """Copy image to static folder"""
    image_file = Path(image_path)
    
    if not image_file.exists():
        print(f"❌ File not found: {image_path}")
        return False
    
    if image_file.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        print(f"❌ Unsupported format: {image_file.suffix}")
        return False
    
    dest_path = STATIC_FOLDER / image_file.name
    
    if dest_path.exists():
        print(f"⚠️  File already exists: {image_file.name}")
        response = input("Overwrite? (y/n): ").lower()
        if response != 'y':
            return False
    
    try:
        shutil.copy2(image_file, dest_path)
        print(f"✅ Added: {image_file.name}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python add_images.py /path/to/image1.jpg [/path/to/image2.png] ...")
        sys.exit(1)
    
    success_count = 0
    for image_path in sys.argv[1:]:
        if add_image(image_path):
            success_count += 1
    
    print(f"\n✨ Added {success_count}/{len(sys.argv)-1} images")
    print(f"📁 Images saved to: {STATIC_FOLDER}")
