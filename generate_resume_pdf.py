#!/usr/bin/env python3
"""
Editorial two-column resume generator.

One run creates English and Dutch PDFs. The layout is intentionally two-column:
experience gets the main column, supporting material sits in a calmer sidebar.
Spacing is controlled through shared components so rules, headers and blocks
line up predictably.
"""

from html import escape
import json
import logging
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from pypdf import PdfReader, PdfWriter


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PDF_APP_NAME = "Tim's resume maker"
CONTENT_FILE = Path(__file__).with_name("resume_content.json")


class Typography:
    NAME = 28
    SECTION = 9.4
    BODY = 7.85
    SMALL = 7.05
    MICRO = 6.8

    REGULAR = "Helvetica"
    BOLD = "Helvetica-Bold"
    ITALIC = "Helvetica-Oblique"


class Color:
    BLUE = (0.004, 0.004, 1.0)
    BLACK = (0, 0, 0)
    GREY_DARK = (0.18, 0.18, 0.18)
    GREY = (0.42, 0.42, 0.42)
    GREY_MID = (0.58, 0.58, 0.58)
    GREY_LIGHT = (0.86, 0.86, 0.86)
    GREY_FAINT = (0.965, 0.965, 0.965)


class Layout:
    PAGE_SIZE = A4
    PAGE_WIDTH, PAGE_HEIGHT = A4

    MARGIN_LEFT = 42
    MARGIN_RIGHT = 38
    MARGIN_TOP = 48
    MARGIN_BOTTOM = 34

    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    COL_GAP = 28
    LEFT_COL_X = MARGIN_LEFT
    LEFT_COL_WIDTH = 318
    RIGHT_COL_X = LEFT_COL_X + LEFT_COL_WIDTH + COL_GAP
    RIGHT_COL_WIDTH = CONTENT_WIDTH - LEFT_COL_WIDTH - COL_GAP
    DIVIDER_X = LEFT_COL_X + LEFT_COL_WIDTH + (COL_GAP / 2)

    HEADER_TOP = PAGE_HEIGHT - 20
    HEADER_HEIGHT = 94
    HEADER_BOTTOM = HEADER_TOP - HEADER_HEIGHT
    FOOTER_Y = MARGIN_BOTTOM + 3
    SIDEBAR_SECTION_GAP = 12
    LINK_ICON_SIZE = 9


STYLES = {
    "contact": ParagraphStyle(
        "contact",
        fontName=Typography.REGULAR,
        fontSize=Typography.SMALL,
        leading=9.3,
        textColor=Color.GREY,
    ),
    "brand": ParagraphStyle(
        "brand",
        fontName=Typography.BOLD,
        fontSize=Typography.SMALL,
        leading=9.3,
        textColor=Color.GREY_DARK,
    ),
    "profile": ParagraphStyle(
        "profile",
        fontName=Typography.REGULAR,
        fontSize=8.7,
        leading=11.4,
        textColor=Color.BLACK,
    ),
    "body": ParagraphStyle(
        "body",
        fontName=Typography.REGULAR,
        fontSize=Typography.BODY,
        leading=9.75,
        textColor=Color.BLACK,
    ),
    "body_grey": ParagraphStyle(
        "body_grey",
        fontName=Typography.REGULAR,
        fontSize=Typography.BODY,
        leading=9.75,
        textColor=Color.GREY_DARK,
    ),
    "small": ParagraphStyle(
        "small",
        fontName=Typography.REGULAR,
        fontSize=Typography.SMALL,
        leading=8.9,
        textColor=Color.GREY,
    ),
    "micro": ParagraphStyle(
        "micro",
        fontName=Typography.REGULAR,
        fontSize=Typography.MICRO,
        leading=8.4,
        textColor=Color.GREY_DARK,
    ),
    "bullet_blue": ParagraphStyle(
        "bullet_blue",
        fontName=Typography.REGULAR,
        fontSize=Typography.BODY,
        leading=9.75,
        textColor=Color.BLUE,
    ),
}


