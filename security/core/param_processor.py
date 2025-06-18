"""
Enhanced parameter processing for business logic handling
Add this to your security/core/ directory
"""
from typing import Any, Dict, List, Union, Optional, Callable
from flask import request
from security.core.validators import security_validator
from security.middleware.decorators import get_sanitized_param

class ParameterProcessor:
    """Enhanced parameter processor for business logic and data transformation"""

    def __init__(self):
        self.processors = {
            'comma_separated_list': self._process_comma_separated_list,
            'integer_with_default': self._process_integer_with_default,
            'integer_with_range': self._process_integer_with_range,
            'integer_with_range_extra_validation': self._process_integer_with_range_extra_validation,
            'fallback_param': self._process_fallback_param,
            'negative_to_default': self._process_negative_to_default,
            'filtered_list': self._process_filtered_list
        }

    def process_parameters(self, param_config: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Process multiple parameters according to configuration

        Args:
            param_config: Configuration dictionary with parameter processing rules

        Returns:
            Dictionary of processed parameters

        Example config:
        {
            'countries': {
                'type': 'comma_separated_list',
                'fallback': 'country',
                'max_items': 10,
                'filter_empty': True
            },
            'limit': {
                'type': 'integer_with_range_extra_validation',
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
        """
        processed_params = {}

        for param_name, config in param_config.items():
            processor_type = config.get('type', 'fallback_param')

            if processor_type in self.processors:
                processed_params[param_name] = self.processors[processor_type](
                    param_name, config
                )
            else:
                # Fallback to basic parameter retrieval
                processed_params[param_name] = get_sanitized_param(
                    param_name, config.get('default')
                )

        return processed_params

    def _process_comma_separated_list(self, param_name: str, config: Dict) -> List[str]:
        """Process comma-separated string into filtered list"""
        fallback = config.get('fallback')
        max_items = config.get('max_items', 50)
        filter_empty = config.get('filter_empty', True)

        # Get raw value with fallback support
        raw_value = get_sanitized_param(param_name)
        if not raw_value and fallback:
            raw_value = get_sanitized_param(fallback)

        if not raw_value:
            return []

        # Handle string input
        if isinstance(raw_value, str):
            items = [item.strip() for item in raw_value.split(',')]
            if filter_empty:
                items = [item for item in items if item]
        elif isinstance(raw_value, list):
            items = [str(item).strip() for item in raw_value]
            if filter_empty:
                items = [item for item in items if item]
        else:
            return []

        # Apply length limit
        return items[:max_items]

    def _process_integer_with_default(self, param_name: str, config: Dict) -> int:
        """Process integer parameter with safe conversion and default"""
        default = config.get('default', 0)

        raw_value = get_sanitized_param(param_name)
        if raw_value is None or raw_value == '':
            return default

        try:
            return int(raw_value)
        except (ValueError, TypeError):
            return default

    def _process_integer_with_range(self, param_name: str, config: Dict) -> int:
        """Process integer with range validation"""
        default = config.get('default', 0)
        min_value = config.get('min_value')
        max_value = config.get('max_value')

        # First get as integer
        value = self._process_integer_with_default(param_name, config)

        # Apply range constraints
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value

        return value

    def _process_integer_with_range_extra_validation(self, param_name: str, config: Dict) -> int:
        """Process integer with range validation plus additional try-catch safety"""
        default = config.get('default', 0)
        min_value = config.get('min_value')
        max_value = config.get('max_value')

        # Additional try-catch validation as requested
        try:
            raw_value = get_sanitized_param(param_name, default)
            value = int(raw_value)
            # Apply max constraint using min() function for extra safety
            if max_value is not None:
                value = min(value, max_value)
            # Apply min constraint
            if min_value is not None and value < min_value:
                value = min_value
        except (ValueError, TypeError):
            value = default

        return value

    def _process_fallback_param(self, param_name: str, config: Dict) -> Any:
        """Process parameter with fallback support"""
        fallback = config.get('fallback')
        default = config.get('default')

        value = get_sanitized_param(param_name)
        if not value and fallback:
            value = get_sanitized_param(fallback)

        return value if value is not None else default

    def _process_negative_to_default(self, param_name: str, config: Dict) -> int:
        """Handle negative values by resetting to default"""
        default = config.get('default', 0)
        negative_default = config.get('negative_default', default)

        # Get as integer first
        value = self._process_integer_with_default(param_name, config)

        # Handle negative values
        if value < 0:
            return negative_default

        return value

    def _process_filtered_list(self, param_name: str, config: Dict) -> List[str]:
        """Process list with custom filtering function"""
        filter_func = config.get('filter_func', lambda x: bool(x.strip()) if isinstance(x, str) else bool(x))
        max_items = config.get('max_items', 50)

        raw_value = get_sanitized_param(param_name, [])

        if not raw_value:
            return []

        # Ensure it's a list
        if not isinstance(raw_value, list):
            raw_value = [raw_value]

        # Apply filter function
        filtered_items = [item for item in raw_value if filter_func(item)]

        # Apply length limit
        return filtered_items[:max_items]

# Global processor instance
parameter_processor = ParameterProcessor()

# Convenience functions
def process_search_parameters() -> Dict[str, Any]:
    """Process common search parameters with business logic"""
    search_config = {
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
            'type': 'integer_with_range_extra_validation',
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

    return parameter_processor.process_parameters(search_config)

def process_api_parameters(config: Dict[str, Dict]) -> Dict[str, Any]:
    """Process API parameters with custom configuration"""
    return parameter_processor.process_parameters(config)

# Pre-defined configurations for common use cases
SEARCH_PARAM_CONFIG = {
    'q': {'type': 'fallback_param', 'default': ''},
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
        'type': 'integer_with_range_extra_validation',
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

FILTER_PARAM_CONFIG = {
    'categories': {
        'type': 'comma_separated_list',
        'fallback': 'category',
        'max_items': 20,
        'filter_empty': True
    },
    'tags': {
        'type': 'comma_separated_list',
        'max_items': 15,
        'filter_empty': True
    },
    'page': {
        'type': 'integer_with_range',
        'default': 1,
        'min_value': 1,
        'max_value': 1000
    }
}

PAGINATION_PARAM_CONFIG = {
    'page': {
        'type': 'integer_with_range',
        'default': 1,
        'min_value': 1,
        'max_value': 1000
    },
    'per_page': {
        'type': 'integer_with_range_extra_validation',
        'default': 20,
        'min_value': 1,
        'max_value': 100
    },
    'offset': {
        'type': 'integer_with_range',
        'default': 0,
        'min_value': 0,
        'max_value': 50000
    }
}
