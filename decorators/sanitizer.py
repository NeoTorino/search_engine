"""
Generic Parameter Sanitization Decorator for Flask Routes

This module provides a flexible decorator factory that creates parameter sanitization
decorators for Flask routes based on a configuration dictionary. It automatically
extracts, sanitizes, and validates parameters from different request sources.

Key Features:
- Supports multiple parameter sources (GET, POST form, JSON, file uploads)
- Flexible sanitization with lambda functions or custom functions
- Automatic parameter validation and error handling
- Monkey-patches Flask request methods to return sanitized values
- Stores sanitized parameters in flask.g for global access

Configuration Dictionary Structure:
    Each parameter is defined with a key (parameter name) and configuration dict:

    sanitization_config = {
        'parameter_name': {
            'source': 'args',           # REQUIRED: Where to extract parameter from
                                       # Options: 'args' (GET params), 'form' (POST form),
                                       #          'json' (JSON body), 'files' (file uploads),
                                       #          'values' (combined args + form)

            'method': 'get',           # REQUIRED: How to extract the value
                                       # Options: 'get' (single value), 'getlist' (list of values)

            'default': None,           # REQUIRED: Default value if parameter missing/invalid
                                       # Can be: any primitive type, list, dict, None, empty string, etc.

            'sanitizer': lambda x: x,  # REQUIRED: Function to sanitize raw value
                                       # Options:
                                       # - Lambda function: lambda x: x.strip().lower()
                                       # - Function reference: my_sanitizer_function
                                       # - Chain with multiple calls: lambda x: sanitize_element(x, limit=(0,500))
                                       # - Identity function: lambda x: x (no sanitization)

            'result_key': 'param',     # OPTIONAL: Key name in sanitized results dict
                                       # Default: uses parameter_name if not specified
                                       # Allows renaming parameters in the sanitized output

            'custom_logic': None       # OPTIONAL: Additional validation function
                                       # Function that receives sanitized value and can apply
                                       # complex validation logic, transformations, or business rules
                                       # Example: lambda x: x if len(x) > 0 else 'default_value'
        }
    }

Parameter Source Details:
    'args':   GET parameters from URL query string (?param=value)
    'form':   POST form data (application/x-www-form-urlencoded or multipart/form-data)
    'json':   JSON data from POST body (application/json)
    'files':  File uploads from multipart forms
    'values': Combined args + form data (Flask's request.values)

Method Details:
    'get':     Extract single value, returns the parameter value or default
    'getlist': Extract list of values, returns list even for single values

Example Configurations:

    # Basic GET parameter sanitization
    {
        'q': {
            'source': 'args',
            'method': 'get',
            'default': '',
            'sanitizer': lambda x: sanitize_element(x, limit=(0, 500)),
            'result_key': 'query'
        }
    }

    # Multiple selection with validation
    {
        'country': {
            'source': 'args',
            'method': 'getlist',
            'default': [],
            'sanitizer': lambda countries: [sanitize_element(c, valid_values=COUNTRIES) for c in countries],
            'result_key': 'selected_countries'
        }
    }

    # POST form data with custom validation
    {
        'username': {
            'source': 'form',
            'method': 'get',
            'default': '',
            'sanitizer': lambda x: x.strip().lower() if x else '',
            'result_key': 'username',
            'custom_logic': lambda x: x if len(x) >= 3 else ''
        }
    }

    # JSON data processing
    {
        'settings': {
            'source': 'json',
            'method': 'get',
            'default': {},
            'sanitizer': lambda x: x if isinstance(x, dict) else {},
            'result_key': 'user_settings'
        }
    }

    # File upload handling
    {
        'avatar': {
            'source': 'files',
            'method': 'get',
            'default': None,
            'sanitizer': lambda f: f if f and f.filename and f.filename.endswith(('.jpg', '.png')) else None,
            'result_key': 'avatar_file'
        }
    }

    # Complex validation with business logic
    {
        'age': {
            'source': 'form',
            'method': 'get',
            'default': 0,
            'sanitizer': lambda x: int(x) if x and x.isdigit() else 0,
            'result_key': 'user_age',
            'custom_logic': lambda age: age if 18 <= age <= 120 else 0
        }
    }

Usage Examples:

    from decorators.sanitizer import create_sanitizer_decorator

    # Define sanitization rules
    search_config = {
        'q': {
            'source': 'args',
            'method': 'get',
            'default': '',
            'sanitizer': lambda x: sanitize_element(x, limit=(0, 500)),
            'result_key': 'search_query'
        },
        'filters': {
            'source': 'args',
            'method': 'getlist',
            'default': [],
            'sanitizer': lambda items: [item.strip() for item in items if item.strip()],
            'result_key': 'active_filters'
        }
    }

    # Create and apply decorator
    sanitize_search = create_sanitizer_decorator(search_config)

    @app.route('/search')
    @sanitize_search
    def search():
        # These now return sanitized values automatically
        query = request.args.get('q')           # Returns sanitized search_query
        filters = request.args.getlist('filters') # Returns sanitized active_filters

        # Or access via flask.g
        sanitized_data = g.sanitized_params
        query = sanitized_data['search_query']
        filters = sanitized_data['active_filters']

        return render_template('search.html', query=query, filters=filters)

How It Works:
1. Decorator extracts parameters from specified sources using configured methods
2. Applies sanitization functions to clean/validate raw values
3. Stores sanitized parameters in flask.g.sanitized_params
4. Monkey-patches Flask request methods to return sanitized values automatically
5. Restores original request methods after route execution
6. Handles errors gracefully by falling back to default values

Error Handling:
- Parameter extraction errors fall back to default values
- Sanitization errors are logged and default values are used
- Invalid source/method configurations raise ValueError
- All errors are non-fatal to prevent route crashes

Flask Parameter Sources Reference:
    request.args   - GET parameters (query string)
    request.form   - Form data (application/x-www-form-urlencoded or multipart/form-data)
    request.json   - JSON data (application/json)
    request.files  - File uploads
    request.values - Combined args + form data

"""

