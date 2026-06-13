import re
from config import settings


async def summarize(title: str, company: str, description: str, dedup_key: str = "") -> str:
    """Generate a 1-2 sentence summary. Uses cache + Claude if available, else truncates."""
    clean = re.sub(r"<[^>]+>", "", description).strip()
    fallback = clean[:200].rsplit(" ", 1)[0] + "..." if len(clean) > 200 else clean

    # Check cache first
    if dedup_key:
        from database import get_cached_summary
        cached = await get_cached_summary(dedup_key)
        if cached:
            return cached

    # No cache hit — generate summary
    summary = fallback

    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic()
            msg = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Buat ringkasan 1-2 kalimat dalam Bahasa Indonesia untuk lowongan ini:\n"
                            f"Posisi: {title} di {company}\n{clean[:1000]}"
                        ),
                    }
                ],
            )
            summary = msg.content[0].text.strip()
        except Exception:
            pass  # fall through to plain summary

    # Cache the result
    if dedup_key and summary != fallback:
        from database import cache_summary
        await cache_summary(dedup_key, summary)

    return summary
