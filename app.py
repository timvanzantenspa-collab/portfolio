#Runs from timvanzantenspam@gmail.com on render, on timvanzantenspa@gmail.com github
#Passw in render: ADMIN_PASSWORD
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, send_file, send_from_directory
from PIL import Image, ImageOps
import markdown
import nh3
from datetime import timedelta
import os
import shutil
from pathlib import Path
import json
import base64
import hashlib
import hmac
import secrets
import subprocess
import threading
import time
import re
from functools import wraps
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from werkzeug.utils import secure_filename
from generate_jsonld import generate_all_schemas, load_resume_content, get_schema_script_tags, get_about_page_script_tags

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '').lower() in {'1', 'true', 'yes'} or bool(os.environ.get('RENDER')),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=64 * 1024 * 1024,
)
STATIC_FOLDER = Path(__file__).parent / 'static'
CACHE_FOLDER = Path(__file__).parent / 'static' / '.cache'
CAPTIONS_FILE = Path(__file__).parent / 'captions.json'
IMAGE_ORDER_FILE = Path(__file__).parent / 'image_order.json'
CAROUSELS_FILE = Path(__file__).parent / 'carousels.json'
PROJECT_GALLERIES_FILE = Path(__file__).parent / 'project_galleries.json'
IMAGE_LINKS_FILE = Path(__file__).parent / 'image_links.json'
CACHE_FOLDER.mkdir(exist_ok=True)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
GITHUB_REPOSITORY = os.environ.get('GITHUB_REPOSITORY', 'timvanzantenspa-collab/portfolio')
ADMIN_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ADMIN_VIDEO_EXTENSIONS = {'.mp4', '.webm'}
ADMIN_MEDIA_EXTENSIONS = ADMIN_IMAGE_EXTENSIONS | ADMIN_VIDEO_EXTENSIONS
MAX_IMAGE_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_GIF_SOURCE_PIXELS = 120_000_000
MAX_GIF_TOTAL_PIXELS = 1_000_000_000
ADMIN_WRITE_LOCK = threading.Lock()
ADMIN_LOGIN_LOCK = threading.Lock()
ADMIN_LOGIN_FAILURES = {}
ADMIN_LOGIN_FAILURE_LIMIT = 5
ADMIN_LOGIN_FAILURE_WINDOW = 15 * 60
DESCRIPTION_MARKDOWN_EXTENSIONS = ['extra', 'nl2br', 'sane_lists']
DESCRIPTION_ALLOWED_TAGS = {
    'a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3', 'h4',
    'h5', 'h6', 'hr', 'li', 'ol', 'p', 'pre', 'strong', 'sub', 'sup', 'table',
    'tbody', 'td', 'th', 'thead', 'tr', 'ul',
}
DESCRIPTION_ALLOWED_ATTRIBUTES = {'a': {'href', 'title'}}

class GitPushUnavailable(RuntimeError):
    pass

# Load JSON-LD schemas on startup
try:
    resume_content = load_resume_content()
    jsonld_schemas = generate_all_schemas(resume_content)
    homepage_scripts = get_schema_script_tags(jsonld_schemas)
    about_page_scripts = get_about_page_script_tags(jsonld_schemas)
except Exception as e:
    print(f"Warning: Could not load JSON-LD schemas: {e}")
    homepage_scripts = ""
    about_page_scripts = ""


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

def load_project_galleries():
    if PROJECT_GALLERIES_FILE.exists():
        try:
            with PROJECT_GALLERIES_FILE.open('r', encoding='utf-8') as data_file:
                value = json.load(data_file)
            if isinstance(value, dict):
                return {
                    cover: list(dict.fromkeys(images))
                    for cover, images in value.items()
                    if isinstance(cover, str) and isinstance(images, list)
                    and all(isinstance(image, str) for image in images)
                }
        except (OSError, json.JSONDecodeError):
            return {}

    captions = load_captions()
    carousels = load_carousels()
    primary_by_group = {}
    for image, carousel_id in carousels.items():
        primary_by_group.setdefault(carousel_id, image)
    galleries = {}
    for cover in captions:
        carousel_id = carousels.get(cover)
        if not carousel_id:
            galleries[cover] = []
        elif primary_by_group.get(carousel_id) == cover:
            galleries[cover] = [
                image for image, group_id in carousels.items()
                if group_id == carousel_id and image != cover
            ]
    return galleries

def rebuild_carousels(project_galleries):
    carousels = {}
    for cover, gallery_images in project_galleries.items():
        carousels.setdefault(cover, cover)
        for image in gallery_images:
            carousels.setdefault(image, cover)
    return carousels

def load_image_links():
    if IMAGE_LINKS_FILE.exists():
        try:
            with IMAGE_LINKS_FILE.open('r', encoding='utf-8') as data_file:
                value = json.load(data_file)
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
    return {}

