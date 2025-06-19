from datetime import datetime
from settings import config as base_config


class ConfigManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._load_config()
            self._initialized = True

    def _load_config(self):
        """Load all configuration settings"""

        # 'comma_separated_list', 'integer_with_default',
        # 'integer_with_range', 'fallback_param',
        # 'negative_to_default', 'filtered_list'
        self.search_config = {
            'q': {
                'type': 'fallback_param',
                'default': ''
            },
            'countries': {
                'type': 'comma_separated_list',
                'fallback': 'country',
                'max_items': 10,
                'filter_empty': True
            },
            'organizations': {
                'type': 'comma_separated_list',
                'fallback': 'organization',
                'max_items': 10,
                'filter_empty': True
            },
            'sources': {
                'type': 'comma_separated_list',
                'fallback': 'source',
                'max_items': 5,
                'filter_empty': True
            },
            'offset': {
                'type': 'integer_with_range',
                'default': 0,
                'min_value': 0,
                'max_value': 10000
            },
            'limit': {
                'type': 'integer_with_range',
                'default': 20,
                'min_value': 1,
                'max_value': 100
            },
            'date_posted_days': {
                'type': 'negative_to_default',
                'default': 365,
                'negative_default': 365
            }
        }

    def to_dict(self):
        """Enhanced to_dict with better data handling"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (list, dict, bool)):
                result[key] = value
            else:
                result[key] = str(value)
        return result

    def to_iso(self, dt):
        return dt.isoformat() if dt else None

    def print_json(self):
        print(json.dumps(self.to_dict(), indent=4))

    def confirm_settings(self):
        """Print settings and ask for user confirmation"""
        print("Configuration Settings:")
        self.print_json()
        confirmation = input("Do you want to proceed? (Y/n): ").strip().lower()
        if confirmation not in ['y', 'yes', '']:
            print("Operation cancelled.")
            sys.exit(0)  # Exit the script if the user does not confirm

config = ConfigManager()