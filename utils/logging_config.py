import os
from logging.config import dictConfig

def setup_logging(app_name='app', log_level='INFO', log_dir='logs'):
    """Sets up logging configuration."""
    os.makedirs(log_dir, exist_ok=True)

    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': log_level,
            },
            'general_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, f'{app_name}_general.log'),
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
                'formatter': 'default',
                'level': log_level,
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, f'{app_name}_errors.log'),
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
                'formatter': 'default',
                'level': 'ERROR',
            },
            'security_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, f'{app_name}_security.log'),
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
                'formatter': 'default',
                'level': 'INFO',
            },
        },
        'loggers': {
            'app.general': {
                'handlers': ['console', 'general_file'],
                'level': log_level,
                'propagate': False,
            },
            'app.error': {
                'handlers': ['console', 'error_file'],
                'level': 'ERROR',
                'propagate': False,
            },
            'app.security': {
                'handlers': ['console', 'security_file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'general_file'],
        },
    }

    dictConfig(log_config)
