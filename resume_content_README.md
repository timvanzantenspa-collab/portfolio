# Editing the Resume Text

Edit `resume_content.json` when you want to change resume text.

The file now uses an easier bilingual structure: each job/project/skill exists
once, with English and Dutch text next to each other.

Most common changes:

- Contact details: edit `common.phone`, `common.email`, `common.website`, `common.linkedin`.
- Education: edit `common.education`.
- English/Dutch labels: edit `labels.en` and `labels.nl`.
- Profile: edit `profile.en` and `profile.nl`.
- Experience: add, remove, or reorder items in `experience`.
- Job text: each job has `role.en`, `role.nl`, `context.en`, `context.nl`, and `bullets.en` / `bullets.nl`.
- Sidebar sections: edit `skills`, `projects`, and `culture`.

After editing, run:

```powershell
& "C:\Users\timva\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "C:\Python projectjes\Portfolio\generate_resume_pdf.py"
```

Notes:

- Keep commas between items.
- Keep straight double quotes around text.
- Use `\/` is not needed; normal slashes are fine.
- The Python file controls layout and styling. The JSON file controls content.
