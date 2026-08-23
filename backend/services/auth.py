"""注册与登录业务。"""

# 验证码校验成功后才执行密码验证，降低自动化撞库风险。
from backend.core.config import Settings
from backend.core.exceptions import BusinessError
from backend.core.security import create_access_token, hash_password, verify_password
from backend.models.user import User
from backend.repositories.user_repository import UserRepository
from backend.services.captcha import CaptchaService
from backend.services.rate_limit import AuthRateLimiter


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        captcha_service: CaptchaService,
        settings: Settings,
        rate_limiter: AuthRateLimiter | None = None,
    ):
        self.repository = repository
        self.captcha_service = captcha_service
        self.settings = settings
        self.rate_limiter = rate_limiter

    def register(
        self,
        username: str,
        password: str,
        confirm_password: str,
        captcha_id: str,
        captcha_code: str,
        client_key: str = "",
    ) -> User:
        if self.rate_limiter:
            self.rate_limiter.check("register", client_key, username)
        self._verify_captcha(captcha_id, captcha_code)
        if password != confirm_password:
            raise BusinessError("两次输入的密码不一致", "PASSWORD_MISMATCH")
        if self.repository.get_by_username(username) is not None:
            raise BusinessError("用户名已存在", "USERNAME_EXISTS", 409)
        return self.repository.create(username=username, password_hash=hash_password(password))

    def login(
        self,
        username: str,
        password: str,
        captcha_id: str,
        captcha_code: str,
        client_key: str = "",
    ) -> tuple[User, str, int]:
        if self.rate_limiter:
            self.rate_limiter.check("login", client_key, username)
        self._verify_captcha(captcha_id, captcha_code)
        user = self.repository.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise BusinessError("用户名或密码错误", "INVALID_CREDENTIALS", 401)
        if not user.is_active:
            raise BusinessError("账号已停用", "USER_DISABLED", 403)
        token, expires_in = create_access_token(user.id, self.settings)
        return user, token, expires_in

    def _verify_captcha(self, captcha_id: str, captcha_code: str) -> None:
        if not self.captcha_service.verify(captcha_id, captcha_code):
            raise BusinessError("验证码错误或已过期", "INVALID_CAPTCHA")
