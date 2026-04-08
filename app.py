#Runs from timvanzantenspam@gmail.com on render, on timvanzantenspa@gmail.com github
from flask import Flask, render_template, jsonify
from PIL import Image
import os
import shutil
from pathlib import Path
import json

# Increase PIL image size limit for large files (safe since processing own files)
Image.MAX_IMAGE_PIXELS = None

app = Flask(__name__)
STATIC_FOLDER = Path(__file__).parent / 'static'
CACHE_FOLDER = Path(__file__).parent / 'static' / '.cache'
CAPTIONS_FILE = Path(__file__).parent / 'captions.json'
IMAGE_ORDER_FILE = Path(__file__).parent / 'image_order.json'
CAROUSELS_FILE = Path(__file__).parent / 'carousels.json'
CACHE_FOLDER.mkdir(exist_ok=True)

# Maximum image width for downscaled versions
MAX_WIDTH = 500
QUALITY = 85

def load_captions():
    """Load captions from JSON file"""
    if CAPTIONS_FILE.exists():
        try:
            with open(CAPTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_carousels():
    """Load carousel groupings from JSON file"""
    if CAROUSELS_FILE.exists():
        try:
            with open(CAROUSELS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def parse_date(date_str):
    """Parse date string and return sortable tuple (year, month).
    Examples:
    - "May 2024" -> (2024, 5)
    - "2024" -> (2024, 1)
    - "2015-2020" -> (2015, 1)
    - "April 2018" -> (2018, 4)
    """
    if not date_str:
        return (0, 0)  # Unknown dates go to bottom
    
    # List of month names
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    
    # Handle date ranges like "2015-2020" - use first year
    if '-' in date_str and date_str.count('-') == 1:
        parts = date_str.split('-')
        if parts[0].isdigit():
            date_str = parts[0]
    
    # Parse the date string
    words = date_str.lower().strip().split()
    year = None
    month = 1  # Default to January
    
    for word in words:
        if word.isdigit() and len(word) == 4:
            year = int(word)
        else:
            # Check if it's a month name
            for month_name, month_num in months.items():
                if month_name in word:
                    month = month_num
                    break
    
    if year is None:
        return (0, 0)
    
    return (year, month)

def get_image_files():
    """Get all image files sorted by date (newest first), using WebP versions from captions.json"""
    # Load captions to get all image filenames and date info
    captions = load_captions()
    
    # Filter to only files that actually exist in static folder
    existing_files = []
    for filename in captions.keys():
        if (STATIC_FOLDER / filename).exists():
            existing_files.append(filename)
    
    # Sort images by date (newest first)
    def get_sort_key(filename):
        caption = captions.get(filename, {})
        date_str = caption.get('date', '')
        year, month = parse_date(date_str)
        # Return negative to sort descending (newest first)
        return (-year, -month, filename)
    
    sorted_images = sorted(existing_files, key=get_sort_key)
    
    # Filter out carousel member images (keep only primary image per carousel)
    carousels_map = load_carousels()
    carousel_primaries = {}
    
    # Identify the primary image for each carousel using JSON order (first image in each carousel)
    for img, carousel_id in carousels_map.items():
        if carousel_id not in carousel_primaries:
            carousel_primaries[carousel_id] = img
    
    # Filter to keep only primary images, sorted by date
    filtered_images = []
    for img in sorted_images:
        if img not in carousels_map:
            # Image is not in any carousel, always show it
            filtered_images.append(img)
        elif carousel_primaries.get(carousels_map[img]) == img:
            # Image is the primary image of its carousel, show it
            filtered_images.append(img)
        # All other carousel member images are hidden from the grid
    
    return filtered_images

def downscale_image(filename):
    """Return WebP image URL. If file is already WebP in static, serve it directly."""
    original_path = STATIC_FOLDER / filename
    
    # If the WebP file exists in static folder, serve it directly
    if filename.lower().endswith('.webp') and original_path.exists():
        return f'/static/{filename}'
    
    # Create cache filename with .webp extension
    cache_filename = filename.rsplit('.', 1)[0] + '.webp'
    cache_path = CACHE_FOLDER / cache_filename
    
    # If cached WebP version exists, return it
    if cache_path.exists():
        return f'/static/.cache/{cache_filename}'
    
    # If original file doesn't exist, return a fallback
    if not original_path.exists():
        print(f"Warning: File not found: {filename}")
        return f'/static/{filename}'
    
    try:
        # Open image (works with PNG, JPG, GIF, etc.)
        img = Image.open(original_path)
        is_gif = filename.lower().endswith('.gif')
        
        # Handle GIF animations - extract frames with limits
        frames = []
        durations = []
        
        if is_gif:
            try:
                # Get total number of frames
                num_frames = img.n_frames
                
                # Limit frames to prevent memory issues (max 160 frames, sample if needed)
                max_frames = 160
                frame_step = max(1, num_frames // max_frames)
                
                if num_frames > max_frames:
                    print(f"GIF {filename} has {num_frames} frames, sampling every {frame_step}th frame")
                
                # Extract frames
                frame_index = 0
                for frame_idx in range(0, num_frames, frame_step):
                    try:
                        img.seek(frame_idx)
                        
                        # Convert frame to RGB
                        frame = img.convert('RGB')
                        
                        # Downscale if too large
                        if frame.width > MAX_WIDTH:
                            ratio = MAX_WIDTH / frame.width
                            new_height = int(frame.height * ratio)
                            frame = frame.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
                        
                        frames.append(frame)
                        durations.append(img.info.get('duration', 100))
                        frame_index += 1
                    except Exception as frame_error:
                        print(f"Error processing frame {frame_idx} in {filename}: {frame_error}")
                        continue
                
                if not frames:
                    # If all frames failed, use first frame as static image
                    img.seek(0)
                    frame = img.convert('RGB')
                    if frame.width > MAX_WIDTH:
                        ratio = MAX_WIDTH / frame.width
                        new_height = int(frame.height * ratio)
                        frame = frame.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
                    frames = [frame]
                    durations = [100]
                    
            except Exception as gif_error:
                print(f"Error reading GIF {filename}: {gif_error}")
                # Fallback: convert to static image
                img.seek(0)
                frame = img.convert('RGB')
                if frame.width > MAX_WIDTH:
                    ratio = MAX_WIDTH / frame.width
                    new_height = int(frame.height * ratio)
                    frame = frame.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
                frames = [frame]
                durations = [100]
        else:
            # For static images, just process normally
            # Convert RGBA to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            else:
                img = img.convert('RGB')
            
            # Downscale if too large
            if img.width > MAX_WIDTH:
                ratio = MAX_WIDTH / img.width
                new_height = int(img.height * ratio)
                img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
            
            frames = [img]
            durations = [100]
        
        # Save as optimized WebP
        if len(frames) > 1:
            # Animated WebP
            frames[0].save(
                cache_path,
                'WEBP',
                quality=QUALITY,
                method=6,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0
            )
        else:
            # Static WebP
            frames[0].save(cache_path, 'WEBP', quality=QUALITY, method=6)
        
        return f'/static/.cache/{cache_filename}'
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        import traceback
        traceback.print_exc()
        return f'/static/{filename}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/robots.txt')
def robots():
    with open(Path(__file__).parent / 'robots.txt', 'r') as f:
        return f.read(), 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    with open(Path(__file__).parent / 'sitemap.xml', 'r') as f:
        return f.read(), 200, {'Content-Type': 'application/xml'}

@app.route('/api/images')
def get_images():
    """API endpoint to get all images"""
    images = get_image_files()
    image_data = []
    
    for img in images:
        cached_url = downscale_image(img)
        image_data.append({
            'filename': img,
            'url': cached_url
        })
    
    return jsonify(image_data)

@app.route('/api/captions')
def get_captions():
    """API endpoint to get image captions"""
    return jsonify(load_captions())

@app.route('/api/carousel/<filename>')
def get_carousel(filename):
    """API endpoint to get carousel images for a specific image with WebP URLs"""
    carousels_map = load_carousels()
    carousel_id = carousels_map.get(filename)
    
    if not carousel_id:
        # If image has no carousel, return just that image with its URL
        if (STATIC_FOLDER / filename).exists():
            url = downscale_image(filename)
            return jsonify({'primary': filename, 'images': [{'filename': filename, 'url': url}]})
        return jsonify({'primary': filename, 'images': []})
    
    # Find all images in this carousel, preserving the order from carousels.json
    carousel_images = []
    for img, cid in carousels_map.items():
        if cid == carousel_id:
            carousel_images.append(img)
    
    # The primary image is the first one in the carousel
    primary_image = carousel_images[0] if carousel_images else filename
    
    # Return carousel images with their WebP URLs in the order they appear in carousels.json
    # Only include images that actually exist in the static folder
    carousel_data = []
    for img in carousel_images:
        if (STATIC_FOLDER / img).exists():
            url = downscale_image(img)
            carousel_data.append({'filename': img, 'url': url})
    
    return jsonify({'primary': primary_image, 'images': carousel_data})

@app.errorhandler(404)
def not_found(error):
    """Redirect 404 errors to home page"""
    return render_template('index.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False)