def normalize_optional_http_url(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError('Image links must be text.')
    value = value.strip()
    if not value:
        return ''
    parsed = urlsplit(value)
    if len(value) > 2048 or parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('Image links must be valid http:// or https:// URLs no longer than 2,048 characters.')
    return value

def normalize_image_link_updates(value):
    if not isinstance(value, dict) or not isinstance(value.get('gallery', []), list):
        raise ValueError('Per-image links must contain a cover URL and a gallery list.')
    normalized = {
        'cover': normalize_optional_http_url(value.get('cover', '')),
        'gallery': [],
    }
    seen = set()
    for item in value.get('gallery', []):
        if not isinstance(item, dict):
            raise ValueError('A per-image link entry is invalid.')
        kind = item.get('kind')
        if kind == 'asset':
            identifier = item.get('filename')
            if not isinstance(identifier, str) or not identifier:
                raise ValueError('A linked gallery asset is invalid.')
        elif kind == 'upload':
            identifier = item.get('index')
            if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 0:
                raise ValueError('A linked gallery upload is invalid.')
        else:
            raise ValueError('A per-image link entry has an unknown media type.')
        key = (kind, identifier)
        if key in seen:
            raise ValueError('A gallery image has duplicate link data.')
        seen.add(key)
        normalized['gallery'].append({
            'kind': kind,
            'identifier': identifier,
            'url': normalize_optional_http_url(item.get('url', '')),
        })
    return normalized

def render_markdown_description(description):
    if not isinstance(description, str) or not description:
        return ''
    rendered = markdown.markdown(
        description,
        extensions=DESCRIPTION_MARKDOWN_EXTENSIONS,
        output_format='html5',
    )
    return nh3.clean(
        rendered,
        tags=DESCRIPTION_ALLOWED_TAGS,
        attributes=DESCRIPTION_ALLOWED_ATTRIBUTES,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer',
    )

def get_static_path(filename):
    """Resolve a filename only when it stays inside the static directory."""
    if not isinstance(filename, str) or Path(filename).name != filename:
        return None

    static_root = STATIC_FOLDER.resolve()
    candidate = (static_root / filename).resolve()
    try:
        candidate.relative_to(static_root)
    except ValueError:
        return None
    return candidate

def is_video_filename(filename):
    return Path(filename).suffix.lower() in ADMIN_VIDEO_EXTENSIONS

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

def get_image_files(include_unpublished=False):
    """Get all image files sorted by date (newest first), using WebP versions from captions.json"""
    # Load captions to get all image filenames and date info
    captions = load_captions()
    
    # Filter to only files that actually exist in static folder
    existing_files = []
    for filename in captions.keys():
        caption = captions.get(filename, {})
        if not include_unpublished and isinstance(caption, dict) and caption.get('published') is False:
            continue
        image_path = get_static_path(filename)
        if image_path is not None and image_path.is_file():
            existing_files.append(filename)
    
    # Sort images by date (newest first)
    def get_sort_key(filename):
        caption = captions.get(filename, {})
        date_str = caption.get('date', '')
        year, month = parse_date(date_str)
        # Return negative to sort descending (newest first)
        return (-year, -month, filename)
    
    sorted_images = sorted(existing_files, key=get_sort_key)
    
    gallery_members = {
        image
        for gallery_images in load_project_galleries().values()
        for image in gallery_images
    }
    return [image for image in sorted_images if image not in gallery_members]

def downscale_image(filename):
    """Return an optimized image URL or the original video URL."""
    original_path = get_static_path(filename)
    if original_path is None:
        return ''

    if is_video_filename(filename):
        return f'/static/{filename}'
    
    # If the WebP file exists in static folder, serve it directly
    if filename.lower().endswith('.webp') and original_path.exists():
        return f'/static/{filename}'
    
    # Create cache filename with .webp extension
    cache_filename = f'{Path(filename).stem}.webp'
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
    return render_template('index.html', jsonld_scripts=homepage_scripts)

@app.route('/about')
def about():
    return render_template('about.html', jsonld_scripts=about_page_scripts)

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return jsonify({'error': 'Set ADMIN_PASSWORD to enable the project editor.'}), 503
        if not session.get('admin_authenticated'):
            if request.path.startswith('/admin/api/'):
                return jsonify({'error': 'Please sign in again.'}), 401
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)
    return wrapped

@app.route('/gif-maker')
@admin_required
def gif_maker():
    return render_template('gif_maker.html')

@app.route('/admin/api/gif-maker', methods=['POST'])
@admin_required
def create_gif():
    uploads = request.files.getlist('images')
    if len(uploads) < 2:
        return jsonify({'error': 'Choose at least two images.'}), 400
    if len(uploads) > 100:
        return jsonify({'error': 'A GIF can contain up to 100 images.'}), 400

    duration = request.form.get('duration', 200, type=int)
    if duration is None or not 50 <= duration <= 1000:
        return jsonify({'error': 'Frame duration must be between 50 and 1000 milliseconds.'}), 400

    total_bytes = 0
    total_pixels = 0
    canvas_width = 0
    canvas_height = 0
    try:
        for upload in uploads:
            upload.stream.seek(0, os.SEEK_END)
            upload_size = upload.stream.tell()
            total_bytes += upload_size
            if upload_size > 16 * 1024 * 1024 or total_bytes > 48 * 1024 * 1024:
                return jsonify({'error': 'Images must be under 16 MB each and 48 MB total.'}), 413

            upload.stream.seek(0)
            with Image.open(upload.stream) as source:
                width, height = source.size
                image_pixels = width * height
                total_pixels += image_pixels
                if image_pixels > MAX_GIF_SOURCE_PIXELS:
                    return jsonify({'error': 'An image exceeds the 120 megapixel processing limit.'}), 400
                if total_pixels > MAX_GIF_TOTAL_PIXELS:
                    return jsonify({'error': 'The selected images exceed the total processing limit. Use fewer or smaller images.'}), 400

                if source.getexif().get(274) in {5, 6, 7, 8}:
                    width, height = height, width
                scale = min(1, 640 / max(width, height))
                canvas_width = max(canvas_width, round(width * scale))
                canvas_height = max(canvas_height, round(height * scale))
            upload.stream.seek(0)

        canvas_size = (max(1, canvas_width), max(1, canvas_height))
        animation_frames = []
        for upload in uploads:
            with Image.open(upload.stream) as source:
                source.thumbnail((640, 640), Image.Resampling.LANCZOS)
                frame = ImageOps.exif_transpose(source).convert('RGBA')
                frame.thumbnail(canvas_size, Image.Resampling.LANCZOS)
                canvas = Image.new('RGB', canvas_size, 'white')
                canvas.paste(
                    frame,
                    ((canvas.width - frame.width) // 2, (canvas.height - frame.height) // 2),
                    frame.getchannel('A'),
                )
                animation_frames.append(canvas.quantize(colors=128, dither=Image.Dither.NONE))
    except (Image.DecompressionBombError, Image.UnidentifiedImageError, OSError, ValueError):
        return jsonify({'error': 'One or more files are not valid, supported images.'}), 400

    output = BytesIO()
    animation_frames[0].save(
        output,
        format='GIF',
        save_all=True,
        append_images=animation_frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
        disposal=2,
    )
    output.seek(0)
    response = send_file(
        output,
        mimetype='image/gif',
        as_attachment=True,
        download_name='frame-animation.gif',
        max_age=0,
    )
    response.headers['Cache-Control'] = 'no-store'
    return response

def admin_csrf_token():
    if 'admin_csrf' not in session:
        session['admin_csrf'] = secrets.token_urlsafe(32)
    return session['admin_csrf']

def valid_admin_csrf():
    supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
    expected = session.get('admin_csrf', '')
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))

