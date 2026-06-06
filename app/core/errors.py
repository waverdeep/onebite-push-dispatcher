# NOTE: onebite-quiz-publisher copy of app/core/errors.py, trimmed for the
# publisher Job. The error CLASSES below are kept byte-for-byte identical to the
# onebite-server original (keep them in sync). What is intentionally dropped is
# the FastAPI-only HTTP wiring (register_exception_handlers / _envelope /
# _request_id), so the Job does not depend on FastAPI. To preserve the
# `status.HTTP_*` references unchanged, `status` is a tiny local shim exposing
# the same integer codes FastAPI's `fastapi.status` module would.
class status:  # noqa: N801 - mirrors fastapi.status's HTTP_* attribute names
    HTTP_400_BAD_REQUEST = 400
    HTTP_401_UNAUTHORIZED = 401
    HTTP_403_FORBIDDEN = 403
    HTTP_404_NOT_FOUND = 404
    HTTP_409_CONFLICT = 409
    HTTP_422_UNPROCESSABLE_ENTITY = 422
    HTTP_423_LOCKED = 423
    HTTP_429_TOO_MANY_REQUESTS = 429
    HTTP_500_INTERNAL_SERVER_ERROR = 500


class AppError(Exception):
    """Base application error mapped to the standard error envelope.

    Domain layers raise subclasses (or AppError directly) with a
    SCREAMING_SNAKE_CASE code following the {DOMAIN}_{REASON} convention.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "INTERNAL_ERROR"
    message: str = "요청을 처리할 수 없습니다."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)


# --- a few common errors; domains extend with their own subclasses ---
class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "리소스를 찾을 수 없습니다."


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_INVALID_TOKEN"
    message = "인증에 실패했습니다."


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMIT_EXCEEDED"
    message = "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "이미 존재하는 리소스입니다."


# --- Auth domain errors (see docs/api-auth.html section 7) ---
class CodeInvalidError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "AUTH_CODE_INVALID"
    message = "인증 코드가 올바르지 않습니다."


class CodeExpiredError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "AUTH_CODE_EXPIRED"
    message = "인증 코드가 만료되었습니다."


class CodeAlreadyUsedError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "AUTH_CODE_ALREADY_USED"
    message = "이미 사용된 인증 코드입니다."


class CodeNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "AUTH_CODE_NOT_FOUND"
    message = "발급된 인증 코드가 없습니다."


class CodeLockedError(AppError):
    status_code = status.HTTP_423_LOCKED
    code = "AUTH_CODE_LOCKED"
    message = "인증 시도 횟수를 초과했습니다. 코드를 다시 요청해주세요."


class TokenRevokedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_TOKEN_REVOKED"
    message = "사용할 수 없는 토큰입니다. 다시 로그인해주세요."


class TokenNotFoundError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_TOKEN_NOT_FOUND"
    message = "유효하지 않은 토큰입니다."


class SessionInvalidatedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTH_SESSION_INVALIDATED"
    message = "세션이 만료되었습니다. 다시 로그인해주세요."


# --- Daily Quiz domain errors (see docs/api-daily-quiz.html section 9) ---
class QuizNotOpenError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "QUIZ_NOT_OPEN"
    message = "아직 오늘의 퀴즈가 오픈되지 않았습니다."


class QuizClosedError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "QUIZ_CLOSED"
    message = "퀴즈 마감 시간이 지났습니다."


class QuizNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "QUIZ_NOT_FOUND"
    message = "해당 날짜의 퀴즈가 없습니다."


class QuizAttemptNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "QUIZ_ATTEMPT_NOT_FOUND"
    message = "퀴즈 시도 기록이 없습니다."


class QuizAlreadySubmittedError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "QUIZ_ALREADY_SUBMITTED"
    message = "이미 완료된 시도입니다."


class QuizInvalidOrderError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "QUIZ_INVALID_ORDER"
    message = "문제 풀이 순서가 올바르지 않습니다."


class QuizAnswerDuplicateError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "QUIZ_ANSWER_DUPLICATE"
    message = "이미 답안을 제출한 문제입니다."


class QuizAnswerInvalidError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "QUIZ_ANSWER_INVALID"
    message = "답안 형식이 문제 유형과 일치하지 않습니다."


class QuizNotCompletedError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "QUIZ_NOT_COMPLETED"
    message = "아직 완료되지 않은 시도입니다."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "AUTH_FORBIDDEN"
    message = "접근 권한이 없습니다."


# --- Practice domain errors (see docs/api-practice.html section 9) ---
class CategoryNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "CATEGORY_NOT_FOUND"
    message = "존재하지 않거나 비활성 카테고리입니다."


class QuestionNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "QUESTION_NOT_FOUND"
    message = "존재하지 않는 문제입니다."


class QuestionNotAvailableError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "QUESTION_NOT_AVAILABLE"
    message = "현재 풀 수 없는 문제입니다."


class PracticeAnswerInvalidError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "PRACTICE_ANSWER_INVALID"
    message = "답안 형식이 문제 유형과 일치하지 않습니다."


class EmailTakenError(ConflictError):
    code = "USER_EMAIL_TAKEN"
    message = "이미 가입된 이메일입니다."


class NicknameTakenError(ConflictError):
    code = "USER_NICKNAME_TAKEN"
    message = "이미 사용 중인 닉네임입니다."


# --- Friends domain errors (see docs/api-friends.html section 8) ---
class FriendSelfNotAllowedError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "FRIEND_SELF_NOT_ALLOWED"
    message = "자기 자신에게는 친구 요청을 보낼 수 없습니다."


class UserNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "USER_NOT_FOUND"
    message = "사용자를 찾을 수 없습니다."


class FriendAlreadyFriendsError(ConflictError):
    code = "FRIEND_ALREADY_FRIENDS"
    message = "이미 친구입니다."


class FriendAlreadyRequestedError(ConflictError):
    code = "FRIEND_ALREADY_REQUESTED"
    message = "이미 친구 요청을 보냈습니다."


class FriendBlockedByYouError(ConflictError):
    code = "FRIEND_BLOCKED_BY_YOU"
    message = "차단한 사용자입니다. 차단을 해제해주세요."


class FriendRequestNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "FRIEND_REQUEST_NOT_FOUND"
    message = "친구 요청을 찾을 수 없습니다."


class FriendInvalidStateError(ConflictError):
    code = "FRIEND_INVALID_STATE"
    message = "현재 상태에서 처리할 수 없는 요청입니다."


class BlockSelfNotAllowedError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BLOCK_SELF_NOT_ALLOWED"
    message = "자기 자신은 차단할 수 없습니다."


# --- Rankings domain errors (see docs/api-rankings.html) ---
class CompanyNotVerifiedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "COMPANY_NOT_VERIFIED"
    message = "회사 인증이 필요합니다."


class CompanyRankingNotAvailableError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "COMPANY_RANKING_NOT_AVAILABLE"
    message = "회사 랭킹은 5명 이상 모이면 활성화됩니다."


# --- Reports domain errors (see docs/api-companies-reports.html) ---
class ReportDuplicateError(ConflictError):
    code = "REPORT_DUPLICATE"
    message = "이미 신고한 문제입니다."
