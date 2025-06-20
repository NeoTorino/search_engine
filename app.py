from config import get_config
from app_factory import create_app
from server import ProductionServer, DevelopmentServer

def main():
    """Main application entry point"""
    config_class = get_config()
    app = create_app(config_class)

    # Initialize config-specific settings
    config_class.init_app(app)

    # Determine server type based on environment
    import os
    if os.getenv('FLASK_ENV') == 'production':
        server = ProductionServer(app)
    else:
        server = DevelopmentServer(app)

    server.run()

if __name__ == '__main__':
    main()

# Export for WSGI servers (gunicorn, uWSGI, etc.)
app = create_app(get_config())