# Resume data is loaded from resume_content.json via load_resume_content()
COMMON = {}
RESUME_DATA = {}
CONFIG = {}


def validate_json_structure(content: dict) -> None:
    """Validate that loaded JSON has required fields."""
    required_top_level = ["common", "labels", "brand", "profile", "skills", "experience", "projects", "culture", "footer", "filenames"]
    missing = [field for field in required_top_level if field not in content]
    if missing:
        logger.warning(f"Missing fields in JSON: {', '.join(missing)}")

    required_common = ["name", "email", "phone", "website", "linkedin", "location", "education"]
    missing_common = [field for field in required_common if field not in content.get("common", {})]
    if missing_common:
        logger.warning(f"Missing fields in 'common': {', '.join(missing_common)}")


def load_resume_content() -> None:
    """Load editable resume text from resume_content.json when it exists."""

    global COMMON, RESUME_DATA, CONFIG

    if not CONTENT_FILE.exists():
        logger.error(f"Content file not found: {CONTENT_FILE}")
        return

    try:
        with CONTENT_FILE.open("r", encoding="utf-8") as source:
            content = json.load(source)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return
    except Exception as e:
        logger.error(f"Failed to load content file: {e}")
        return

    validate_json_structure(content)

    # Load configuration if present
    if "config" in content:
        CONFIG = content["config"]
        logger.info(f"Loaded custom configuration")

    if "languages" in content:
        COMMON = content["common"]
        RESUME_DATA = content["languages"]
        return

    COMMON = content["common"]
    labels = content["labels"]

    # Prepare education for each language
    education_by_lang = {}
    for language in ("en", "nl"):
        education_by_lang[language] = [
            [item["degree"][language], item["institution"][language]]
            for item in content["common"]["education"]
        ]

    built_languages = {}
    for language in ("en", "nl"):
        built_languages[language] = {
            "filename": content["filenames"][language],
            "labels": labels[language],
            "brand": content["brand"][language],
            "profile": content["profile"][language],
            "skills": [
                [item["label"][language], item["text"][language]]
                for item in content["skills"]
            ],
            "experience": [
                {
                    "role": item["role"][language],
                    "period": item["period"][language],
                    "context": item["context"][language],
                    "bullets": item["bullets"][language],
                    "url": item.get("url")
                }
                for item in content["experience"]
            ],
            "projects": [
                [item["label"][language], item["text"][language], item.get("url")]
                for item in content["projects"]
            ],
            "culture": content["culture"][language],
            "footer": content["footer"][language],
            "festivals": content.get("festivals", {})
        }

    if content.get("legacy_filename"):
        built_languages["en"]["legacy_filename"] = content["legacy_filename"]

    # Update COMMON education for all languages (used by draw_education)
    # We'll use the English version as default for COMMON
    COMMON["education"] = education_by_lang["en"]

    RESUME_DATA = built_languages
    logger.info(f"Successfully loaded resume content for {len(built_languages)} languages")


def set_color(c: canvas.Canvas, color: tuple) -> None:
    c.setFillColorRGB(*color)


def set_stroke_color(c: canvas.Canvas, color: tuple) -> None:
    c.setStrokeColorRGB(*color)


def draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font: str = Typography.REGULAR,
    size: float = Typography.BODY,
    color: tuple = Color.BLACK,
    right_align: bool = False,
) -> None:
    set_color(c, color)
    c.setFont(font, size)
    if right_align:
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def draw_rule(c: canvas.Canvas, x1: float, x2: float, y: float, color=Color.GREY_LIGHT, width=0.45) -> None:
    set_stroke_color(c, color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def draw_paragraph(c: canvas.Canvas, text: str, x: float, y: float, width: float, style: ParagraphStyle) -> float:
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, 1000)
    paragraph.drawOn(c, x, y - height)
    return y - height


def clean(text: str) -> str:
    return escape(text)


