#!/usr/bin/env python3
"""Convert all carousel images to WebP format"""

import json
import os
from pathlib import Path
from PIL import Image

STATIC_FOLDER = Path(__file__).parent / 'static'
CAPTIONS_FILE = Path(__file__).parent / 'captions.json'

def convert_image_to_webp(image_path):
    """Convert an image to WebP format and return the new filename"""
    try:
        img = Image.open(image_path)
        
        # Create webp filename (replace extension with .webp)
        webp_path = image_path.with_suffix('.webp')
        
        # Convert RGBA to RGB if necessary (WebP can handle both but some apps prefer RGB)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB with white background for transparency
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            rgb_img.save(webp_path, 'WEBP', quality=85)
        else:
            img.save(webp_path, 'WEBP', quality=85)
        
        # Delete the original file after successful conversion
        image_path.unlink()
        return webp_path.name
    except Exception as e:
        print(f"Error converting {image_path}: {e}")
        return None

def main():
    """Main conversion function"""
    
    # Load captions to get target filenames
    with open(CAPTIONS_FILE, 'r', encoding='utf-8') as f:
        captions = json.load(f)
    
    # Get all unique WebP filenames we're targeting
    target_files = list(captions.keys())
    
    print(f"Found {len(target_files)} target WebP filenames in captions.json")
    print("Converting original images to WebP...")
    
    converted_count = 0
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    # Scan static folder for original images
    for file in STATIC_FOLDER.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            # Convert the image
            webp_filename = convert_image_to_webp(file)
            
            if webp_filename:
                converted_count += 1
                print(f"✓ Converted: {file.name} → {webp_filename}")
            else:
                print(f"✗ Failed to convert: {file.name}")
    
    print(f"\n✓ Done! Converted {converted_count} images to WebP")

if __name__ == '__main__':
    main()
