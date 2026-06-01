"""
Generate JSON-LD structured data schemas from resume_content.json
Supports Person, BreadcrumbList, Experience, and Education schemas
for Google, LinkedIn, and search engine indexing
"""

import json
from pathlib import Path
from datetime import datetime


def load_resume_content():
    """Load resume content from JSON file"""
    resume_path = Path(__file__).parent / 'resume_content.json'
    with open(resume_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_person_schema(content):
    """
    Generate Person schema (https://schema.org/Person)
    Includes professional profile, contact info, and social profiles
    """
    common = content['common']
    
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": common['name'],
        "givenName": common['name'].split()[0],
        "familyName": common['name'].split()[-1],
        "url": f"https://{common['website']}",
        "email": common['email'],
        "telephone": common['phone'],
        "jobTitle": "Creative Producer & Researcher",
        "description": content['profile']['en'],
        "location": {
            "@type": "Place",
            "name": common['location']['en']
        },
        "sameAs": [
            f"https://{common['linkedin']}",
            f"https://{common['website']}"
        ],
        "knowsAbout": [
            "Event Coordination",
            "Cultural Production",
            "Digital Literacy",
            "Audience Research",
            "Project Management",
            "Social Media Strategy",
            "Content Strategy",
            "AI Literacy",
            "Media Literacy"
        ]
    }
    
    return schema