def safe_anchor(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def add_url_link(c: canvas.Canvas, url: str, x: float, y: float, width: float, height: float, enabled: bool) -> None:
    if enabled:
        c.linkURL(url, (x, y, x + width, y + height), relative=0, thickness=0)


def draw_tiny_icon(c: canvas.Canvas, label: str, x: float, y: float, enabled: bool) -> float:
    if not enabled:
        return x

    set_color(c, Color.BLUE)
    c.rect(x, y - 1.5, Layout.LINK_ICON_SIZE, Layout.LINK_ICON_SIZE, fill=True, stroke=False)
    draw_text(c, label, x + 1.6, y + 0.4, Typography.BOLD, 5.7, (1, 1, 1))
    return x + Layout.LINK_ICON_SIZE + 4


def draw_contact_item(c: canvas.Canvas, text: str, url: str, x: float, y: float, online: bool, icon: str | None = None) -> float:
    if icon:
        x = draw_tiny_icon(c, icon, x, y, online)
    draw_text(c, text, x, y, Typography.REGULAR, Typography.SMALL, Color.GREY)
    width = stringWidth(text, Typography.REGULAR, Typography.SMALL)
    add_url_link(c, url, x, y - 1, width, 9, online)
    return x + width


def draw_separator(c: canvas.Canvas, x: float, y: float) -> float:
    draw_text(c, "/", x, y, Typography.REGULAR, Typography.SMALL, Color.GREY_MID)
    return x + stringWidth("/", Typography.REGULAR, Typography.SMALL) + 6


def configure_pdf(c: canvas.Canvas, data: dict, language: str, mode: str) -> None:
    """Configure PDF metadata with language-specific content and mode optimization."""
    
    lang_label = "English" if language == "en" else "Dutch"
    mode_label = "Online (Interactive)" if mode == "online" else "Print (Static)"
    title = f"Resume - {COMMON['name']} ({lang_label}, {mode_label})"
    
    # Extract keywords dynamically from data
    keywords = [COMMON["name"], "resume", "cv", language, mode]
    
    # Add brand keywords
    if "brand" in data:
        keywords.extend(data["brand"].lower().split(" / "))
    
    # Add role keywords from experience
    for exp in data.get("experience", [])[:2]:  # First 2 experiences
        role_words = exp["role"].lower().split()
        keywords.extend([w for w in role_words if len(w) > 3])
    
    # Language-specific subject line
    subject = {
        "en": f"{COMMON['name']}'s Resume - Communication, Culture and Digital Literacy",
        "nl": f"CV van {COMMON['name']} - Communicatie, Cultuur en Digitale Geletterdheid"
    }
    
    c.setTitle(title)
    c.setAuthor(COMMON["name"])
    c.setSubject(subject.get(language, subject["en"]))
    c.setCreator(PDF_APP_NAME)
    c.setKeywords(", ".join(keywords))
    
    # Only enable interactive outline for online version
    if mode == "online":
        c.showOutline()


def normalize_pdf_metadata(filename: str) -> None:
    path = Path(filename)
    reader = PdfReader(str(path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    metadata = dict(reader.metadata or {})
    metadata["/Creator"] = PDF_APP_NAME
    metadata["/Producer"] = PDF_APP_NAME
    writer.add_metadata(metadata)

    temp_path = path.with_suffix(".metadata.tmp.pdf")
    with temp_path.open("wb") as output:
        writer.write(output)
    temp_path.replace(path)


def draw_page_system(c: canvas.Canvas, online: bool) -> None:
    """Draw decorative page system. Optimized for each mode."""
    if online:
        # Online: Full color decorative elements
        set_color(c, Color.GREY_FAINT)
        c.rect(0, 0, 9, Layout.PAGE_HEIGHT, fill=True, stroke=False)
        set_color(c, Color.BLUE)
        c.rect(0, 0, 2.2, Layout.PAGE_HEIGHT, fill=True, stroke=False)
    else:
        # Print: Subtle grayscale elements that print well
        set_color(c, (0.95, 0.95, 0.95))  # Very light gray
        c.rect(0, 0, 9, Layout.PAGE_HEIGHT, fill=True, stroke=False)
        # Skip the blue bar for better print appearance - just use subtle left margin


def draw_vertical_divider(c: canvas.Canvas, body_top: float) -> None:
    set_stroke_color(c, Color.GREY_LIGHT)
    c.setLineWidth(0.45)
    c.line(Layout.DIVIDER_X, Layout.MARGIN_BOTTOM + 45, Layout.DIVIDER_X, body_top + 4)


def section_title(c: canvas.Canvas, title: str, x: float, y: float, width: float, online: bool) -> float:
    draw_text(c, title.upper(), x, y, Typography.BOLD, Typography.SECTION, Color.BLUE)
    draw_rule(c, x, x + width, y - 5, Color.GREY_LIGHT, 0.45)
    return y - 12


def draw_header(c: canvas.Canvas, data: dict, language: str, online: bool) -> float:
    header_x = Layout.MARGIN_LEFT - 12
    header_w = Layout.CONTENT_WIDTH + 24
    # Use header background for both online and print
    set_color(c, Color.GREY_FAINT)
    c.rect(header_x, Layout.HEADER_BOTTOM, header_w, Layout.HEADER_HEIGHT, fill=True, stroke=False)

    name_y = Layout.HEADER_TOP - 38
    draw_text(c, COMMON["name"], Layout.MARGIN_LEFT, name_y, Typography.BOLD, Typography.NAME, Color.BLUE)
    name_width = stringWidth(COMMON["name"], Typography.BOLD, Typography.NAME)
    add_url_link(c, "https://timvanzanten.nl", Layout.MARGIN_LEFT, name_y - 2, name_width, 11, online)
    
    draw_text(
        c,
        COMMON["location"][language],
        Layout.PAGE_WIDTH - Layout.MARGIN_RIGHT,
        name_y - 1,
        Typography.REGULAR,
        Typography.SMALL,
        Color.GREY,
        right_align=True,
    )

    contact_y = name_y - 20
    if online:
        # ONLINE: Clickable contact info with interactive elements
        x = Layout.MARGIN_LEFT
        x = draw_contact_item(c, COMMON["phone"], "tel:+31650426640", x, contact_y, online)
        x = draw_separator(c, x + 6, contact_y)
        x = draw_contact_item(c, COMMON["email"], f"mailto:{COMMON['email']}", x, contact_y, online)
        x = draw_separator(c, x + 6, contact_y)
        x = draw_contact_item(c, COMMON["website"], "https://timvanzanten.nl", x, contact_y, online)
        x = draw_separator(c, x + 6, contact_y)
        draw_contact_item(c, COMMON["linkedin"], "https://linkedin.com/in/timzv", x, contact_y, online, "in")
        contact_y -= 7.5
    else:
        # PRINT: Plain text contact info with full URLs visible for reference
        contact = " / ".join([COMMON["phone"], COMMON["email"], COMMON["website"], COMMON["linkedin"]])
        contact_y = draw_paragraph(c, clean(contact), Layout.MARGIN_LEFT, contact_y, Layout.CONTENT_WIDTH, STYLES["contact"])

    brand_y = contact_y - 2
    draw_paragraph(c, clean(data["brand"]), Layout.MARGIN_LEFT, brand_y, Layout.CONTENT_WIDTH, STYLES["brand"])

    profile_y = Layout.HEADER_BOTTOM - 10
    return draw_paragraph(c, clean(data["profile"]), Layout.MARGIN_LEFT, profile_y, 450, STYLES["profile"]) - 26


def draw_experience(c: canvas.Canvas, data: dict, y: float, online: bool) -> float:
    y = section_title(c, data["labels"]["experience"], Layout.LEFT_COL_X, y, Layout.LEFT_COL_WIDTH, online)

    # Get festival URLs from common data
    festival_urls = RESUME_DATA.get(list(RESUME_DATA.keys())[0], {}).get("festivals", {})

    for index, exp in enumerate(data["experience"]):
        draw_text(
            c,
            exp["period"],
            Layout.LEFT_COL_X + Layout.LEFT_COL_WIDTH,
            y - 7.5,
            Typography.REGULAR,
            Typography.MICRO,
            Color.GREY_MID,
            right_align=True,
        )
        y = draw_paragraph(
            c,
            f"<b>{clean(exp['role'])}</b>",
            Layout.LEFT_COL_X,
            y,
            Layout.LEFT_COL_WIDTH - 55,
            STYLES["body"],
        )
        y -= 2
        y = draw_paragraph(c, clean(exp["context"]), Layout.LEFT_COL_X, y, Layout.LEFT_COL_WIDTH, STYLES["small"])
        y -= 8

        for item in exp["bullets"]:
            # Draw blue bullet dot
            draw_text(c, "•", Layout.LEFT_COL_X + 7, y - 8, Typography.REGULAR, Typography.BODY, Color.BLUE)
            # Draw bullet with potential festival links
            y = draw_bullet_with_links(c, item, Layout.LEFT_COL_X + 14, y, Layout.LEFT_COL_WIDTH - 14, online, festival_urls)
            y -= 4

        y -= 16 if index < len(data["experience"]) - 1 else 0

    return y


def draw_labeled_lines(c: canvas.Canvas, items: list, x: float, y: float, width: float, online: bool = False) -> float:
    for item in items:
        if len(item) == 3:
            label, value, url = item
        else:
            label, value = item
            url = None
        
        y = draw_paragraph(c, f"<b>{clean(label)}</b>", x, y, width, STYLES["body"])
        y -= 2
        
        # For print mode, append URL as reference text if available
        if not online and url:
            display_value = f"{value} — {url}"
        else:
            display_value = value
        
        y = draw_paragraph(c, clean(display_value), x, y, width, STYLES["small"])
        
        # For online mode, create clickable link on label
        if online and url:
            label_width = stringWidth(clean(label), Typography.REGULAR, Typography.BODY)
            add_url_link(c, url, x, y + 8, label_width, 9, True)
        
        y -= 12
    return y


def draw_skills(c: canvas.Canvas, data: dict, y: float, online: bool) -> float:
    y = section_title(c, data["labels"]["skills"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH, online)
    return draw_labeled_lines(c, data["skills"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH) - Layout.SIDEBAR_SECTION_GAP


def draw_education(c: canvas.Canvas, data: dict, y: float, online: bool) -> float:
    y = section_title(c, data["labels"]["education"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH, online)
    return draw_labeled_lines(c, COMMON["education"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH) - Layout.SIDEBAR_SECTION_GAP


def draw_projects(c: canvas.Canvas, data: dict, y: float, online: bool) -> float:
    y = section_title(c, data["labels"]["projects"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH, online)
    return draw_labeled_lines(c, data["projects"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH, online) - Layout.SIDEBAR_SECTION_GAP


def draw_bullet_with_links(c: canvas.Canvas, bullet: dict | str, x: float, y: float, width: float, online: bool, festival_urls: dict = None) -> float:
    """Draw a bullet point that may contain festival links."""
    
    if isinstance(bullet, str):
        # Simple string bullet - no links
        return draw_paragraph(c, f" {clean(bullet)}", x, y, width, STYLES["body"])
    
    # Structured bullet with festivals
    text = bullet.get("text", "")
    festivals = bullet.get("festivals", [])
    suffix = bullet.get("suffix", "")
    
    # Build the full text
    festival_text = ", ".join(festivals)
    full_text = text + festival_text + suffix
    
    # Calculate paragraph height for accurate link positioning
    test_paragraph = Paragraph(f" {clean(full_text)}", STYLES["body"])
    _, para_height = test_paragraph.wrap(width, 1000)
    
    # Store the y position before drawing (top of text area)
    text_y_top = y
    text_y_bottom = y - para_height
    
    # Draw the paragraph
    y_result = draw_paragraph(c, f" {clean(full_text)}", x, y, width, STYLES["body"])
    
    # Add links for each festival (only in online mode)
    if online and festival_urls:
        # Calculate position of festival list in the text
        prefix_text = text
        prefix_width = stringWidth(clean(prefix_text) + " ", Typography.REGULAR, Typography.BODY)
        
        # Link should be positioned roughly in the middle of the text area vertically
        link_y_center = (text_y_top + text_y_bottom) / 2
        link_height = 10
        
        # Add links for each festival
        current_x = x + prefix_width
        for i, festival in enumerate(festivals):
            if festival in festival_urls:
                festival_width = stringWidth(festival, Typography.REGULAR, Typography.BODY)
                # Position link with bottom at link_y_center, extending upward
                add_url_link(c, festival_urls[festival], current_x, link_y_center - (link_height / 2), festival_width, link_height, True)
                current_x += festival_width
                
                # Add separator width if not last
                if i < len(festivals) - 1:
                    current_x += stringWidth(", ", Typography.REGULAR, Typography.BODY)
    
    return y_result

def draw_culture(c: canvas.Canvas, data: dict, y: float, online: bool) -> float:
    y = section_title(c, data["labels"]["culture"], Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH, online)
    
    # Get festival names and build URLs from the festivals object
    festival_names = data["culture"]
    festival_urls = data.get("festivals", {})
    
    # Build display text
    festival_text = " / ".join(festival_names)
    text_y = y
    y = draw_paragraph(c, clean(festival_text), Layout.RIGHT_COL_X, y, Layout.RIGHT_COL_WIDTH, STYLES["small"])
    
    # Add clickable links for each festival
    if online:
        x_pos = Layout.RIGHT_COL_X
        for festival_name in festival_names:
            if festival_name in festival_urls:
                url = festival_urls[festival_name]
                text_width = stringWidth(festival_name, Typography.REGULAR, Typography.SMALL)
                add_url_link(c, url, x_pos, text_y - 8, text_width, 8, True)
            x_pos += stringWidth(festival_name, Typography.REGULAR, Typography.SMALL)
            x_pos += stringWidth(" / ", Typography.REGULAR, Typography.SMALL)
    
    return y - Layout.SIDEBAR_SECTION_GAP


def draw_footer(c: canvas.Canvas, data: dict, online: bool) -> None:
    draw_rule(c, Layout.MARGIN_LEFT, Layout.PAGE_WIDTH - Layout.MARGIN_RIGHT, Layout.FOOTER_Y + 14)
    draw_text(c, data["footer"], Layout.MARGIN_LEFT, Layout.FOOTER_Y, Typography.REGULAR, 7.0, Color.GREY)
    
    # Website in footer - different treatment for online vs print
    website_text = COMMON["website"]
    if not online:
        # PRINT: Show full URL for reference
        website_text = f"https://{COMMON['website']}"
    
    website_width = stringWidth(website_text, Typography.REGULAR, 7.0)
    draw_text(
        c,
        website_text,
        Layout.PAGE_WIDTH - Layout.MARGIN_RIGHT,
        Layout.FOOTER_Y,
        Typography.REGULAR,
        7.0,
        Color.GREY,
        right_align=True,
    )
    # Only add clickable link in online mode
    if online:
        add_url_link(
            c,
            "https://timvanzanten.nl",
            Layout.PAGE_WIDTH - Layout.MARGIN_RIGHT - website_width,
            Layout.FOOTER_Y - 1,
            website_width,
            9,
            True,
        )


def variant_filenames(data: dict, language: str, mode: str) -> list[str]:
    stem = f"Resume_Tim_van_Zanten_2026_{language.upper()}_{mode}"
    filenames = [f"{stem}.pdf"]

    if language == "en" and mode == "online":
        filenames.append(data["legacy_filename"])

    return filenames


def build_resume(language: str, mode: str) -> list[str]:
    data = RESUME_DATA[language]
    online = mode == "online"
    filenames = variant_filenames(data, language, mode)

    for filename in filenames:
        try:
            c = canvas.Canvas(filename, pagesize=Layout.PAGE_SIZE)
            configure_pdf(c, data, language, mode)
            
            # Draw page system with mode optimization
            draw_page_system(c, online)
            body_y = draw_header(c, data, language, online)
            draw_vertical_divider(c, body_y)

            draw_experience(c, data, body_y, online)

            sidebar_y = body_y
            sidebar_y = draw_skills(c, data, sidebar_y, online)
            sidebar_y = draw_education(c, data, sidebar_y, online)
            sidebar_y = draw_projects(c, data, sidebar_y, online)
            draw_culture(c, data, sidebar_y, online)

            draw_footer(c, data, online)
            c.save()
            normalize_pdf_metadata(filename)
            logger.info(f"Generated {mode} PDF: {filename}")
        except Exception as e:
            logger.error(f"Failed to create {filename}: {e}", exc_info=True)
            raise

    return filenames


def text_filename(language: str) -> str:
    return f"Resume_Tim_van_Zanten_2026_{language.upper()}.txt"


def build_plain_text(language: str) -> str:
    data = RESUME_DATA[language]
    lines = [
        COMMON["name"],
        COMMON["location"][language],
        f"{COMMON['phone']} / {COMMON['email']} / {COMMON['website']} / {COMMON['linkedin']}",
        data["brand"],
        "",
        data["profile"],
        "",
        data["labels"]["experience"].upper(),
    ]

    for exp in data["experience"]:
        lines.extend(
            [
                "",
                f"{exp['role']} | {exp['period']}",
                exp["context"],
            ]
        )
        lines.extend(f"- {item}" for item in exp["bullets"] if isinstance(item, str))
        for item in exp["bullets"]:
            if isinstance(item, dict):
                text = item.get("text", "") + ", ".join(item.get("festivals", [])) + item.get("suffix", "")
                lines.append(f"- {text}")

    lines.extend(["", data["labels"]["skills"].upper()])
    for label, value in data["skills"]:
        lines.append(f"{label}: {value}")

    lines.extend(["", data["labels"]["education"].upper()])
    for degree, institution in COMMON["education"]:
        lines.append(f"{degree}: {institution}")

    lines.extend(["", data["labels"]["projects"].upper()])
    for project in data["projects"]:
        label = project[0]
        value = project[1]
        lines.append(f"{label}: {value}")

    lines.extend(["", data["labels"]["culture"].upper(), " / ".join(data["culture"])])

    filename = text_filename(language)
    Path(filename).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return filename


def build_jsonld_schema(language: str) -> str:
    """Generate JSON-LD structured data for search engines and social platforms."""
    from datetime import datetime
    
    data = RESUME_DATA[language]
    
    # Build work experience entries
    work_entries = []
    for exp in data.get("experience", []):
        work_entries.append({
            "@type": "EmployeeRole",
            "roleName": exp["role"],
            "startDate": exp["period"].split("-")[0] if "-" in exp["period"] else None,
            "endDate": "present" if any(word in exp["period"].lower() for word in ["present", "heden"]) else exp["period"].split("-")[1].strip() if "-" in exp["period"] else None,
            "description": exp["context"]
        })
    
    # Build education entries
    education_entries = []
    for degree, institution in COMMON.get("education", []):
        education_entries.append({
            "@type": "EducationalOccupationalCredential",
            "name": degree,
            "educationalLevel": "HigherEducation",
            "credentialCategory": "Diploma",
            "awardingBody": {
                "@type": "Organization",
                "name": institution
            }
        })
    
    # Build skills
    skills = []
    for skill_item in data.get("skills", []):
        skills.append({
            "@type": "Thing",
            "name": skill_item[0],
            "description": skill_item[1]
        })
    
    # Build projects
    projects = []
    for project in data.get("projects", []):
        projects.append({
            "@type": "CreativeWork",
            "name": project[0],
            "description": project[1],
            "url": project[2] if len(project) > 2 else None
        })
    
    # Main Person schema
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": COMMON["name"],
        "url": f"https://{COMMON['website']}",
        "email": COMMON["email"],
        "telephone": COMMON["phone"],
        "jobTitle": data["brand"],
        "description": data["profile"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": COMMON["location"][language]
        },
        "sameAs": [
            f"https://linkedin.com/in/{COMMON['linkedin'].split('/')[-1]}",
            f"https://{COMMON['website']}"
        ],
        "workExperience": work_entries,
        "educationExperience": education_entries,
        "skills": skills,
        "projects": projects,
        "knowsAbout": data["culture"],
        "dateModified": datetime.now().isoformat()
    }
    
    filename = f"resume_{language}.jsonld"
    Path(filename).write_text(json.dumps(jsonld, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Generated JSON-LD schema: {filename}")
    return filename


def build_all_resumes() -> list[str]:
    load_resume_content()

    # Apply custom configuration if loaded
    if CONFIG:
        logger.info(f"Using custom configuration with {len(CONFIG)} sections")
        # Configuration is available in CONFIG dict for runtime customization
        # Current implementation uses hardcoded classes but config is available
        # Future: Could make Layout/Typography classes read from CONFIG at runtime

    generated = []
    failed = []
    
    for language in ("en", "nl"):
        lang_name = "English" if language == "en" else "Dutch"
        logger.info(f"\n{'='*60}")
        logger.info(f"Building resumes for {lang_name} ({language})")
        logger.info(f"{'='*60}")
        
        try:
            # Build online and print versions
            for mode in ("online", "print"):
                try:
                    results = build_resume(language, mode)
                    generated.extend(results)
                    logger.info(f"✓ {mode.capitalize()} variant created")
                except Exception as e:
                    failed.extend([f"{language}-{mode}"])
                    logger.error(f"✗ Failed to create {mode} variant: {e}")
                    raise
            
            # Build supplementary formats
            try:
                generated.append(build_plain_text(language))
                logger.info(f"✓ Plain text version created")
            except Exception as e:
                logger.error(f"✗ Failed to create plain text: {e}")
                failed.append(f"{language}-text")
            
            try:
                generated.append(build_jsonld_schema(language))
                logger.info(f"✓ JSON-LD schema created")
            except Exception as e:
                logger.error(f"✗ Failed to create JSON-LD schema: {e}")
                failed.append(f"{language}-jsonld")
                
        except Exception as e:
            logger.error(f"Critical error generating resume for {language}: {e}", exc_info=True)
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"BUILD SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Successfully generated: {len(generated)} files")
    if failed:
        logger.warning(f"Failed: {len(failed)} items: {', '.join(failed)}")
    else:
        logger.info(f"✓ All builds completed successfully")
    
    return generated


if __name__ == "__main__":
    print("\n" + "="*70)
    print(f"  {PDF_APP_NAME.upper()}")
    print("  Two-column editorial resume generator")
    print("="*70 + "\n")
    
    try:
        results = build_all_resumes()
        
        print("\n" + "="*70)
        print(f"  GENERATED OUTPUT ({len(results)} files)")
        print("="*70)
        
        # Group results by type
        pdfs = [r for r in results if r.endswith('.pdf')]
        text_files = [r for r in results if r.endswith('.txt')]
        jsonld = [r for r in results if r.endswith('.jsonld')]
        
        print(f"\n  PDFs ({len(pdfs)}):")
        for pdf in sorted(pdfs):
            size_kb = Path(pdf).stat().st_size / 1024 if Path(pdf).exists() else 0
            print(f"    ✓ {pdf} ({size_kb:.1f} KB)")
        
        if text_files:
            print(f"\n  Text ({len(text_files)}):")
            for txt in sorted(text_files):
                print(f"    ✓ {txt}")
        
        if jsonld:
            print(f"\n  JSON-LD Schemas ({len(jsonld)}):")
            for jl in sorted(jsonld):
                print(f"    ✓ {jl}")
        
        print("\n" + "="*70)
        print("  ✓ BUILD STATUS: SUCCESS")
        print("  ✓ Two-column editorial layout")
        print("  ✓ Online (interactive) variants with clickable links")
        print("  ✓ Print (static) variants optimized for B&W printing")
        print("="*70 + "\n")
        
    except Exception as e:
        print("\n" + "="*70)
        print("  ✗ BUILD STATUS: FAILED")
        print("="*70)
        print(f"\n  Error: {e}\n")
        import traceback
        traceback.print_exc()
        exit(1)
