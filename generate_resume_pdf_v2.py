#!/usr/bin/env python3
"""
Generate professional PDF resumes with invoice-inspired design
Uses professional colors, spacing, and typography
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== PDF CONFIGURATION =====
class ResumeConfig:
    """Professional resume PDF configuration - Illustrator style with two-column layout"""
    
    # Page settings
    PAGE_SIZE = letter
    MARGIN_LEFT = 50
    MARGIN_RIGHT = 50
    MARGIN_TOP = 40
    MARGIN_BOTTOM = 40
    
    # Colors (RGB) - clean and minimal
    COLOR_BLACK = (0, 0, 0)
    COLOR_DARK_GREY = (0.2, 0.2, 0.2)
    COLOR_GREY = (0.7, 0.7, 0.7)
    COLOR_LIGHT_GREY = (0.95, 0.95, 0.95)
    
    # Font sizes
    FONT_SIZE_NAME = 32
    FONT_SIZE_TITLE = 13
    FONT_SIZE_SUBTITLE = 11
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_SMALL = 9
    FONT_SIZE_LABEL = 8
    
    # Spacing - generous breathing room
    HEADER_SPACING = 6
    NAME_SPACING = 16
    CONTACT_SPACING = 20
    SECTION_SPACING = 20
    SECTION_TOP_PADDING = 14
    SECTION_BOTTOM_PADDING = 12
    JOB_ITEM_SPACING = 12
    BULLET_SPACING = 9
    SKILL_ITEM_SPACING = 7
    LINE_HEIGHT = 13
    
    # Two-column layout
    COLUMN_WIDTH = 300
    COLUMN_GAP = 40
    LEFT_COL_X = 50
    RIGHT_COL_X = 390
    DIVIDER_X = 375
    
    # Divider line
    DIVIDER_WIDTH = 1


def set_text_color(c: canvas.Canvas, color: tuple) -> None:
    """Set text fill color"""
    c.setFillColorRGB(*color)


def set_stroke_color(c: canvas.Canvas, color: tuple) -> None:
    """Set stroke color"""
    c.setStrokeColorRGB(*color)


def draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font_name: str = "Helvetica",
    font_size: int = 10,
    color: tuple = None,
    right_align: bool = False
) -> None:
    """Draw text with styling"""
    if color is None:
        color = ResumeConfig.COLOR_BLACK
    set_text_color(c, color)
    c.setFont(font_name, font_size)
    if right_align:
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def draw_horizontal_line(
    c: canvas.Canvas,
    x_start: float,
    x_end: float,
    y: float,
    color: tuple = None,
    line_width: float = 1
) -> None:
    """Draw a horizontal line"""
    if color is None:
        color = ResumeConfig.COLOR_GREY
    set_stroke_color(c, color)
    c.setLineWidth(line_width)
    c.line(x_start, y, x_end, y)


def draw_accent_bars(c: canvas.Canvas, height: float) -> None:
    """Draw vertical divider line between columns"""
    set_stroke_color(c, ResumeConfig.COLOR_LIGHT_GREY)
    c.setLineWidth(ResumeConfig.DIVIDER_WIDTH)
    c.line(ResumeConfig.DIVIDER_X, 40, ResumeConfig.DIVIDER_X, height - 60)


def draw_header(c: canvas.Canvas, width: float, height: float) -> float:
    """Draw professional header with name and contact"""
    y_pos = height - ResumeConfig.MARGIN_TOP
    
    # Name
    draw_text(c, "Tim van Zanten", ResumeConfig.MARGIN_LEFT, y_pos,
              font_name="Helvetica-Bold", font_size=ResumeConfig.FONT_SIZE_NAME,
              color=ResumeConfig.COLOR_BLACK)
    
    y_pos -= ResumeConfig.NAME_SPACING
    
    # Location
    draw_text(c, "Utrecht", ResumeConfig.MARGIN_LEFT, y_pos,
              font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_NORMAL,
              color=ResumeConfig.COLOR_DARK_GREY)
    
    y_pos -= ResumeConfig.HEADER_SPACING * 2
    
    # Contact info - stacked
    draw_text(c, "+31 6 50426640", ResumeConfig.MARGIN_LEFT, y_pos,
              font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_SMALL,
              color=ResumeConfig.COLOR_DARK_GREY)
    
    y_pos -= ResumeConfig.HEADER_SPACING + 2
    
    draw_text(c, "contact@timvanzanten.nl", ResumeConfig.MARGIN_LEFT, y_pos,
              font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_SMALL,
              color=ResumeConfig.COLOR_DARK_GREY)
    
    return y_pos - ResumeConfig.CONTACT_SPACING


def draw_profile_section(c: canvas.Canvas, y_pos: float, width: float) -> float:
    """Draw professional profile - minimal intro"""
    y_pos -= ResumeConfig.SECTION_TOP_PADDING
    
    profile_text = "Hoi, vanuit een achtergrond in nieuwe media ben ik freelance creatief op het snijvlak van digitale cultuur, muziek en publieksbeleving. Met ervaring in productie, programmering, communicatie en educatie focus ik me op toegankelijke en inclusieve kunstprojecten."
    
    # Word wrap profile text
    words = profile_text.split()
    line = ""
    text_x = ResumeConfig.MARGIN_LEFT
    max_width = ResumeConfig.COLUMN_WIDTH - 10
    
    set_text_color(c, ResumeConfig.COLOR_BLACK)
    c.setFont("Helvetica", ResumeConfig.FONT_SIZE_NORMAL)
    
    for word in words:
        test_line = line + word + " "
        if c.stringWidth(test_line, "Helvetica", ResumeConfig.FONT_SIZE_NORMAL) > max_width:
            if line:
                c.drawString(text_x, y_pos, line)
                y_pos -= ResumeConfig.LINE_HEIGHT
            line = word + " "
        else:
            line = test_line
    
    if line:
        c.drawString(text_x, y_pos, line)
        y_pos -= ResumeConfig.LINE_HEIGHT
    
    return y_pos - ResumeConfig.SECTION_BOTTOM_PADDING


def draw_skills_section(c: canvas.Canvas, y_pos: float, width: float) -> float:
    """Left column only - not used in two-column layout"""
    return y_pos


def draw_education_section_right(c: canvas.Canvas, y_pos: float, width: float) -> float:
    """Draw education section on right column"""
    y_pos -= ResumeConfig.SECTION_TOP_PADDING
    
    draw_text(c, "Opleidingen", ResumeConfig.RIGHT_COL_X, y_pos,
              font_name="Helvetica-Bold", font_size=ResumeConfig.FONT_SIZE_TITLE,
              color=ResumeConfig.COLOR_BLACK)
    
    y_pos -= ResumeConfig.SECTION_SPACING
    
    education = [
        ("MA New Media & Digital Culture", "Universiteit Utrecht, 2023 – 2024"),
        ("Pre-Master Media Studies", "Universiteit Utrecht, 2022 – 2023"),
        ("Pre-Master Filosofie", "Radboud Universiteit Nijmegen, 2021 – 2022"),
        ("Minor Music & Technology", "HKU, 2021"),
        ("BA Communicatie & Multimedia Design", "Hogeschool Utrecht, 2017 – 2021")
    ]
    
    for degree, institution in education:
        # Degree
        draw_text(c, degree, ResumeConfig.RIGHT_COL_X, y_pos,
                  font_name="Helvetica-Bold", font_size=ResumeConfig.FONT_SIZE_NORMAL)
        
        y_pos -= ResumeConfig.JOB_ITEM_SPACING
        
        # Institution
        draw_text(c, institution, ResumeConfig.RIGHT_COL_X, y_pos,
                  font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_SMALL,
                  color=ResumeConfig.COLOR_DARK_GREY)
        
        y_pos -= ResumeConfig.BULLET_SPACING + 4
    
    return y_pos


def draw_experience_section(c: canvas.Canvas, y_pos: float, width: float) -> float:
    """Draw professional experience on left column"""
    y_pos -= ResumeConfig.SECTION_SPACING
    
    draw_text(c, "Relevante ervaring", ResumeConfig.LEFT_COL_X, y_pos,
              font_name="Helvetica-Bold", font_size=ResumeConfig.FONT_SIZE_TITLE,
              color=ResumeConfig.COLOR_BLACK)
    
    y_pos -= ResumeConfig.SECTION_TOP_PADDING
    
    experiences = [
        {
            "title": "Freelance Expo & Festival Production (o.a. via Popkraft)",
            "period": "2023 – heden",
            "bullets": [
                "Coördinatie van vrijwilligers op festivals en culturele evenementen.",
                "o.a. NFF, IDFA, IFFR, SPRING, ITGWO, Inscience, Paradiso, Brainwash en IMPAKT"
            ]
        },
        {
            "title": "Freelance Docent Digitale Geletterdheid",
            "period": "2024 – heden",
            "bullets": [
                "Als gastdocent verzorg ik interactieve lessen op middelbare scholen over AI, algoritmes, privacy en digitale cultuur.",
                "Met als doel leerlingen kritisch te laten reflecteren op het gebruik hiervan."
            ]
        },
        {
            "title": "Muziekclub Democrazy – Stage Communicatie & Data-analyse",
            "period": "2023 – 2024",
            "bullets": [
                "Analyseerde 15 jaar ticketingdata en genereerde zo publieksinzichten voor programmering en communicatie"
            ]
        },
        {
            "title": "Frisse Gedachtes – PR & Conceptontwikkeling / Social Content",
            "period": "2021 – 2023",
            "bullets": [
                "Ontwikkelde content en campagnes voor een platform rond mentale gezondheid onder studenten"
            ]
        },
        {
            "title": "De Speld – Stage & Afstudeerproject Conceptontwikkeling / Branded Content",
            "period": "2019 – 2021",
            "bullets": [
                "Ontwikkelde branded content en creatieve concepten voor partners",
                "Deed onderzoek naar alternatieve vormen van commerciële content binnen satire"
            ]
        }
    ]
    
    for exp in experiences:
        # Job title
        draw_text(c, exp["title"], ResumeConfig.LEFT_COL_X, y_pos,
                  font_name="Helvetica-Bold", font_size=ResumeConfig.FONT_SIZE_SUBTITLE)
        
        # Period on same line, right-aligned
        draw_text(c, exp["period"], ResumeConfig.DIVIDER_X - 5, y_pos,
                  font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_SMALL,
                  color=ResumeConfig.COLOR_DARK_GREY, right_align=True)
        
        y_pos -= ResumeConfig.JOB_ITEM_SPACING
        
        # Bullets
        for bullet in exp["bullets"]:
            draw_text(c, bullet, ResumeConfig.LEFT_COL_X, y_pos,
                      font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_SMALL)
            y_pos -= ResumeConfig.BULLET_SPACING
        
        y_pos -= ResumeConfig.SECTION_BOTTOM_PADDING
    
    return y_pos


def draw_footer(c: canvas.Canvas, width: float) -> None:
    """Draw professional footer"""
    y_footer = 25
    
    footer_text = "Mail  Linkedin  Telefoon"
    draw_text(c, footer_text, width / 2, y_footer,
              font_name="Helvetica", font_size=ResumeConfig.FONT_SIZE_NORMAL,
              color=ResumeConfig.COLOR_DARK_GREY)


def create_resume_pdf(version="v1"):
    """Create professional PDF resume with two-column layout"""
    
    filename = f"Resume_Tim_van_Zanten_2026_{version}.pdf"
    width, height = ResumeConfig.PAGE_SIZE
    
    c = canvas.Canvas(filename, pagesize=ResumeConfig.PAGE_SIZE)
    
    # Set PDF metadata
    c.setTitle("Resume - Tim van Zanten")
    c.setAuthor("Tim van Zanten")
    c.setSubject("Professional Resume - Communication & Culture")
    c.setCreator("Tim van Zanten")
    
    # Draw vertical divider
    draw_accent_bars(c, height)
    
    # Draw header
    y_pos = draw_header(c, width, height)
    
    # Draw profile intro
    y_pos = draw_profile_section(c, y_pos, width)
    
    # Draw left column experience
    y_pos_left = draw_experience_section(c, y_pos, width)
    
    # Draw right column education
    y_pos_right = draw_education_section_right(c, y_pos, width)
    
    # Draw footer
    draw_footer(c, width)
    
    # Save PDF
    c.save()
    print(f"✓ PDF created: {filename}")
    return filename


if __name__ == "__main__":
    try:
        create_resume_pdf(version="v1")
        print("\n✨ Professional resume PDF generated successfully!")
        print("   Layout: Two-column design with experience & education")
        print("   Spacing: Generous breathing room")
        print("   Style: Clean, minimalist Illustrator-inspired")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
