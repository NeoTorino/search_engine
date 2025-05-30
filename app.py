from datetime import datetime
import secrets
import urllib3
from flask import Flask
from flask import g

from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from filters.custom_filters import register_filters
from middleware.secure_headers import apply_secure_headers
from routes.main_routes import main

# Load environment
load_dotenv(".env")

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

@app.before_request
def set_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)

@app.context_processor
def inject_nonce():
    return dict(nonce=g.csp_nonce)

@app.context_processor
def inject_now():
    return {'year': datetime.utcnow().year}

# Register secure headers
app.after_request(apply_secure_headers)

# Register Jinja2 filters
register_filters(app)

# Register blueprints
app.register_blueprint(main)

if __name__ == '__main__':
    app.run(debug=True)