def generate_breadcrumb_schema():
    """
    Generate BreadcrumbList schema for site navigation
    https://schema.org/BreadcrumbList
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://timvanzanten.nl"
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "About",
                "item": "https://timvanzanten.nl/about"
            }
        ]
    }
    
    return schema


def generate_experience_schema(content):
    """
    Generate WorkExperience schemas (https://schema.org/WorkExperience)
    One schema per job/project
    """
    experiences = []
    
    for exp in content['experience']:
        period_en = exp['period']['en']
        
        # Parse date range
        date_parts = period_en.split('-')
        start_date = parse_date_string(date_parts[0].strip())
        
        if 'present' in date_parts[1].lower():
            end_date = None
        else:
            end_date = parse_date_string(date_parts[1].strip())
        
        work_exp = {
            "@context": "https://schema.org",
            "@type": "WorkExperience",
            "position": {
                "@type": "JobTitle",
                "title": exp['role']['en']
            },
            "description": " ".join(exp['bullets']['en']),
            "startDate": start_date,
            "jobTitle": exp['role']['en'],
            "areaServed": exp['context']['en']
        }
        
        if end_date:
            work_exp["endDate"] = end_date
        
        experiences.append(work_exp)
    
    return experiences


def generate_education_schema(content):
    """
    Generate EducationEvent schemas (https://schema.org/EducationEvent)
    One schema per educational qualification
    """
    educations = []
    
    for edu in content['common']['education']:
        education = {
            "@context": "https://schema.org",
            "@type": "EducationEvent",
            "name": edu[0],
            "organizer": {
                "@type": "EducationalOrganization",
                "name": edu[1].split(',')[0]  # Extract university name
            }
        }
        
        # Extract year from education entry
        year_str = edu[1].split(',')[-1].strip()
        if year_str and year_str[0].isdigit():
            education["startDate"] = year_str.split('-')[0].strip()
            if '-' in year_str:
                education["endDate"] = year_str.split('-')[1].strip()
        
        educations.append(education)
    
    return educations


def generate_professional_service_schema(content):
    """
    Generate ProfessionalService schema for describing service offerings
    https://schema.org/ProfessionalService
    """
    common = content['common']
    skills = content['skills']
    
    service_categories = [skill['text']['en'] for skill in skills]
    
    schema = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": f"{common['name']} - Consulting & Production",
        "description": content['profile']['en'],
        "url": f"https://{common['website']}",
        "email": common['email'],
        "telephone": common['phone'],
        "areaServed": [
            "Utrecht",
            "Amsterdam",
            "Netherlands",
            "European Union"
        ],
        "serviceType": [
            "Event Coordination",
            "Cultural Production",
            "Project Management",
            "Digital Literacy Training",
            "Audience Research"
        ],
        "knowsAbout": service_categories
    }
    
    return schema


def generate_organization_schema(content):
    """
    Generate Organization schema for portfolio/professional profile
    https://schema.org/Organization
    """
    common = content['common']
    
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": common['name'],
        "url": f"https://{common['website']}",
        "logo": f"https://{common['website']}/static/Favicon/og-image.png",
        "description": content['brand']['en'],
        "sameAs": [
            f"https://{common['linkedin']}",
            f"https://{common['website']}"
        ],
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "Professional",
            "email": common['email'],
            "telephone": common['phone']
        }
    }
    
    return schema


def generate_about_page_schema(content):
    """
    Generate comprehensive schema for the about page
    Combines Person, ProfessionalService, and describes offerings
    """
    common = content['common']
    
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            # Main person profile
            {
                "@type": "Person",
                "@id": f"https://{common['website']}/about#person",
                "name": common['name'],
                "url": f"https://{common['website']}/about",
                "description": content['profile']['en'],
                "image": f"https://{common['website']}/static/Favicon/og-image.png",
                "sameAs": [
                    f"https://{common['linkedin']}",
                    f"https://{common['website']}"
                ]
            },
            # Professional services offered
            {
                "@type": "ProfessionalService",
                "@id": f"https://{common['website']}/about#services",
                "provider": {
                    "@id": f"https://{common['website']}/about#person"
                },
                "serviceType": [
                    "Event Coordination & Festival Production",
                    "Digital Literacy Workshops",
                    "Audience Research & Analysis",
                    "Communication & Content Strategy",
                    "Project Coordination"
                ]
            },
            # Breadcrumb navigation
            {
                "@type": "BreadcrumbList",
                "@id": f"https://{common['website']}/about#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": f"https://{common['website']}"
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "About",
                        "item": f"https://{common['website']}/about"
                    }
                ]
            }
        ]
    }
    
    return schema


def parse_date_string(date_str):
    """
    Parse date string to ISO 8601 format (YYYY-MM-DD)
    Examples: "2023", "May 2024", "2023-2024" -> "2023-05-01", "2024-05-01", "2023-01-01"
    """
    months = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    date_str = date_str.strip().lower()
    
    # Handle just year
    if date_str.isdigit() and len(date_str) == 4:
        return f"{date_str}-01-01"
    
    # Handle "Month Year"
    parts = date_str.split()
    if len(parts) >= 2:
        for month_name, month_num in months.items():
            if month_name in parts[0]:
                year = parts[-1]
                if year.isdigit():
                    return f"{year}-{month_num}-01"
    
    # Handle year range - return first year
    if '-' in date_str:
        year = date_str.split('-')[0].strip()
        if year.isdigit():
            return f"{year}-01-01"
    
    return None


def generate_all_schemas(content):
    """
    Generate all JSON-LD schemas and return as dictionary
    """
    schemas = {
        'person': generate_person_schema(content),
        'breadcrumb': generate_breadcrumb_schema(),
        'organization': generate_organization_schema(content),
        'professional_service': generate_professional_service_schema(content),
        'experience': generate_experience_schema(content),
        'education': generate_education_schema(content),
        'about_page': generate_about_page_schema(content)
    }
    
    return schemas


def get_schema_script_tags(schemas):
    """
    Convert schemas dictionary to HTML script tags
    Returns string of <script type="application/ld+json"> tags
    """
    scripts = []
    
    # Add person schema
    scripts.append(
        f'<script type="application/ld+json">\n{json.dumps(schemas["person"], indent=2)}\n</script>'
    )
    
    # Add breadcrumb schema
    scripts.append(
        f'<script type="application/ld+json">\n{json.dumps(schemas["breadcrumb"], indent=2)}\n</script>'
    )
    
    # Add organization schema
    scripts.append(
        f'<script type="application/ld+json">\n{json.dumps(schemas["organization"], indent=2)}\n</script>'
    )
    
    return '\n'.join(scripts)


def get_about_page_script_tags(schemas):
    """
    Get script tags specifically for the about page with more detailed schemas
    """
    scripts = []
    
    # Add comprehensive about page schema
    scripts.append(
        f'<script type="application/ld+json">\n{json.dumps(schemas["about_page"], indent=2)}\n</script>'
    )
    
    # Add experience schemas
    if schemas['experience']:
        scripts.append(
            f'<script type="application/ld+json">\n{json.dumps(schemas["experience"][0], indent=2)}\n</script>'
        )
    
    # Add education schemas
    if schemas['education']:
        scripts.append(
            f'<script type="application/ld+json">\n{json.dumps(schemas["education"][0], indent=2)}\n</script>'
        )
    
    return '\n'.join(scripts)


if __name__ == '__main__':
    # Load resume content
    content = load_resume_content()
    
    # Generate all schemas
    schemas = generate_all_schemas(content)
    
    # Print schemas for debugging
    print("=== Person Schema ===")
    print(json.dumps(schemas['person'], indent=2))
    
    print("\n=== Organization Schema ===")
    print(json.dumps(schemas['organization'], indent=2))
    
    print("\n=== Professional Service Schema ===")
    print(json.dumps(schemas['professional_service'], indent=2))
    
    print("\n=== HTML Script Tags (Homepage) ===")
    print(get_schema_script_tags(schemas))
    
    print("\n=== HTML Script Tags (About Page) ===")
    print(get_about_page_script_tags(schemas))
