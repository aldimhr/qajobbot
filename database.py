import aiosqlite
import json
from config import settings

DB_PATH = settings.DB_PATH

CREATE_JOBS = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT NOT NULL,
    source          TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    title           TEXT NOT NULL,
    company_name    TEXT NOT NULL,
    location        TEXT,
    is_remote       INTEGER DEFAULT 0,
    is_hybrid       INTEGER DEFAULT 0,
    work_type       TEXT,
    experience_level TEXT DEFAULT 'unknown',
    salary_min      INTEGER,
    salary_max      INTEGER,
    description_summary TEXT,
    skills          TEXT,
    posted_at       TEXT,
    scraped_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_active       INTEGER DEFAULT 1,
    UNIQUE(source, external_id)
);
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id     INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    is_subscribed   INTEGER DEFAULT 0,
    notification_mode TEXT DEFAULT 'instant',
    preferences     TEXT DEFAULT '{}',
    subscribed_at   TEXT,
    last_active_at  TEXT DEFAULT (datetime('now'))
);
"""

CREATE_SENT_JOBS = """
CREATE TABLE IF NOT EXISTS sent_jobs (
    user_id  INTEGER NOT NULL,
    job_id   INTEGER NOT NULL,
    sent_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, job_id)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs(scraped_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_jobs_active  ON jobs(is_active) WHERE is_active=1;",
    "CREATE INDEX IF NOT EXISTS idx_jobs_source  ON jobs(source);",
]

CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
    title, company_name, location, description_summary, skills,
    content=jobs, content_rowid=id
);
"""

CREATE_FTS_TRIGGERS = [
    """
CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, company_name, location, description_summary, skills)
    VALUES (new.id, new.title, new.company_name, new.location, new.description_summary, new.skills);
END;
""",
    """
CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company_name, location, description_summary, skills)
    VALUES ('delete', old.id, old.title, old.company_name, old.location, old.description_summary, old.skills);
END;
""",
    """
CREATE TRIGGER IF NOT EXISTS jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, company_name, location, description_summary, skills)
    VALUES ('delete', old.id, old.title, old.company_name, old.location, old.description_summary, old.skills);
    INSERT INTO jobs_fts(rowid, title, company_name, location, description_summary, skills)
    VALUES (new.id, new.title, new.company_name, new.location, new.description_summary, new.skills);
END;
""",
]


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute(CREATE_JOBS)
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_SENT_JOBS)
        for idx in CREATE_INDEXES:
            await db.execute(idx)
        await db.execute(CREATE_FTS)
        for trigger in CREATE_FTS_TRIGGERS:
            await db.execute(trigger)
        await db.commit()


async def save_job(job: dict) -> bool:
    """Insert job, ignore if duplicate. Returns True if newly inserted."""
    async with aiosqlite.connect(DB_PATH) as db:
        skills = job.get("skills", "")
        if isinstance(skills, list):
            skills_str = ",".join(skills)
        else:
            skills_str = str(skills)
        try:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO jobs
                    (external_id, source, source_url, title, company_name, location,
                     is_remote, is_hybrid, work_type, experience_level,
                     salary_min, salary_max, description_summary, skills, posted_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    job["external_id"], job["source"], job["source_url"],
                    job["title"], job["company_name"], job.get("location", ""),
                    int(job.get("is_remote", False)), int(job.get("is_hybrid", False)),
                    job.get("work_type", ""), job.get("experience_level", "unknown"),
                    job.get("salary_min"), job.get("salary_max"),
                    job.get("description_summary", ""), skills_str,
                    job.get("posted_at", ""),
                ),
            )
            await db.commit()
            return cursor.rowcount > 0
        except aiosqlite.IntegrityError:
            return False


async def get_new_jobs(since_minutes: int = 16) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM jobs
            WHERE scraped_at > datetime('now', ? || ' minutes')
              AND is_active = 1
            ORDER BY scraped_at DESC
            """,
            (f"-{since_minutes}",),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_unsent_jobs(user_id: int, since_minutes: int = 60) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT j.* FROM jobs j
            WHERE j.scraped_at > datetime('now', ? || ' minutes')
              AND j.is_active = 1
              AND j.id NOT IN (SELECT job_id FROM sent_jobs WHERE user_id = ?)
            ORDER BY j.scraped_at DESC
            """,
            (f"-{since_minutes}", user_id),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_sent(user_id: int, job_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_jobs (user_id, job_id) VALUES (?, ?)",
            (user_id, job_id),
        )
        await db.commit()


async def upsert_user(telegram_id: int, username: str = "", first_name: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_active_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active_at = datetime('now')
            """,
            (telegram_id, username, first_name),
        )
        await db.commit()


async def set_subscribed(telegram_id: int, subscribed: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        if subscribed:
            await db.execute(
                "UPDATE users SET is_subscribed = 1, subscribed_at = datetime('now') WHERE telegram_id = ?",
                (telegram_id,),
            )
        else:
            await db.execute(
                "UPDATE users SET is_subscribed = 0 WHERE telegram_id = ?",
                (telegram_id,),
            )
        await db.commit()


async def get_subscribers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE is_subscribed = 1")
        return [dict(r) for r in await cursor.fetchall()]


async def get_recent_jobs(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM jobs WHERE is_active = 1 ORDER BY scraped_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def search_jobs(query: str, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT j.* FROM jobs j
            JOIN jobs_fts fts ON j.id = fts.rowid
            WHERE jobs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def update_user_preferences(telegram_id: int, prefs: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET preferences = ? WHERE telegram_id = ?",
            (json.dumps(prefs), telegram_id),
        )
        await db.commit()


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sent_jobs WHERE user_id = ?", (telegram_id,))
        await db.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        await db.commit()


async def purge_old_jobs(days: int = 90):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM jobs WHERE scraped_at < datetime('now', ? || ' days')",
            (f"-{days}",),
        )
        await db.commit()


async def get_digest_jobs(since_hours: int = 24) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM jobs
            WHERE scraped_at > datetime('now', ? || ' hours')
              AND is_active = 1
            ORDER BY scraped_at DESC
            LIMIT 10
            """,
            (f"-{since_hours}",),
        )
        return [dict(r) for r in await cursor.fetchall()]
