from starlette.datastructures import FormData

from app.identity.usecases.manage_sessions import ManageSessions
from app.identity.usecases.manage_users import ManageUsers
from z8ter.auth.crypto import hash_password, verify_password
from z8ter.auth.guards import get_post_login_redirect, skip_if_authenticated
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import RedirectResponse, Response
from z8ter.security.audit import SecurityEvent, log_security_event

# Pre-computed dummy hash for timing attack prevention
# This ensures login attempts for non-existent users take the same time
# as attempts for existing users with wrong passwords
_DUMMY_HASH = hash_password("dummy_password_for_timing_attack_prevention")


class Login(View):
    @skip_if_authenticated
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/login.jinja", {})

    @skip_if_authenticated
    async def post(self, request: Request) -> Response:
        form: FormData = await request.form()
        ms = ManageSessions(request.app.state.session_repo)
        mu = ManageUsers(request.app.state.user_repo)

        if form is None:
            raise TypeError("Form data is None")

        email = str(form.get("email") or "").strip().lower()
        pwd = str(form.get("password") or "")

        # Get client info for logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Fetch user
        user = await mu.get_user_email(email)

        # Timing attack prevention: always verify against a hash
        # If user doesn't exist, verify against dummy hash to maintain constant time
        hash_to_check = user["pwd_hash"] if user else _DUMMY_HASH
        ok = verify_password(hash_to_check, pwd)

        # Check authentication result
        if not user or not ok:
            # Log failed login attempt
            log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                email=email,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                details={"reason": "invalid_credentials"},
            )
            return RedirectResponse("/login?e=badcreds", status_code=303)

        # Session fixation prevention: revoke any existing sessions for this cookie
        # This ensures a fresh session is created on each login
        existing_sid = request.cookies.get("z8_sid")
        if existing_sid:
            ms.session_repo.revoke(sid_plain=existing_sid)

        # Create new session
        sid = await ms.start_session(user["id"])

        # Log successful login
        log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            user_id=user["id"],
            email=email,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Get safe redirect URL (validates against open redirect attacks)
        config = request.app.state.services["config"]
        app_path = config("APP_PATH")
        redirect_url = get_post_login_redirect(request, fallback=app_path)

        resp = RedirectResponse(redirect_url, status_code=303)

        # Secure cookie configuration: derive from request scheme
        is_secure = request.url.scheme == "https"
        await ms.set_session_cookie(resp, sid, secure=is_secure)

        return resp
