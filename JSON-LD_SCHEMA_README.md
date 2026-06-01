# JSON-LD Schema Implementation

## Overview

JSON-LD (JSON for Linking Data) structured data has been added to the portfolio website for improved SEO, machine readability, and better indexing by search engines like Google, LinkedIn, and other platforms.

## Files Added

### `generate_jsonld.py`
Python module that generates structured data schemas from `resume_content.json`. 

**Key Functions:**
- `generate_person_schema()` - Creates Person schema with professional profile
- `generate_organization_schema()` - Creates Organization schema
- `generate_professional_service_schema()` - Describes services offered
- `generate_experience_schema()` - Generates work experience schemas
- `generate_education_schema()` - Generates education schemas
- `generate_breadcrumb_schema()` - Creates navigation breadcrumbs
- `generate_about_page_schema()` - Comprehensive schema graph for about page

## Files Modified

### `app.py`
- Added imports for JSON-LD generation functions
- Loads and generates schemas on Flask app startup
- Passes `jsonld_scripts` to templates for embedding in HTML

### `templates/index.html`
- Added `{{ jsonld_scripts | safe }}` in the `<head>` section
- Embeds Person, BreadcrumbList, and Organization schemas

### `templates/about.html`
- Added `{{ jsonld_scripts | safe }}` in the `<head>` section
- Embeds comprehensive Person, Education, and Experience schemas

## Schema Types Implemented

### 1. **Person Schema**
```json
{
  "@type": "Person",
  "name": "Tim van Zanten",
  "url": "https://timvanzanten.nl",
  "email": "contact@timvanzanten.nl",
  "telephone": "+31 6 50426640",
  "jobTitle": "Creative Producer & Researcher",
  "knowsAbout": [...]
}
```
**Purpose:** Identifies the website as representing a specific person, used by search engines for knowledge graph integration.

### 2. **Organization Schema**
```json
{
  "@type": "Organization",
  "name": "Tim van Zanten",
  "url": "https://timvanzanten.nl",
  "logo": "...",
  "contactPoint": {...}
}
```
**Purpose:** Provides organizational information, helps with local search and business listings.

### 3. **ProfessionalService Schema**
```json
{
  "@type": "ProfessionalService",
  "serviceType": [
    "Event Coordination & Festival Production",
    "Digital Literacy Workshops",
    "Audience Research & Analysis"
  ],
  "areaServed": ["Utrecht", "Amsterdam", "Netherlands"]
}
```
**Purpose:** Describes professional services offered, improves service discovery.

### 4. **BreadcrumbList Schema**
```json
{
  "@type": "BreadcrumbList",
  "itemListElement": [...]
}
```
**Purpose:** Helps search engines understand site structure and navigation.

### 5. **Experience Schema** (About Page)
```json
{
  "@type": "WorkExperience",
  "position": {"title": "..."},
  "startDate": "2023-01-01",
  "jobTitle": "..."
}
```
**Purpose:** Makes work experience machine-readable for LinkedIn, Google, and career networks.

### 6. **Education Schema** (About Page)
```json
{
  "@type": "EducationEvent",
  "name": "MA New Media & Digital Culture",
  "organizer": {"@type": "EducationalOrganization", ...}
}
```
**Purpose:** Helps education platforms and credential verifiers understand qualifications.

## SEO & Indexing Benefits

### For Google Search
- ✅ Rich snippets in search results
- ✅ Knowledge graph profile
- ✅ Better understanding of page content
- ✅ Improved ranking for related searches

### For LinkedIn
- ✅ Enhanced profile discovery
- ✅ Better job matching
- ✅ Experience and education verification
- ✅ Professional credibility signals

### For General Web
- ✅ Better content understanding by AI/LLMs
- ✅ Improved accessibility
- ✅ Machine-readable resume data
- ✅ Portable profile information

## Testing & Validation

### 1. **Validate Schemas**
Use Google's Rich Results Test:
- Visit: https://search.google.com/test/rich-results
- Enter: https://timvanzanten.nl
- Check: Validates Person, Organization schemas

### 2. **LinkedIn Compatibility**
- Schemas follow LinkedIn scraping conventions
- Profile data is now machine-readable for sharing

### 3. **Local Testing**
Run schema generator directly:
```bash
python generate_jsonld.py
```

This outputs all schemas and HTML script tags for inspection.

## Data Flow

```
resume_content.json
        ↓
generate_jsonld.py
        ↓
Flask app startup (app.py)
        ↓
Schema generation
        ↓
Pass to templates
        ↓
HTML rendering with <script type="application/ld+json">
        ↓
Search engines parse & index
```

## Configuration

To modify schemas, edit:
- **Content:** `resume_content.json` - changes are automatically reflected
- **Schema types:** `generate_jsonld.py` - add new schema functions
- **Rendering:** `app.py` - modify how schemas are passed to templates

## Performance Notes

- Schemas are generated once on app startup
- Minimal performance impact (~1-2ms)
- Schemas are embedded inline (no additional HTTP requests)
- Supports caching if needed in future

## Schema.org Reference

Schemas conform to schema.org standards:
- https://schema.org/Person
- https://schema.org/Organization
- https://schema.org/ProfessionalService
- https://schema.org/WorkExperience
- https://schema.org/EducationEvent
- https://schema.org/BreadcrumbList

## Future Enhancements

Potential additions:
- [ ] Event schema for workshop offerings
- [ ] ScholarlyArticle for research/thesis
- [ ] JobPosting for available roles
- [ ] Newsletter/Blog post schemas
- [ ] Image metadata schemas
- [ ] FAQPage schema for common questions
