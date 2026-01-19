from app.identity.usecases.manage_users import ManageUsers
from z8ter.auth.guards import skip_if_authenticated
from z8ter.endpoints.view import View
from z8ter.requests import Request
from z8ter.responses import RedirectResponse, Response
from z8ter.security.audit import SecurityEvent, log_security_event
from z8ter.security.validators import validate_email, validate_password


class Register(View):
    @skip_if_authenticated
    async def get(self, request: Request) -> Response:
        return self.render(request, "pages/register.jinja", {})

    @skip_if_authenticated
    async def post(self, request: Request) -> Response:
        mu = ManageUsers(request.app.state.user_repo)
        form = await request.form()

        email = str(form.get("email") or "").strip().lower()
        pwd = str(form.get("password") or "")
        pwd2 = str(form.get("password2") or "")

        # Get client info for logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Validate email format
        email_result = validate_email(email)
        if not email_result.valid:
            return RedirectResponse(
                f"/register?e=invalid_email&msg={email_result.error}",
                status_code=303,
            )

        # Validate password policy (minimum 8 characters)
        pwd_result = validate_password(pwd, min_length=8)
        if not pwd_result.valid:
            return RedirectResponse(
                f"/register?e=weak_password&msg={pwd_result.error}",
                status_code=303,
            )

        # Check password confirmation match
        if pwd != pwd2:
            return RedirectResponse("/register?e=password_mismatch", status_code=303)

        # Check for duplicate email
        if await mu.email_exists(email):
            return RedirectResponse("/register?e=email_exists", status_code=303)

        # Create user
        user_id = await mu.create_user(email, pwd)

        # Log account creation
        log_security_event(
            SecurityEvent.ACCOUNT_CREATED,
            user_id=user_id,
            email=email,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return RedirectResponse("/login?m=signup_ok", status_code=303)