def login_failure_count(client_address):
    now = time.monotonic()
    with ADMIN_LOGIN_LOCK:
        attempts = [
            attempt for attempt in ADMIN_LOGIN_FAILURES.get(client_address, [])
            if now - attempt < ADMIN_LOGIN_FAILURE_WINDOW
        ]
        if attempts:
            ADMIN_LOGIN_FAILURES[client_address] = attempts
        else:
            ADMIN_LOGIN_FAILURES.pop(client_address, None)
        return len(attempts)

def record_login_failure(client_address):
    now = time.monotonic()
    with ADMIN_LOGIN_LOCK:
        attempts = [
            attempt for attempt in ADMIN_LOGIN_FAILURES.get(client_address, [])
            if now - attempt < ADMIN_LOGIN_FAILURE_WINDOW
        ]
        attempts.append(now)
        ADMIN_LOGIN_FAILURES[client_address] = attempts
        return len(attempts)

def clear_login_failures(client_address):
    with ADMIN_LOGIN_LOCK:
        ADMIN_LOGIN_FAILURES.pop(client_address, None)

def prepare_admin_webp(upload_filename, upload_bytes, occupied_filenames):
    safe_name = secure_filename(upload_filename)
    if not safe_name or Path(safe_name).suffix.lower() not in ADMIN_IMAGE_EXTENSIONS:
        raise ValueError('Use a JPG, PNG, GIF, or WebP image.')

    image_stem = Path(safe_name).stem.strip('._- ') or 'project-image'
    occupied = {name.casefold() for name in occupied_filenames}
    output_filename = f'{image_stem}.webp'
    suffix = 2
    while output_filename.casefold() in occupied:
        output_filename = f'{image_stem}-{suffix}.webp'
        suffix += 1

    try:
        with Image.open(BytesIO(upload_bytes)) as image:
            image.verify()
        with Image.open(BytesIO(upload_bytes)) as source:
            if source.width * source.height > 20_000_000:
                raise ValueError('Images must be no larger than 20 megapixels.')

            frame_count = getattr(source, 'n_frames', 1)
            frame_step = max(1, (frame_count + 159) // 160)
            frames = []
            durations = []
            for frame_index in range(0, frame_count, frame_step):
                source.seek(frame_index)
                frame = ImageOps.exif_transpose(source.copy())
                has_alpha = 'A' in frame.getbands() or 'transparency' in frame.info
                frame = frame.convert('RGBA' if has_alpha else 'RGB')
                frame.thumbnail((MAX_WIDTH, MAX_WIDTH), Image.Resampling.LANCZOS)
                frames.append(frame)
                durations.append(max(20, int(source.info.get('duration', 100)) * frame_step))

            webp_bytes = BytesIO()
            save_options = {'format': 'WEBP', 'quality': QUALITY, 'method': 6}
            if len(frames) > 1:
                save_options.update(
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=source.info.get('loop', 0),
                )
            frames[0].save(webp_bytes, **save_options)
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError('That file is not a supported, readable image.') from error

    return output_filename, webp_bytes.getvalue()

def prepare_admin_media(upload_filename, upload_bytes, occupied_filenames):
    safe_name = secure_filename(upload_filename)
    extension = Path(safe_name).suffix.lower()
    if not safe_name or extension not in ADMIN_MEDIA_EXTENSIONS:
        raise ValueError('Use a JPG, PNG, GIF, WebP, MP4, or WebM file.')

    if extension in ADMIN_VIDEO_EXTENSIONS:
        if len(upload_bytes) > MAX_VIDEO_UPLOAD_BYTES:
            raise ValueError('Videos must be 50 MB or smaller.')
        if extension == '.mp4' and (len(upload_bytes) < 12 or upload_bytes[4:8] != b'ftyp'):
            raise ValueError('That file is not a valid MP4 video.')
        if extension == '.webm' and not upload_bytes.startswith(b'\x1a\x45\xdf\xa3'):
            raise ValueError('That file is not a valid WebM video.')

        image_stem = Path(safe_name).stem.strip('._- ') or 'project-video'
        occupied = {name.casefold() for name in occupied_filenames}
        output_filename = f'{image_stem}{extension}'
        suffix = 2
        while output_filename.casefold() in occupied:
            output_filename = f'{image_stem}-{suffix}{extension}'
            suffix += 1
        return output_filename, upload_bytes

    return prepare_admin_webp(safe_name, upload_bytes, occupied_filenames)

def admin_media_files():
    return sorted(
        path.name for path in STATIC_FOLDER.iterdir()
        if path.is_file() and path.suffix.lower() in ADMIN_MEDIA_EXTENSIONS
    )

def admin_media_modified_times():
    modified_times = {}
    for filename in admin_media_files():
        try:
            modified_times[filename] = (STATIC_FOLDER / filename).stat().st_mtime
        except OSError:
            continue
    return modified_times

def order_admin_gallery_images(gallery_order, selected_assets, uploaded_assets):
    if gallery_order is None:
        return list(dict.fromkeys([*selected_assets, *uploaded_assets]))
    if not isinstance(gallery_order, list):
        raise ValueError('Gallery order must be a list.')

    ordered_images = []
    seen_assets = set()
    seen_uploads = set()
    for item in gallery_order:
        if not isinstance(item, dict):
            raise ValueError('Gallery order contains an invalid item.')
        if item.get('kind') == 'asset':
            filename = item.get('filename')
            if not isinstance(filename, str) or filename not in selected_assets or filename in seen_assets:
                raise ValueError('Gallery order contains an invalid or duplicate asset.')
            seen_assets.add(filename)
            ordered_images.append(filename)
        elif item.get('kind') == 'upload':
            index = item.get('index')
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(uploaded_assets) or index in seen_uploads:
                raise ValueError('Gallery order contains an invalid or duplicate upload.')
            seen_uploads.add(index)
            ordered_images.append(uploaded_assets[index])
        else:
            raise ValueError('Gallery order contains an unknown media type.')

    if seen_assets != set(selected_assets) or seen_uploads != set(range(len(uploaded_assets))):
        raise ValueError('Gallery order must include every selected image and upload exactly once.')
    return ordered_images

def admin_asset_owners():
    project_galleries = load_project_galleries()
    owners = {}
    for filename in admin_media_files():
        for cover, gallery_images in project_galleries.items():
            if filename == cover or filename in gallery_images:
                owners[filename] = cover
                break
    return owners

def admin_project_records():
    captions = load_captions()
    project_galleries = load_project_galleries()
    records = []
    for filename in get_image_files(include_unpublished=True):
        caption = captions.get(filename, {})
        images = [filename, *project_galleries.get(filename, [])]
        records.append({
            'filename': filename,
            'title': caption.get('title', ''),
            'date': caption.get('date', ''),
            'type': caption.get('type', ''),
            'extra': caption.get('extra', ''),
            'description': caption.get('description', ''),
            'link': caption.get('link', ''),
            'published': caption.get('published') is not False,
            'images': images,
        })
    return records

def read_admin_json(path):
    with path.open('r', encoding='utf-8') as data_file:
        value = json.load(data_file)
    if not isinstance(value, dict):
        raise ValueError(f'{path.name} must contain a JSON object.')
    return value

def write_admin_json(path, value):
    temporary_path = path.with_suffix(path.suffix + '.tmp')
    with temporary_path.open('w', encoding='utf-8') as data_file:
        json.dump(value, data_file, ensure_ascii=False, indent=4)
        data_file.write('\n')
    temporary_path.replace(path)

def serialize_admin_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=4) + '\n').encode('utf-8')