import functools
from typing import Dict, Any, Callable
from flask import request, g


def create_sanitizer_decorator(config: Dict[str, Dict[str, Any]]) -> Callable:
    """
    Create a parameter sanitization decorator based on configuration.

    Args:
        config: Dictionary defining sanitization rules for each parameter.
                Each key is the parameter name, value is a dict with:
                - 'source': 'args', 'form', 'json', 'files', 'values' - where to extract from
                - 'method': 'get' or 'getlist' - how to extract the value
                - 'default': default value if parameter is missing
                - 'sanitizer': function to sanitize the raw value
                - 'result_key': key name in the sanitized results dict
                - 'custom_logic': optional function for complex validation (receives sanitized value)

    Returns:
        Decorator function that sanitizes parameters according to config

    Example config:
        {
            'q': {
                'source': 'args',  # GET parameters
                'method': 'get',
                'default': '',
                'sanitizer': lambda x: sanitize_element(x, limit=(0, 500)),
                'result_key': 'query'
            },
            'username': {
                'source': 'form',  # POST form data
                'method': 'get',
                'default': '',
                'sanitizer': lambda x: x.strip().lower(),
                'result_key': 'username'
            },
            'data': {
                'source': 'json',  # JSON POST body
                'method': 'get',
                'default': {},
                'sanitizer': lambda x: x if isinstance(x, dict) else {},
                'result_key': 'data'
            },
            'upload': {
                'source': 'files',  # File uploads
                'method': 'get',
                'default': None,
                'sanitizer': lambda x: x if x and x.filename else None,
                'result_key': 'upload_file'
            }
        }
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Create sanitized parameters dictionary
            sanitized = {}
            param_mapping = {}

            # Process each parameter according to config
            for param_name, param_config in config.items():
                source = param_config.get('source', 'args')
                method = param_config.get('method', 'get')
                default = param_config.get('default', None)
                sanitizer = param_config.get('sanitizer', lambda x: x)
                result_key = param_config.get('result_key', param_name)
                custom_logic = param_config.get('custom_logic', None)

                # Extract raw value from appropriate source
                raw_value = default

                try:
                    if source == 'args':
                        # GET parameters from URL
                        if method == 'get':
                            raw_value = request.args.get(param_name, default)
                        elif method == 'getlist':
                            raw_value = request.args.getlist(param_name)
                            if not raw_value and default is not None:
                                raw_value = default

                    elif source == 'form':
                        # POST form data (application/x-www-form-urlencoded or multipart/form-data)
                        if method == 'get':
                            raw_value = request.form.get(param_name, default)
                        elif method == 'getlist':
                            raw_value = request.form.getlist(param_name)
                            if not raw_value and default is not None:
                                raw_value = default

                    elif source == 'json':
                        # JSON POST body
                        json_data = request.get_json(silent=True) or {}
                        if method == 'get':
                            raw_value = json_data.get(param_name, default)
                        elif method == 'getlist':
                            value = json_data.get(param_name, default)
                            raw_value = value if isinstance(value, list) else [value] if value is not None else (default or [])

                    elif source == 'files':
                        # File uploads
                        if method == 'get':
                            raw_value = request.files.get(param_name, default)
                        elif method == 'getlist':
                            raw_value = request.files.getlist(param_name)
                            if not raw_value and default is not None:
                                raw_value = default

                    elif source == 'values':
                        # Combined args + form (Flask's request.values)
                        if method == 'get':
                            raw_value = request.values.get(param_name, default)
                        elif method == 'getlist':
                            raw_value = request.values.getlist(param_name)
                            if not raw_value and default is not None:
                                raw_value = default

                    else:
                        raise ValueError(f"Invalid source '{source}' for parameter '{param_name}'")

                except Exception as e:
                    print(f"Error extracting parameter '{param_name}' from '{source}': {e}")
                    raw_value = default

                # Apply sanitization
                try:
                    sanitized_value = sanitizer(raw_value)

                    # Apply custom logic if provided
                    if custom_logic:
                        sanitized_value = custom_logic(sanitized_value)

                    sanitized[result_key] = sanitized_value
                    param_mapping[param_name] = result_key

                except Exception as e:
                    # Log sanitization error and use default
                    print(f"Sanitization error for parameter '{param_name}': {e}")
                    sanitized[result_key] = default
                    param_mapping[param_name] = result_key

            # Store sanitized parameters in flask.g
            g.sanitized_params = sanitized

            # Monkey patch request methods for all sources
            original_args_get = request.args.get
            original_args_getlist = request.args.getlist
            original_form_get = request.form.get
            original_form_getlist = request.form.getlist
            original_files_get = request.files.get
            original_files_getlist = request.files.getlist
            original_values_get = request.values.get
            original_values_getlist = request.values.getlist

            def create_sanitized_get(source_name):
                def sanitized_get(key, default=None, **kwargs):
                    result_key = param_mapping.get(key, key)
                    if result_key in g.sanitized_params:
                        return g.sanitized_params[result_key]

                    # Fallback to original method based on source
                    if source_name == 'args':
                        return original_args_get(key, default, **kwargs)
                    elif source_name == 'form':
                        return original_form_get(key, default, **kwargs)
                    elif source_name == 'files':
                        return original_files_get(key, default, **kwargs)
                    elif source_name == 'values':
                        return original_values_get(key, default, **kwargs)
                    return default
                return sanitized_get

            def create_sanitized_getlist(source_name):
                def sanitized_getlist(key, **kwargs):
                    result_key = param_mapping.get(key, key)
                    if result_key in g.sanitized_params:
                        value = g.sanitized_params[result_key]
                        return value if isinstance(value, list) else [value] if value is not None else []

                    # Fallback to original method based on source
                    if source_name == 'args':
                        return original_args_getlist(key, **kwargs)
                    elif source_name == 'form':
                        return original_form_getlist(key, **kwargs)
                    elif source_name == 'files':
                        return original_files_getlist(key, **kwargs)
                    elif source_name == 'values':
                        return original_values_getlist(key, **kwargs)
                    return []
                return sanitized_getlist

            # Apply monkey patches
            request.args.get = create_sanitized_get('args')
            request.args.getlist = create_sanitized_getlist('args')
            request.form.get = create_sanitized_get('form')
            request.form.getlist = create_sanitized_getlist('form')
            request.files.get = create_sanitized_get('files')
            request.files.getlist = create_sanitized_getlist('files')
            request.values.get = create_sanitized_get('values')
            request.values.getlist = create_sanitized_getlist('values')

            try:
                return f(*args, **kwargs)
            finally:
                # Restore original methods
                request.args.get = original_args_get
                request.args.getlist = original_args_getlist
                request.form.get = original_form_get
                request.form.getlist = original_form_getlist
                request.files.get = original_files_get
                request.files.getlist = original_files_getlist
                request.values.get = original_values_get
                request.values.getlist = original_values_getlist

        return decorated_function
    return decorator


def sanitize_params(config: Dict[str, Dict[str, Any]]) -> Callable:
    """
    Direct parameter sanitization decorator that accepts configuration as an argument.

    This is a convenience wrapper around create_sanitizer_decorator() that allows
    passing the sanitization configuration directly to the decorator, enabling
    cleaner syntax: @sanitize_params(config) instead of first creating the decorator.

    Args:
        config: Dictionary defining sanitization rules for each parameter.
                Same format as create_sanitizer_decorator().

    Returns:
        Decorator function that sanitizes parameters according to config.

    Usage:
        @sanitize_params({
            'param_name': {
                'source': 'args',
                'method': 'get',
                'default': '',
                'sanitizer': lambda x: x.strip()
            }
        })
        def my_route():
            pass
    """
    return create_sanitizer_decorator(config)