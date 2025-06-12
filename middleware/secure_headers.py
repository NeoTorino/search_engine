from flask import g, request
import secrets

# def apply_secure_headers(response):
#     nonce = getattr(g, "csp_nonce", "")  # Get nonce from Flask's global context

#     response.headers["X-Content-Type-Options"] = "nosniff"
#     response.headers["X-Frame-Options"] = "DENY"
#     response.headers["X-XSS-Protection"] = "1; mode=block"
#     response.headers["Content-Security-Policy"] = (
#         f"default-src 'self'; "
#         f"img-src 'self' data:; "
#         f"style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
#         f"font-src 'self' https://fonts.gstatic.com; "
#         f"script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com https://unpkg.com https://cdnjs.cloudflare.com 'nonce-{nonce}';"
#     )
#     return response


def apply_secure_headers(response):
    """Apply comprehensive security headers"""
    
    # Get CSP nonce
    nonce = getattr(g, 'csp_nonce', secrets.token_urlsafe(16))
    
    # Content Security Policy (very strict)
    csp_policy = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "connect-src 'self'; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests"
    )
    
    response.headers['Content-Security-Policy'] = csp_policy
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HSTS (if HTTPS)
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    # Additional security headers
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    
    # Remove server information
    response.headers.pop('Server', None)
    response.headers.pop('X-Powered-By', None)
    
    # Cache control for sensitive pages
    if request.endpoint in ['search_results', 'stats']:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response