def persist_admin_updates(file_updates):
    root = Path(__file__).parent.resolve()
    for relative_path, contents in file_updates.items():
        destination = (root / relative_path).resolve()
        try:
            destination.relative_to(root)
        except ValueError as error:
            raise ValueError('Invalid portfolio update path.') from error
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = destination.with_suffix(destination.suffix + '.tmp')
        temporary_path.write_bytes(contents)
        temporary_path.replace(destination)

def build_admin_file_updates(captions, carousels, uploaded_media=(), image_links=None, project_galleries=None):
    file_updates = {
        'captions.json': serialize_admin_json(captions),
        'carousels.json': serialize_admin_json(carousels),
        'image_links.json': serialize_admin_json(image_links or {}),
        'project_galleries.json': serialize_admin_json(project_galleries or {}),
    }
    for filename, contents in uploaded_media:
        file_updates[f'static/{filename}'] = contents
    return file_updates

def git_run(arguments, env=None):
    return subprocess.run(
        ['git', *arguments], cwd=Path(__file__).parent, env=env,
        capture_output=True, text=True, timeout=45, check=False,
    )

def git_push_branch():
    branch = os.environ.get('GIT_BRANCH') or os.environ.get('RENDER_GIT_BRANCH')
    if not branch:
        branch_result = git_run(['symbolic-ref', '--quiet', '--short', 'HEAD'])
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'main'
    if git_run(['check-ref-format', '--branch', branch]).returncode != 0:
        raise GitPushUnavailable('GIT_BRANCH is not a valid branch name.')
    return branch

def git_push_environment():
    push_env = os.environ.copy()
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GIT_PUSH_TOKEN')
    if token:
        encoded_credentials = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
        push_env.update({
            'GIT_CONFIG_COUNT': '1',
            'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
            'GIT_CONFIG_VALUE_0': f'AUTHORIZATION: basic {encoded_credentials}',
        })
    return push_env

