from routes.main_routes import main
from routes.utility_routes import utility
from routes.api_routes import api
from routes.page_routes import pages
from routes.search_routes import search

def register_blueprints(app):
    """Register all application blueprints"""

    app.register_blueprint(main)
    app.register_blueprint(pages)
    app.register_blueprint(search)
    app.register_blueprint(utility)
    app.register_blueprint(api)
