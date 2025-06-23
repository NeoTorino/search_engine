from routes.main_routes import main_bp
from routes.utility_routes import utility_bp
from routes.search_routes import search_bp
from routes.error_routes import error_bp

def register_blueprints(app):
    """Register all application blueprints"""

    app.register_blueprint(main_bp)
    app.register_blueprint(utility_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(error_bp)
