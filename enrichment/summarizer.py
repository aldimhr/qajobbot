import re
from config import settings


async def summarize(title: str, company: str, description: str) -> str:
    """Generate a 2-sentence summary. Uses Claude if ANTHROPIC_API_KEY set, else truncates."""
    clean = re.sub(r"<[^>]+>", "", description).strip()
    summary = clean[:200].rsplit(" ", 1)[0] + "..." if len(clean) > 200 else clean

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

    return summary
