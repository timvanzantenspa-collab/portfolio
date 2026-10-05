# Portfolio - Infinite Scroll Image Gallery

A beautiful, minimal single-page portfolio with infinite scroll image grid.

## Features

✨ **Simple & Clean** - White background, elegant design
📱 **Responsive** - Works on desktop, tablet, and mobile
⚡ **Fast** - Images automatically downscaled and optimized
♾️ **Infinite Scroll** - Loads more images as you scroll
🎨 **2-Column Grid** - With plenty of whitespace and random spacing
📝 **Image Captions** - Add titles and descriptions to your images with a JSON file

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Images

Simply place image files in the `static/` folder:

```
static/
  ├── photo1.jpg
  ├── photo2.png
  ├── photo3.jpg
  └── ... any jpg, png, gif, webp
```

Supported formats: JPG, PNG, GIF, WEBP

### 3. Reorder Images (Optional)

Edit `image_order.json` to control the display order of images:

```json
{
    "order": [
        "my_first_photo.jpg",
        "my_second_photo.png",
        "ezgif.com-video-to-gif.gif"
    ]
}
```

Add image filenames in the order you want them to appear. Any images not listed will be added at the end in alphabetical order.

### 4. Add Captions (Optional)

Edit `captions.json` to add titles and descriptions to your images:

```json
{
    "photo1.jpg": {
        "title": "My Amazing Project",
        "description": "This is a description of the project.\n\nYou can use multiple lines.\nJust use \\n for line breaks."
    },
    "photo2.png": {
        "title": "Another Cool Thing",
        "description": "Description here..."
    }
}
```

**Click any image** to see its title and description in a modal!

### Manage Projects

Open `/admin` to add, edit, group, or remove portfolio projects without editing JSON directly. Project descriptions support Markdown links, bold, italic, lists, and a live preview. The editor accepts up to eight gallery files per save: images are optimized to WebP, while MP4/WebM files remain videos and autoplay muted inline in the portfolio and carousel. Each selected image or video can have its own destination URL; leave it blank to use the project URL. Images are limited to 16 MB each, videos to 50 MB each, and a save to 60 MB total. Saving commits the data and media assets and pushes them to the configured branch. A Render service configured to deploy from that branch will then publish the update.

Configure these environment variables on the server (for Render, use the service's Environment page):

- `ADMIN_PASSWORD` - password for `/admin`.
- `SECRET_KEY` - a long, random value used to protect the admin session.
- `GITHUB_TOKEN` - a GitHub token with Contents write access to this repository. Keep it in the host's secret environment settings; never commit it.
- `GITHUB_REPOSITORY` - optional `owner/repository` override; defaults to `timvanzantenspa-collab/portfolio`.
- `GIT_BRANCH` - optional push target; defaults to the checked-out branch, or `main` when the checkout is detached.

When `GITHUB_TOKEN` is set, the editor publishes atomic commits through the GitHub API, so the app does not need a local Git remote. The token needs Contents read/write permission and access to the target branch; failed publishing leaves project files untouched. For local use without a token, set `ADMIN_PASSWORD` and `SECRET_KEY` before starting Flask; local Git credential-manager authentication is used instead.

### 4. Run the Server

```bash
python app.py
```

Then open: http://127.0.0.1:5005

## How It Works

- **Image Optimization**: Images are automatically downscaled to max 600px width and optimized for web (JPEG quality 85)
- **Smart Caching**: Processed images are cached, so they're only processed once
- **Infinite Scroll**: New images load automatically as you scroll down
- **Responsive Grid**: 2 columns on desktop, 1 column on mobile
- **Modal View**: Click any image to see its details with blurred background
- **Easy Captions**: Just add entries to `captions.json` - no code needed!
- **Custom Ordering**: Control image order with `image_order.json` - no code needed!

## Tips

- Higher resolution original images give better results after downscaling
- Add images in any size - they'll be optimized automatically
- No need to restart the server when adding new images
- Cached versions are stored in `static/.cache/` (can be deleted to force reprocessing)
- Images without entries in `captions.json` will just show their filename as the title
- Images without entries in `image_order.json` will appear at the end in alphabetical order

## File Structure

```
Portfolio/
├── app.py              # Flask backend
├── captions.json       # Image titles and descriptions
├── image_order.json    # Control image display order
├── requirements.txt    # Python dependencies
├── static/             # Your images go here
│   └── .cache/         # Auto-generated optimized images (ignore this)
└── templates/
    └── index.html      # Frontend
```

Enjoy your portfolio! 🎉
