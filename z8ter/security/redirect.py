"""Safe redirect URL validation for Z8ter.

This module prevents open redirect vulnerabilities by validating redirect URLs
before use. Only relative URLs or URLs to the same host are considered safe.

Security considerations:
- Always validate user-supplied redirect URLs before redirecting
- Default to a safe fallback URL when validation fails
- Be careful with protocol-relative URLs (//evil.com)
"""

from urllib.parse import urlparse


def is_safe_redirect_url(url: str, allowed_hosts: set[str] | None = None) -> bool:
    """Validate that a redirect URL is safe.

    A URL is considered safe if:
    - It is a relative URL (no scheme/netloc), or
    - It has a netloc that matches the allowed hosts

    Args:
        url: The URL to validate
        allowed_hosts: Set of allowed hostnames. If None, only relative URLs are allowed.

    Returns:
        True if the URL is safe to redirect to, False otherwise.

    Examples:
        >>> is_safe_redirect_url("/dashboard")
        True
        >>> is_safe_redirect_url("https://evil.com/steal")
        False
        >>> is_safe_redirect_url("https://myapp.com/home", {"myapp.com"})
        True

    Security notes:
        - Protocol-relative URLs (//evil.com) are rejected
        - URLs with credentials (user:pass@host) are rejected
        - Empty URLs return False
    """
    if not url or not isinstance(url, str):
        return False

    # Strip whitespace
    url = url.strip()

    # Reject protocol-relative URLs (//evil.com)
    if url.startswith("//"):
        return False

    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    # Reject URLs with credentials
    if parsed.username or parsed.password:
        return False

    # If no netloc, it's a relative URL - safe
    if not parsed.netloc:
        # But make sure it doesn't have a scheme that could be dangerous
        if parsed.scheme and parsed.scheme.lower() not in ("", "http", "https"):
            return False
        return True

    # If there's a netloc, check if it's in allowed hosts
    if allowed_hosts:
        # Normalize host (lowercase, strip port for comparison)
        host = parsed.netloc.lower()
        if ":" in host:
            host = host.split(":")[0]
        return host in allowed_hosts

    # Has a netloc but no allowed hosts configured - reject
    return False


def get_safe_redirect_url(
    url: str | None,
    fallback: str = "/",
    allowed_hosts: set[str] | None = None,
) -> str:
    """Get a safe redirect URL, with fallback.

    Validates the provided URL and returns it if safe, otherwise returns
    the fallback URL.

    Args:
        url: The URL to validate (may be None)
        fallback: Safe URL to return if validation fails (default: "/")
        allowed_hosts: Set of allowed hostnames for absolute URLs

    Returns:
        The validated URL if safe, otherwise the fallback URL.

    Examples:
        >>> get_safe_redirect_url("/dashboard")
        '/dashboard'
        >>> get_safe_redirect_url("https://evil.com", fallback="/home")
        '/home'
        >>> get_safe_redirect_url(None)
        '/'
    """
    if url and is_safe_redirect_url(url, allowed_hosts):
        return url
    return fallback
