"""Central import of all ORM models so Alembic autogenerate sees them.
Grouped by domain. Add new models to their group file and re-export here."""

from app.core.db import Base
from app.models.auth import EmailVerification, RateLimit, RefreshToken
from app.models.category import Category
from app.models.company import Company, CompanyDomain
from app.models.subject import Subject
from app.models.notifications import Notification, PushSubscription
from app.models.daily_quiz import (
    DailyAttempt,
    DailyAttemptAnswer,
    DailyQuiz,
    DailyQuizQuestion,
)
from app.models.pack import (
    Pack,
    PackAttempt,
    PackAttemptAnswer,
    PackPurchase,
    PackQuestion,
    PackSubscription,  # transitional alias
)
from app.models.question import (
    Question,
    QuestionAnswer,
    QuestionChoice,
    QuestionReport,
)
from app.models.social import Block, Friendship
from app.models.stats import (
    Badge,
    StreakEvent,
    UserBadge,
    UserStats,
)
from app.models.user import User, UserCompanyMembership, UserSettings

__all__ = [
    "Base",
    # user
    "User",
    "UserSettings",
    "UserCompanyMembership",
    # company
    "Company",
    "CompanyDomain",
    # auth
    "EmailVerification",
    "RefreshToken",
    "RateLimit",
    # subject (학습 분야)
    "Subject",
    # category
    "Category",
    # question
    "Question",
    "QuestionChoice",
    "QuestionAnswer",
    "QuestionReport",
    # daily quiz
    "DailyQuiz",
    "DailyQuizQuestion",
    "DailyAttempt",
    "DailyAttemptAnswer",
    # pack
    "Pack",
    "PackQuestion",
    "PackPurchase",
    "PackSubscription",  # transitional alias
    "PackAttempt",
    "PackAttemptAnswer",
    # stats
    "UserStats",
    "StreakEvent",
    "Badge",
    "UserBadge",
    # social
    "Friendship",
    "Block",
    # notifications
    "PushSubscription",
    "Notification",
]