def is_render_environment():
    return bool(os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'))

def git_push_is_configured():
    return not is_render_environment() or bool(
        os.environ.get('GITHUB_TOKEN') or os.environ.get('GIT_PUSH_TOKEN')
    )

def github_api_publishing_enabled():
    return bool(
        is_render_environment()
        or os.environ.get('GITHUB_TOKEN')
        or os.environ.get('GIT_PUSH_TOKEN')
    )

def github_repository_slug():
    repository = GITHUB_REPOSITORY.strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise GitPushUnavailable('GITHUB_REPOSITORY must use owner/repository format.')
    return repository

def github_api_request(method, path, payload=None):
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GIT_PUSH_TOKEN')
    if not token:
        raise GitPushUnavailable('GITHUB_TOKEN is not configured in this running service.')
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    api_request = Request(
        f'https://api.github.com{path}',
        data=body,
        method=method,
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {token}',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'Portfolio-Admin',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urlopen(api_request, timeout=45) as response:
            response_body = response.read()
    except HTTPError as error:
        if error.code == 401:
            message = 'GitHub rejected GITHUB_TOKEN. Replace it with a valid, unexpired token.'
        elif error.code == 403:
            message = 'GitHub denied access. Grant this token Contents: Read and write access to this repository.'
        elif error.code == 404:
            message = 'GitHub could not find the configured repository or branch. Check GITHUB_REPOSITORY and GIT_BRANCH.'
        elif error.code in {409, 422}:
            message = 'The GitHub branch changed or rejected the commit. Retry after checking branch protection.'
        else:
            message = f'GitHub API returned HTTP {error.code}.'
        raise GitPushUnavailable(message) from error
    except URLError as error:
        raise GitPushUnavailable('Could not connect to the GitHub API. Check Render outbound network access.') from error
    try:
        return json.loads(response_body.decode('utf-8')) if response_body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GitPushUnavailable('GitHub returned an unreadable API response.') from error

def commit_portfolio_to_github(file_updates, title):
    repository = github_repository_slug()
    branch = git_push_branch()
    branch_ref = quote(f'heads/{branch}', safe='/')
    ref_data = github_api_request('GET', f'/repos/{repository}/git/ref/{branch_ref}')
    parent_sha = ref_data['object']['sha']
    parent_commit = github_api_request('GET', f'/repos/{repository}/git/commits/{parent_sha}')
    base_tree_sha = parent_commit['tree']['sha']
    existing_tree = github_api_request(
        'GET', f'/repos/{repository}/git/trees/{base_tree_sha}?recursive=1',
    )
    existing_blobs = {entry['path']: entry['sha'] for entry in existing_tree.get('tree', [])}

    changed_files = {}
    for path, contents in file_updates.items():
        blob_header = f'blob {len(contents)}\0'.encode('ascii')
        blob_sha = hashlib.sha1(blob_header + contents).hexdigest()
        if existing_blobs.get(path) != blob_sha:
            changed_files[path] = (contents, blob_sha)
    if not changed_files:
        return {'shipped': True, 'commit': None}

    tree_entries = []
    for path, (contents, _) in changed_files.items():
        blob = github_api_request('POST', f'/repos/{repository}/git/blobs', {
            'content': base64.b64encode(contents).decode('ascii'),
            'encoding': 'base64',
        })
        tree_entries.append({
            'path': path,
            'mode': '100644',
            'type': 'blob',
            'sha': blob['sha'],
        })

    tree = github_api_request('POST', f'/repos/{repository}/git/trees', {
        'base_tree': base_tree_sha,
        'tree': tree_entries,
    })
    safe_title = ' '.join(title.split())[:100] or 'project details'
    commit = github_api_request('POST', f'/repos/{repository}/git/commits', {
        'message': f'Update portfolio project: {safe_title}',
        'tree': tree['sha'],
        'parents': [parent_sha],
    })
    github_api_request('PATCH', f'/repos/{repository}/git/refs/{branch_ref}', {
        'sha': commit['sha'],
        'force': False,
    })
    return {'shipped': True, 'commit': commit['sha'][:7]}

def git_push_failure_message(result):
    raw_output = f'{result.stderr or ""}\n{result.stdout or ""}'
    output = raw_output.lower()
    if 'not a git repository' in output or 'does not appear to be a git repository' in output:
        return 'Render did not provide a Git checkout to push from. Redeploy from the connected GitHub repository.'
    if 'authentication failed' in output or 'invalid username or password' in output or 'http 401' in output:
        return 'GitHub rejected GITHUB_TOKEN. Replace it with a valid token that has access to this repository.'
    if 'http 403' in output or 'write access to repository not granted' in output or 'permission to' in output:
        return 'GitHub denied the push. Grant this token Contents: Read and write access to this repository and allow pushes to the configured branch.'
    if 'repository not found' in output:
        return 'GitHub could not find this repository for the configured token. Check the token repository access.'

    details = raw_output.strip()
    for token in (os.environ.get('GITHUB_TOKEN'), os.environ.get('GIT_PUSH_TOKEN')):
        if token:
            details = details.replace(token, '[redacted]')
    details = re.sub(r'(?i)(authorization:\s*(?:basic|bearer)\s+)\S+', r'\1[redacted]', details)
    details = re.sub(r'https?://[^/\s@]+:[^@\s]+@', 'https://[redacted]@', details)
    details = ' '.join(details.split())
    return f'Git push verification failed: {details[:240] or "Git returned no error details."}'

def ensure_git_push_ready():
    if not git_push_is_configured():
        raise GitPushUnavailable('Git publishing is not configured. Add GITHUB_TOKEN in Render; no changes were saved.')
    branch = git_push_branch()
    if github_api_publishing_enabled():
        repository = github_repository_slug()
        ref_data = github_api_request(
            'GET', f'/repos/{repository}/git/ref/{quote(f"heads/{branch}", safe="/")}',
        )
        github_api_request('GET', f'/repos/{repository}/git/commits/{ref_data["object"]["sha"]}')
        return
    push_result = git_run(
        ['push', '--dry-run', 'origin', f'HEAD:refs/heads/{branch}'],
        env=git_push_environment(),
    )
    if push_result.returncode != 0:
        raise GitPushUnavailable(git_push_failure_message(push_result))

def commit_and_push_portfolio(uploaded_assets=None, title='', file_updates=None):
    if github_api_publishing_enabled():
        if file_updates is None:
            raise GitPushUnavailable('Portfolio file contents were not provided to the GitHub publisher.')
        return commit_portfolio_to_github(file_updates, title)
    if git_run(['rev-parse', '--is-inside-work-tree']).returncode != 0:
        raise RuntimeError('Git is not available for this deployment.')

    branch = git_push_branch()
    push_env = git_push_environment()
    branch_ref = f'refs/heads/{branch}'
    paths = ['captions.json', 'carousels.json', 'image_links.json', 'project_galleries.json']
    uploaded_assets = uploaded_assets or []
    if uploaded_assets:
        paths.extend(uploaded_assets)
        add_result = git_run(['add', '--intent-to-add', '--', *uploaded_assets])
        if add_result.returncode != 0:
            raise RuntimeError('Could not stage the uploaded project images.')

    diff_result = git_run(['diff', '--quiet', 'HEAD', '--', *paths])
    if diff_result.returncode == 0:
        head_result = git_run(['rev-parse', 'HEAD'])
        remote_result = git_run(['ls-remote', 'origin', branch_ref], env=push_env)
        if remote_result.returncode != 0:
            raise RuntimeError('Could not check whether pending project changes reached GitHub.')
        remote_head = remote_result.stdout.split()[0] if remote_result.stdout.strip() else ''
        if head_result.returncode == 0 and remote_head == head_result.stdout.strip():
            return {'shipped': True, 'commit': None}
    elif diff_result.returncode != 1:
        raise RuntimeError('Could not inspect the Git changes.')

    else:
        safe_title = ' '.join(title.split())[:100] or 'project details'
        commit_result = git_run([
            '-c', 'user.name=Portfolio Admin',
            '-c', 'user.email=portfolio-admin@localhost',
            'commit', '--only', '-m', f'Update portfolio project: {safe_title}',
            '--', *paths,
        ])
        if commit_result.returncode != 0:
            raise RuntimeError('Git could not commit the project changes.')

    push_result = git_run(['push', 'origin', f'HEAD:{branch_ref}'], env=push_env)
    if push_result.returncode != 0:
        raise RuntimeError('Changes were committed, but Git push failed. Check GitHub write access and branch configuration.')

    commit_hash = git_run(['rev-parse', '--short', 'HEAD']).stdout.strip()
    return {'shipped': True, 'commit': commit_hash}

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    csrf_token = admin_csrf_token()
    if request.method == 'POST':
        if not valid_admin_csrf():
            return render_template('admin_login.html', csrf_token=csrf_token, error='Please refresh the page and try again.', configured=bool(ADMIN_PASSWORD)), 400
        client_address = request.remote_addr or 'unknown'
        if login_failure_count(client_address) >= ADMIN_LOGIN_FAILURE_LIMIT:
            return render_template('admin_login.html', csrf_token=csrf_token, error='Too many failed attempts. Try again in 15 minutes.', configured=bool(ADMIN_PASSWORD)), 429, {'Retry-After': str(ADMIN_LOGIN_FAILURE_WINDOW)}
        supplied_password = request.form.get('password', '')
        if ADMIN_PASSWORD and hmac.compare_digest(supplied_password, ADMIN_PASSWORD):
            clear_login_failures(client_address)
            session.clear()
            session.permanent = True
            session['admin_authenticated'] = True
            admin_csrf_token()
            return redirect(url_for('admin'))
        failed_attempts = record_login_failure(client_address)
        if failed_attempts >= ADMIN_LOGIN_FAILURE_LIMIT:
            return render_template('admin_login.html', csrf_token=csrf_token, error='Too many failed attempts. Try again in 15 minutes.', configured=bool(ADMIN_PASSWORD)), 429, {'Retry-After': str(ADMIN_LOGIN_FAILURE_WINDOW)}
        error = 'Project editor is not configured yet.' if not ADMIN_PASSWORD else 'That password did not match.'
        return render_template('admin_login.html', csrf_token=csrf_token, error=error, configured=bool(ADMIN_PASSWORD)), 401 if ADMIN_PASSWORD else 503
    return render_template('admin_login.html', csrf_token=csrf_token, error='', configured=bool(ADMIN_PASSWORD))

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html', csrf_token=admin_csrf_token())

@app.route('/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    if not valid_admin_csrf():
        return 'Invalid request token.', 400
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/api/projects', methods=['GET', 'POST'])
@admin_required
def admin_projects():
    if request.method == 'GET':
        media_files = admin_media_files()
        return jsonify({
            'projects': admin_project_records(),
            'assets': media_files,
            'assetModified': admin_media_modified_times(),
            'assetOwners': admin_asset_owners(),
            'imageLinks': load_image_links(),
            'gitPushConfigured': git_push_is_configured(),
        })
    if not valid_admin_csrf():
        return jsonify({'error': 'Your session expired. Refresh and try again.'}), 400

    uploaded_assets = []
    upload = request.files.get('cover_image')
    gallery_uploads = [file for file in request.files.getlist('gallery_uploads') if file.filename]
    if request.is_json:
        data = request.get_json(silent=True) or {}
        gallery_images = data.get('images', [])
        gallery_order = data.get('gallery_order')
        raw_image_link_updates = data.get('image_link_updates')
    else:
        data = request.form
        gallery_images = request.form.getlist('images')
        raw_gallery_order = request.form.get('gallery_order')
        raw_image_link_updates = request.form.get('image_link_updates')
        try:
            gallery_order = json.loads(raw_gallery_order) if raw_gallery_order else None
        except json.JSONDecodeError:
            return jsonify({'error': 'Gallery order must be valid JSON.'}), 400
    try:
        image_link_updates = normalize_image_link_updates(
            json.loads(raw_image_link_updates) if isinstance(raw_image_link_updates, str) else raw_image_link_updates,
        ) if raw_image_link_updates is not None else None
    except (ValueError, json.JSONDecodeError) as error:
        return jsonify({'error': str(error)}), 400

    project_id = str(data.get('project_id', '')).strip()
    filename = str(data.get('filename', '')).strip()
    title = str(data.get('title', '')).strip()
    raw_published = data.get('published')
    if raw_published is None:
        published = None
    elif isinstance(raw_published, bool):
        published = raw_published
    elif isinstance(raw_published, str) and raw_published.lower() in {'true', 'false', '1', '0', 'on', 'off'}:
        published = raw_published.lower() in {'true', '1', 'on'}
    else:
        return jsonify({'error': 'Publish state must be true or false.'}), 400
    fields = {
        'title': title,
        'date': str(data.get('date', '')).strip(),
        'type': str(data.get('type', '')).strip(),
        'extra': str(data.get('extra', '')).strip(),
        'description': str(data.get('description', '')).strip(),
        'link': str(data.get('link', '')).strip(),
    }
    limits = {'title': 160, 'date': 80, 'type': 100, 'extra': 160, 'description': 12000, 'link': 2048}
    if not title:
        return jsonify({'error': 'Add a project title before saving.'}), 400
    if any(len(fields[key]) > limit for key, limit in limits.items()):
        return jsonify({'error': 'One of the project fields is too long.'}), 400
    if fields['link']:
        parsed_link = urlsplit(fields['link'])
        if parsed_link.scheme not in {'http', 'https'} or not parsed_link.netloc:
            return jsonify({'error': 'Project links must start with http:// or https://.'}), 400

    saved_locally = False
    try:
        with ADMIN_WRITE_LOCK:
            captions = read_admin_json(CAPTIONS_FILE)
            carousels = read_admin_json(CAROUSELS_FILE)
            image_links = load_image_links()
            project_galleries = load_project_galleries()
            if published is None:
                existing_caption = captions.get(project_id or filename, {})
                published = not isinstance(existing_caption, dict) or existing_caption.get('published') is not False
            fields['published'] = published
            if project_id and project_id not in {record['filename'] for record in admin_project_records()}:
                return jsonify({'error': 'That project no longer exists. Refresh and try again.'}), 404

            assets = set(admin_media_files())
            if len(gallery_uploads) > 8:
                return jsonify({'error': 'Upload no more than eight gallery images at a time.'}), 400

            prepared_uploads = []
            prepared_gallery_names = []
            upload_names = set()
            cover_filename = None
            uploads = []
            if upload and upload.filename:
                if project_id:
                    return jsonify({'error': 'For an existing project, choose a cover already in the portfolio and upload gallery images below.'}), 400
                uploads.append(upload)
            uploads.extend(gallery_uploads)

            for image_file in uploads:
                safe_name = secure_filename(image_file.filename)
                extension = Path(safe_name).suffix.lower()
                if not safe_name or extension not in ADMIN_MEDIA_EXTENSIONS:
                    return jsonify({'error': 'Use a JPG, PNG, GIF, WebP, MP4, or WebM file.'}), 400
                upload_limit = MAX_VIDEO_UPLOAD_BYTES if extension in ADMIN_VIDEO_EXTENSIONS else MAX_IMAGE_UPLOAD_BYTES
                upload_bytes = image_file.stream.read(upload_limit + 1)
                if len(upload_bytes) > upload_limit:
                    limit_message = 'Videos must be 50 MB or smaller.' if extension in ADMIN_VIDEO_EXTENSIONS else 'Images must be 16 MB or smaller.'
                    return jsonify({'error': limit_message}), 413
                try:
                    media_name, media_bytes = prepare_admin_media(
                        safe_name, upload_bytes, assets | upload_names,
                    )
                except ValueError as error:
                    return jsonify({'error': str(error)}), 400
                upload_names.add(media_name)
                prepared_uploads.append((media_name, media_bytes))
                if image_file is upload:
                    cover_filename = media_name
                else:
                    prepared_gallery_names.append(media_name)

            if cover_filename:
                filename = cover_filename

            if filename not in assets and filename not in upload_names:
                return jsonify({'error': 'Choose an image from the portfolio or upload a new cover.'}), 400
            if filename in captions and filename != project_id:
                return jsonify({'error': 'That image already belongs to another project. Choose an unused cover.'}), 409
            if any(
                filename in gallery_images and cover != project_id
                for cover, gallery_images in project_galleries.items()
            ):
                return jsonify({'error': 'That image is already used in another project gallery. Choose an unused cover.'}), 409

            if isinstance(gallery_images, str):
                gallery_images = [gallery_images]
            if not isinstance(gallery_images, list) or any(not isinstance(image, str) for image in gallery_images):
                return jsonify({'error': 'Choose valid gallery images.'}), 400
            gallery_images = list(dict.fromkeys(gallery_images))
            try:
                ordered_gallery_images = order_admin_gallery_images(
                    gallery_order, gallery_images, prepared_gallery_names,
                )
            except ValueError as error:
                return jsonify({'error': str(error)}), 400
            selected_images = list(dict.fromkeys([filename, *ordered_gallery_images]))
            if any(image not in assets and image not in upload_names for image in selected_images):
                return jsonify({'error': 'One of the selected gallery images is no longer available.'}), 400

            old_project_images = [project_id, *project_galleries.get(project_id, [])] if project_id else []
            for image in selected_images:
                if image != filename and image in captions:
                    return jsonify({'error': f'"{image}" is already the cover of another project.'}), 409

            if project_id and project_id != filename:
                project_galleries.pop(project_id, None)
            project_galleries[filename] = [image for image in ordered_gallery_images if image != filename]
            carousels = rebuild_carousels(project_galleries)

            if image_link_updates is not None:
                resolved_gallery_links = {}
                for item in image_link_updates['gallery']:
                    if item['kind'] == 'asset':
                        linked_filename = item['identifier']
                        if linked_filename not in ordered_gallery_images or linked_filename in resolved_gallery_links:
                            return jsonify({'error': 'Image links must match selected gallery media.'}), 400
                    else:
                        upload_index = item['identifier']
                        if upload_index >= len(prepared_gallery_names):
                            return jsonify({'error': 'An image link refers to an unavailable upload.'}), 400
                        linked_filename = prepared_gallery_names[upload_index]
                        if linked_filename in resolved_gallery_links:
                            return jsonify({'error': 'Image links contain a duplicate upload.'}), 400
                    resolved_gallery_links[linked_filename] = item['url']
                if set(resolved_gallery_links) != set(ordered_gallery_images):
                    return jsonify({'error': 'Add a link setting for every selected gallery image.'}), 400

                for image in selected_images:
                    image_links.pop(image, None)
                if image_link_updates['cover']:
                    image_links[filename] = image_link_updates['cover']
                image_links.update({
                    image: link for image, link in resolved_gallery_links.items() if link
                })
                still_used_media = set(project_galleries)
                still_used_media.update(
                    image for gallery_images in project_galleries.values() for image in gallery_images
                )
                for image in old_project_images:
                    if image not in still_used_media:
                        image_links.pop(image, None)

            try:
                ensure_git_push_ready()
            except GitPushUnavailable as error:
                return jsonify({'error': str(error), 'saved': False, 'shipped': False}), 503

            if project_id and project_id != filename:
                captions.pop(project_id, None)
            captions[filename] = fields

            uploaded_assets = [f'static/{image_name}' for image_name, _ in prepared_uploads]
            file_updates = build_admin_file_updates(
                captions, carousels, prepared_uploads, image_links, project_galleries,
            )
            if github_api_publishing_enabled():
                result = commit_and_push_portfolio(uploaded_assets, title, file_updates)
                persist_admin_updates(file_updates)
            else:
                persist_admin_updates(file_updates)
                result = commit_and_push_portfolio(uploaded_assets, title)
            saved_locally = True
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return jsonify({'error': f'Could not save the project: {error}'}), 500
    except GitPushUnavailable as error:
        return jsonify({'error': str(error), 'saved': saved_locally, 'shipped': False}), 502 if saved_locally else 503
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        return jsonify({'error': str(error), 'saved': saved_locally, 'shipped': False}), 502

    return jsonify({**result, 'project': filename})

@app.route('/admin/api/description-preview', methods=['POST'])
@admin_required
def admin_description_preview():
    if not valid_admin_csrf():
        return jsonify({'error': 'Your session expired. Refresh and try again.'}), 400
    data = request.get_json(silent=True) or {}
    description = data.get('description', '')
    if not isinstance(description, str) or len(description) > 12000:
        return jsonify({'error': 'Description must be text no longer than 12,000 characters.'}), 400
    return jsonify({'html': render_markdown_description(description)})

@app.route('/admin/api/git-status', methods=['POST'])
@admin_required
def admin_git_status():
    if not valid_admin_csrf():
        return jsonify({'error': 'Your session expired. Refresh and try again.'}), 400
    saved_locally = False
    try:
        ensure_git_push_ready()
    except GitPushUnavailable as error:
        return jsonify({'ready': False, 'error': str(error)}), 503
    except subprocess.TimeoutExpired:
        return jsonify({'ready': False, 'error': 'GitHub did not respond in time. Try again shortly.'}), 503
    return jsonify({'ready': True, 'message': 'GitHub repository and branch are reachable; write access is checked when you save.'})

@app.route('/admin/api/projects/<path:filename>', methods=['DELETE'])
@admin_required
def admin_delete_project(filename):
    if not valid_admin_csrf():
        return jsonify({'error': 'Your session expired. Refresh and try again.'}), 400
    try:
        with ADMIN_WRITE_LOCK:
            captions = read_admin_json(CAPTIONS_FILE)
            image_links = load_image_links()
            project_galleries = load_project_galleries()
            if filename not in {record['filename'] for record in admin_project_records()}:
                return jsonify({'error': 'That project no longer exists. Refresh and try again.'}), 404
            try:
                ensure_git_push_ready()
            except GitPushUnavailable as error:
                return jsonify({'error': str(error), 'saved': False, 'shipped': False}), 503
            removed_images = [filename, *project_galleries.pop(filename, [])]
            captions.pop(filename, None)
            carousels = rebuild_carousels(project_galleries)
            still_used_media = set(project_galleries)
            still_used_media.update(
                image for gallery_images in project_galleries.values() for image in gallery_images
            )
            for image in removed_images:
                if image not in still_used_media:
                    image_links.pop(image, None)
            file_updates = build_admin_file_updates(
                captions, carousels, image_links=image_links, project_galleries=project_galleries,
            )
            if github_api_publishing_enabled():
                result = commit_and_push_portfolio(title='Remove project', file_updates=file_updates)
                persist_admin_updates(file_updates)
            else:
                persist_admin_updates(file_updates)
                result = commit_and_push_portfolio(title='Remove project')
            saved_locally = True
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return jsonify({'error': f'Could not remove the project: {error}'}), 500
    except GitPushUnavailable as error:
        return jsonify({'error': str(error), 'saved': saved_locally, 'shipped': False}), 502 if saved_locally else 503
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        return jsonify({'error': str(error), 'saved': saved_locally, 'shipped': False}), 502
    return jsonify({**result, 'deleted': filename})

@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    if request.path.startswith('/admin'):
        response.headers.setdefault('Cache-Control', 'no-store')
    if os.environ.get('RENDER'):
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

@app.route('/robots.txt')
def robots():
    with open(Path(__file__).parent / 'robots.txt', 'r') as f:
        return f.read(), 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    with open(Path(__file__).parent / 'sitemap.xml', 'r') as f:
        return f.read(), 200, {'Content-Type': 'application/xml'}

@app.route('/ping')
def ping():
    """Keep-alive endpoint for Render uptime monitoring"""
    return jsonify({'status': 'ok', 'message': 'Server is alive'}), 200

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(STATIC_FOLDER / 'Favicon', 'favicon.ico', max_age=86400)

@app.route('/api/images')
def get_images():
    """API endpoint to get all images"""
    images = get_image_files()
    image_data = []
    
    for img in images:
        cached_url = downscale_image(img)
        image_data.append({
            'filename': img,
            'url': cached_url,
            'media_type': 'video' if is_video_filename(img) else 'image',
        })
    
    return jsonify(image_data)

@app.route('/api/captions')
def get_captions():
    """API endpoint to get image captions"""
    captions = {
        filename: caption for filename, caption in load_captions().items()
        if not isinstance(caption, dict) or caption.get('published') is not False
    }
    for caption in captions.values():
        if isinstance(caption, dict):
            caption['description_html'] = render_markdown_description(caption.get('description', ''))
    return jsonify(captions)

@app.route('/api/carousel/<filename>')
def get_carousel(filename):
    """API endpoint to get carousel images for a specific image with WebP URLs"""
    caption = load_captions().get(filename, {})
    if isinstance(caption, dict) and caption.get('published') is False:
        return jsonify({'primary': filename, 'images': []})
    project_galleries = load_project_galleries()
    image_links = load_image_links()
    gallery_images = project_galleries.get(filename)
    
    if gallery_images is None:
        # If image has no carousel, return just that image with its URL
        image_path = get_static_path(filename)
        if image_path is not None and image_path.is_file():
            url = downscale_image(filename)
            media_type = 'video' if is_video_filename(filename) else 'image'
            return jsonify({'primary': filename, 'images': [{
                'filename': filename,
                'url': url,
                'media_type': media_type,
                'link': image_links.get(filename, ''),
            }]})
        return jsonify({'primary': filename, 'images': []})
    
    carousel_images = [filename, *gallery_images]
    primary_image = filename
    
    # Return carousel images with their WebP URLs in the order they appear in carousels.json
    # Only include images that actually exist in the static folder
    carousel_data = []
    for img in carousel_images:
        image_path = get_static_path(img)
        if image_path is not None and image_path.is_file():
            url = downscale_image(img)
            media_type = 'video' if is_video_filename(img) else 'image'
            carousel_data.append({
                'filename': img,
                'url': url,
                'media_type': media_type,
                'link': image_links.get(img, ''),
            })
    
    return jsonify({'primary': primary_image, 'images': carousel_data})

@app.errorhandler(404)
def not_found(error):
    """Render the homepage as a fallback while preserving the 404 status."""
    return render_template('index.html', jsonld_scripts=homepage_scripts), 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False)
