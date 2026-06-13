def format_job_alert(job: dict) -> str:
    """Format a job dict into a Telegram markdown message."""
    level_emoji = {"entry": "🟢", "mid": "🟡", "senior": "🔴"}.get(
        job.get("experience_level", "mid"), "⚪"
    )

    title = job.get("title", "Unknown Position")
    company = job.get("company_name", "Unknown Company")
    lines = [f"🧪 *{_escape_md(title)}* — {_escape_md(company)}"]

    # Location
    location = job.get("location", "")
    remote_tag = ""
    if job.get("is_remote"):
        remote_tag = " (Remote)"
    elif job.get("is_hybrid"):
        remote_tag = " (Hybrid)"
    if location:
        lines.append(f"\n📍 {_escape_md(location)}{remote_tag}")

    # Work type + level
    work_type = job.get("work_type", "")
    level = job.get("experience_level", "")
    parts = []
    if work_type:
        parts.append(_escape_md(work_type))
    if level and level != "unknown":
        parts.append(f"{level_emoji} {level.capitalize()}")
    if parts:
        lines.append(f"💼 {' · '.join(parts)}")

    # Salary
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if salary_min or salary_max:
        salary_str = _format_salary(salary_min, salary_max)
        lines.append(f"💰 {salary_str}")

    # Skills
    skills = job.get("skills", "")
    if isinstance(skills, list) and skills:
        skills_list = ", ".join(skills)
    elif isinstance(skills, str) and skills:
        skills_list = skills
    else:
        skills_list = ""
    if skills_list:
        lines.append(f"\n🔧 *Skills:* {_escape_md(skills_list)}")

    # Description summary
    desc = job.get("description_summary", "")
    if desc:
        lines.append(f"\n📝 {_escape_md(desc[:200])}")

    # Apply link
    source_url = job.get("source_url", "")
    if source_url:
        lines.append(f"\n🔗 [Apply Now]({source_url})")

    # Source + posted
    source = job.get("source", "")
    posted = job.get("posted_at", "")
    meta_parts = []
    if posted:
        meta_parts.append(f"📅 {_escape_md(posted[:10])}")
    if source:
        meta_parts.append(f"Source: {_escape_md(source)}")
    if meta_parts:
        lines.append(f"{' · '.join(meta_parts)}")

    return "\n".join(lines)


def format_digest(jobs: list[dict]) -> str:
    """Format a daily/weekly digest of jobs as a compact list."""
    if not jobs:
        return "📭 No new jobs in the last 24 hours."

    lines = [f"📋 *Latest QA Jobs* ({len(jobs)} jobs)\n"]
    for i, job in enumerate(jobs, 1):
        title = job.get("title", "")
        company = job.get("company_name", "")
        source_url = job.get("source_url", "")
        link = f" [Lamar]({source_url})" if source_url else ""
        lines.append(f"{i}. {_escape_md(title)} — {_escape_md(company)}{link}")

    return "\n".join(lines)


def _escape_md(text: str) -> str:
    """Escape Telegram Markdown special characters."""
    for char in ["_", "*", "[", "]", "`"]:
        text = text.replace(char, f"\\{char}")
    return text


def _format_salary(min_val, max_val) -> str:
    """Format salary range in IDR."""
    if min_val and max_val:
        return f"IDR {min_val:,.0f} – {max_val:,.0f}".replace(",", ".")
    elif min_val:
        return f"IDR {min_val:,.0f}+".replace(",", ".")
    elif max_val:
        return f"Up to IDR {max_val:,.0f}".replace(",", ".")
    return ""
