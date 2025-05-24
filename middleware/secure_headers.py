from flask import g

def apply_secure_headers(response):
    nonce = getattr(g, "csp_nonce", "")  # Get nonce from Flask's global context

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"img-src 'self' data:; "
        f"style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        f"font-src 'self' https://fonts.gstatic.com; "
        f"script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com https://unpkg.com 'nonce-{nonce}';"
    )
    return response
