from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    external_id: str
    source: str
    source_url: str
    title: str
    company_name: str
    location: str = ""
    is_remote: bool = False
    is_hybrid: bool = False
    work_type: str = ""
    experience_level: str = "unknown"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description_summary: str = ""
    skills: list[str] = field(default_factory=list)
    posted_at: str = ""


@dataclass
class Preferences:
    work_type: str = "any"         # any, remote, onsite, hybrid
    experience_level: str = "any"  # any, entry, mid, senior
    job_type: str = "any"          # any, fulltime, parttime, contract, freelance, internship
    notification_mode: str = "instant"  # instant, daily, weekly


@dataclass
class User:
    telegram_id: int
    username: str = ""
    first_name: str = ""
    is_subscribed: bool = False
    notification_mode: str = "instant"
    preferences: Preferences = field(default_factory=Preferences)
