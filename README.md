# Tim van Zanten - Portfolio

A project portfolio for Tim van Zanten, built with Flask.

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

### 2. Add Projects

The easiest way to add and manage projects is through `/admin`. The editor can upload a cover image and gallery media, edit project details, and publish changes to GitHub. See [Manage Projects](#manage-projects) for the required environment variables.

Project data can also be edited directly in `captions.json`:

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

Projects are ordered by date, newest first. Each has a server-rendered detail page with its description and gallery.

### English and Dutch

Public pages use the language saved in the `site_language` cookie, or fall back to the visitor's browser language preference. Dutch is selected when a Dutch preference is present; otherwise the site uses English. Visitors can switch languages using the EN/NL links. The site does not request location access.

Interface copy and its English/Dutch variants are stored in `site-translations.json`. Use **Website translations** in `/admin` to search and edit either version, draft Dutch text with the auto-translate button, and publish reviewed changes. Project titles, project descriptions and metadata, marked names, emphasized or quoted text, and URLs are kept as entered and excluded from translation. Visitors only receive saved translations for eligible interface text; page views do not call a translation service. Auto-translation uses a free service limited to 5,000 characters per day, so larger batches may need to be retried after the daily limit resets. Third-party embeds remain controlled by their own providers.

### Manage Projects

Open `/admin` to add, edit, group, or remove portfolio projects without editing JSON directly. Project descriptions support Markdown links, bold, italic, lists, and a live preview. Add Instagram, YouTube, or webpage embed URLs in the project's embedded-content field, one per line; arbitrary HTML is not accepted. YouTube videos attempt muted autoplay, but Instagram controls playback and browsers may require user interaction. Other sites must permit iframe embedding. The editor accepts up to eight gallery files per save: images are optimized to WebP, while MP4/WebM files remain videos and autoplay muted inline in the portfolio and carousel. Each selected image or video can have its own destination URL; leave it blank to use the project URL. Images are limited to 16 MB each, videos to 50 MB each, and a save to 60 MB total. Saving commits the data and media assets and pushes them to the configured branch. A Render service configured to deploy from that branch will then publish the update.

Configure these environment variables on the server (for Render, use the service's Environment page):

- `ADMIN_PASSWORD` - password for `/admin`.
- `SECRET_KEY` - a long, random value used to protect the admin session.
- `GITHUB_TOKEN` - a GitHub token with Contents write access to this repository. Keep it in the host's secret environment settings; never commit it.
- `GITHUB_REPOSITORY` - optional `owner/repository` override; defaults to `timvanzantenspa-collab/portfolio`.
- `GIT_BRANCH` - optional push target; defaults to the checked-out branch, or `main` when the checkout is detached.

When `GITHUB_TOKEN` is set, the editor publishes atomic commits through the GitHub API, so the app does not need a local Git remote. The token needs Contents read/write permission and access to the target branch; failed publishing leaves project files untouched. For local use without a token, set `ADMIN_PASSWORD` and `SECRET_KEY` before starting Flask; local Git credential-manager authentication is used instead.

### 3. Run the Server

```bash
python app.py
```

Then open: http://127.0.0.1:5005

## How It Works

- **Image Optimization**: Images are converted to WebP and downscaled to a maximum width of 500px on demand, when requested
- **Smart Caching**: Processed images are cached in `static/.cache/`
- **Infinite Scroll**: New images load automatically as you scroll down
- **Project Galleries**: Group images and videos under projects, with optional links per asset
- **Searchable Project Pages**: Each published project has a server-rendered page linked from the homepage and sitemap
- **Project Editor**: Manage project details and media at `/admin`
- **About Page**: Read about Tim and access resume links at `/about`
- **English and Dutch**: Public pages display saved, editable translations selected by the visitor's language preference

## Tips

- Higher resolution original images give better results after downscaling
- Add images in any size - they'll be optimized automatically
- No need to restart the server when adding new images
- Cached versions are stored in `static/.cache/` (can be deleted to force reprocessing)
- Project media and captions are managed through the editor or the corresponding JSON files.

## File Structure

```
Portfolio/
├── app.py              # Flask backend
├── captions.json       # Image titles and descriptions
├── requirements.txt    # Python dependencies
├── static/             # Your images go here
│   ├── language.js     # Browser language selection and page translation
│   └── .cache/         # Auto-generated optimized images (ignore this)
└── templates/
    ├── index.html      # Portfolio homepage
    └── project.html    # Searchable project detail page
```

Enjoy your portfolio! 🎉
