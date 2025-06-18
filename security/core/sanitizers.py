"""
Unified input sanitization with configurable security levels
"""
import unicodedata
from typing import Dict, List, Union
from enum import Enum
import bleach

from security.core.patterns import security_patterns

class SecurityLevel(Enum):
    """Security levels for sanitization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"

class SanitizationConfig:
    """Configuration for sanitization behavior"""

    def __init__(
        self,
        max_length: int = 200,
        allow_html: bool = False,
        allowed_tags: List[str] = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        preserve_case: bool = False,
        normalize_unicode: bool = True,
        remove_control_chars: bool = True,
        strip_whitespace: bool = True
    ):
        self.max_length = max_length
        self.allow_html = allow_html
        self.allowed_tags = allowed_tags or ['b', 'i', 'em', 'strong']
        self.security_level = security_level
        self.preserve_case = preserve_case
        self.normalize_unicode = normalize_unicode
        self.remove_control_chars = remove_control_chars
        self.strip_whitespace = strip_whitespace

    @classmethod
    def for_search_query(cls) -> 'SanitizationConfig':
        """Configuration optimized for search queries"""
        return cls(
            max_length=1000,
            allow_html=False,
            security_level=SecurityLevel.HIGH,
            preserve_case=True,
            strip_whitespace=True
        )

    @classmethod
    def for_user_input(cls) -> 'SanitizationConfig':
        """Configuration for general user input"""
        return cls(
            max_length=500,
            allow_html=False,
            security_level=SecurityLevel.MEDIUM,
            strip_whitespace=True
        )

    @classmethod
    def for_html_content(cls) -> 'SanitizationConfig':
        """Configuration for HTML content"""
        return cls(
            max_length=5000,
            allow_html=True,
            allowed_tags=['b', 'i', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li'],
            security_level=SecurityLevel.HIGH,
            strip_whitespace=False
        )

    @classmethod
    def for_opensearch_query(cls) -> 'SanitizationConfig':
        """Configuration for OpenSearch queries"""
        return cls(
            max_length=2000,
            allow_html=False,
            security_level=SecurityLevel.STRICT,
            preserve_case=True
        )

class UnifiedSanitizer:
    """Unified sanitizer with configurable security levels and optimized performance"""

    def __init__(self):
        self.patterns = security_patterns

        # Define dangerous characters by security level
        self._dangerous_chars = {
            SecurityLevel.LOW: ['<', '>', '"', "'"],
            SecurityLevel.MEDIUM: ['<', '>', '"', "'", '`', ';', '(', ')', '{', '}'],
            SecurityLevel.HIGH: ['<', '>', '"', "'", '`', '\\', ';', '(', ')', '{', '}', '[', ']', '$', '|'],
            SecurityLevel.STRICT: ['<', '>', '"', "'", '`', '\\', ';', '(', ')', '{', '}', '[', ']', '$', '|', '&', '*', '?', '!', '^', '%', '#', '@']
        }

    def sanitize(
        self,
        input_data: Union[str, Dict, List],
        config: SanitizationConfig = None
    ) -> Union[str, Dict, List]:
        """
        Main sanitization method that handles strings, dicts, and lists
        """
        if config is None:
            config = SanitizationConfig()

        if isinstance(input_data, str):
            return self._sanitize_string(input_data, config)
        elif isinstance(input_data, dict):
            return self._sanitize_dict(input_data, config)
        elif isinstance(input_data, list):
            return self._sanitize_list(input_data, config)
        else:
            return input_data

    def _sanitize_string(self, text: str, config: SanitizationConfig) -> str:
        """Sanitize a single string with comprehensive security checks"""
        if not text or not isinstance(text, str):
            return ""

        # Step 1: Remove null bytes and control characters
        if config.remove_control_chars:
            text = text.replace('\x00', '')
            text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')

        # Step 2: Unicode normalization
        if config.normalize_unicode:
            text = unicodedata.normalize('NFKC', text)

        # Step 3: Length limiting (early to prevent processing huge strings)
        if len(text) > config.max_length:
            text = text[:config.max_length]

        # Step 4: Security pattern detection and removal
        if config.security_level in [SecurityLevel.HIGH, SecurityLevel.STRICT]:
            if self.patterns.is_dangerous_string(text):
                text = self._remove_dangerous_patterns(text, config.security_level)

        # Step 5: HTML handling
        if config.allow_html:
            text = bleach.clean(
                text,
                tags=config.allowed_tags,
                attributes={},
                strip=True
            )
        else:
            # Remove all HTML/XML tags
            text = self.patterns.get_pattern('html_tags').sub('', text)

        # Step 6: Remove dangerous characters
        dangerous_chars = self._dangerous_chars[config.security_level]
        for char in dangerous_chars:
            text = text.replace(char, '')

        # Step 7: Case handling
        if not config.preserve_case:
            text = text.lower()

        # Step 8: Whitespace handling
        if config.strip_whitespace:
            text = text.strip()
            # Normalize internal whitespace
            text = ' '.join(text.split())

        return text

    def _sanitize_dict(self, data: Dict, config: SanitizationConfig) -> Dict:
        """Sanitize dictionary recursively"""
        sanitized = {}

        for key, value in data.items():
            # Sanitize key
            if isinstance(key, str):
                clean_key = self._sanitize_string(key, config)
                if not clean_key:  # Skip empty keys
                    continue
            else:
                clean_key = key

            # Sanitize value
            clean_value = self.sanitize(value, config)
            sanitized[clean_key] = clean_value

        return sanitized

    def _sanitize_list(self, data: List, config: SanitizationConfig) -> List:
        """Sanitize list recursively"""
        return [self.sanitize(item, config) for item in data]

    def _remove_dangerous_patterns(self, text: str, security_level: SecurityLevel) -> str:
        """Remove dangerous patterns based on security level"""

        # Basic dangerous patterns (all levels)
        pattern_groups = ['dangerous_strings']

        if security_level in [SecurityLevel.MEDIUM, SecurityLevel.HIGH, SecurityLevel.STRICT]:
            pattern_groups.extend(['sql_injection', 'command_injection'])

        if security_level in [SecurityLevel.HIGH, SecurityLevel.STRICT]:
            pattern_groups.extend([
                'nosql_injection', 'path_traversal', 'ldap_injection',
                'xxe_injection', 'template_injection'
            ])

        if security_level == SecurityLevel.STRICT:
            pattern_groups.extend(['opensearch_injection', 'json_injection'])

        # Remove matches for each pattern group
        for group in pattern_groups:
            patterns = self.patterns._patterns.get(group, [])
            if isinstance(patterns, list):
                for pattern in patterns:
                    text = pattern.sub('', text)

        return text

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file operations"""
        return self.patterns.sanitize_filename(filename)

    def sanitize_search_query(self, query: str) -> str:
        """Sanitize search query with search-specific rules"""
        config = SanitizationConfig.for_search_query()
        return self._sanitize_string(query, config)

    def sanitize_opensearch_query(self, query_dict: Dict) -> Dict:
        """Sanitize OpenSearch query with strict security"""
        config = SanitizationConfig.for_opensearch_query()
        return self._sanitize_opensearch_dict(query_dict, config)

    def _sanitize_opensearch_dict(self, query_dict: Dict, config: SanitizationConfig) -> Dict:
        """Specialized sanitization for OpenSearch queries"""
        if not isinstance(query_dict, dict):
            return {}

        sanitized = {}

        # List of safe OpenSearch query keys
        safe_query_keys = {
            'query', 'bool', 'must', 'must_not', 'should', 'filter',
            'match', 'match_all', 'multi_match', 'term', 'terms', 'range',
            'exists', 'prefix', 'wildcard', 'regexp', 'fuzzy',
            'ids', 'constant_score', 'dis_max', 'function_score',
            'boosting', 'nested', 'has_child', 'has_parent',
            'from', 'size', 'sort', '_source', 'highlight', 'aggs', 'aggregations'
        }

        # Safe aggregation types
        safe_agg_types = {
            'terms', 'date_histogram', 'histogram', 'range', 'date_range',
            'sum', 'avg', 'min', 'max', 'count', 'cardinality', 'value_count',
            'percentiles', 'percentile_ranks', 'stats', 'extended_stats',
            'geo_distance', 'geo_hash_grid', 'nested', 'reverse_nested',
            'children', 'sampler', 'diversified_sampler', 'global',
            'filter', 'filters', 'missing', 'significant_terms',
            'top_hits', 'composite'
        }

        for key, value in query_dict.items():
            # Sanitize and validate keys
            clean_key = self._sanitize_opensearch_field_name(key)
            if not clean_key:
                continue

            # Skip if key is not in safe list (for top-level keys)
            if key in safe_query_keys or key in safe_agg_types or '.' in key:
                if isinstance(value, str):
                    clean_value = self._sanitize_opensearch_value(value)
                elif isinstance(value, dict):
                    clean_value = self._sanitize_opensearch_dict(value, config)
                elif isinstance(value, list):
                    clean_value = self._sanitize_opensearch_list(value, config)
                elif isinstance(value, (int, float, bool)) or value is None:
                    clean_value = value
                else:
                    continue  # Skip unknown types

                sanitized[clean_key] = clean_value

        return sanitized

    def _sanitize_opensearch_list(self, value_list: List, config: SanitizationConfig) -> List:
        """Sanitize lists in OpenSearch queries"""
        sanitized_list = []

        for item in value_list:
            if isinstance(item, str):
                clean_item = self._sanitize_opensearch_value(item)
                if clean_item:  # Only add non-empty strings
                    sanitized_list.append(clean_item)
            elif isinstance(item, dict):
                clean_item = self._sanitize_opensearch_dict(item, config)
                if clean_item:  # Only add non-empty dicts
                    sanitized_list.append(clean_item)
            elif isinstance(item, (int, float, bool)) or item is None:
                sanitized_list.append(item)

        return sanitized_list

    def _sanitize_opensearch_field_name(self, field_name: str) -> str:
        """Sanitize OpenSearch field names"""
        if not isinstance(field_name, str):
            return ""

        # Allow only alphanumeric, dots, underscores, hyphens, and asterisks (for wildcards)
        if not self.patterns.validate_field_name(field_name.replace('*', '')):
            return ""

        # Prevent access to dangerous system fields
        dangerous_fields = {
            '_script', '_inline', '_file', '_lang', '_params', '_source_includes',
            '_source_excludes', '_routing', '_parent', '_timestamp', '_ttl'
        }

        if field_name in dangerous_fields:
            return ""

        # Allow common system fields that are safe
        safe_system_fields = {
            '_id', '_type', '_index', '_score', '_source', '_all', '_uid',
            '_version', '_routing', '_parent', '_timestamp', '_ttl'
        }

        if field_name.startswith('_') and field_name not in safe_system_fields:
            return ""

        return field_name

    def _sanitize_opensearch_value(self, value: str) -> str:
        """Sanitize OpenSearch query values"""
        if not isinstance(value, str):
            return ""

        # Remove script-related content and dangerous patterns
        dangerous_patterns = [
            r'script\s*:', r'inline\s*:', r'source\s*:', r'file\s*:',
            r'params\s*:', r'lang\s*:', r'painless', r'groovy',
            r'expression', r'mustache', r'_delete', r'_update',
            r'_bulk', r'_reindex', r'_update_by_query', r'_delete_by_query'
        ]

        clean_value = value
        for pattern in dangerous_patterns:
            clean_value = self.patterns.get_pattern('opensearch_injection')[0].sub('', clean_value)

        # Use string sanitization with strict config
        strict_config = SanitizationConfig(
            max_length=1000,
            security_level=SecurityLevel.STRICT,
            preserve_case=True
        )

        return self._sanitize_string(clean_value, strict_config)

    def sanitize_aggregation_query(self, agg_dict: Dict) -> Dict:
        """Sanitize OpenSearch aggregation queries with enhanced security"""
        if not isinstance(agg_dict, dict):
            return {}

        # Safe aggregation types (whitelist approach)
        safe_agg_types = {
            'terms', 'date_histogram', 'histogram', 'range', 'date_range',
            'sum', 'avg', 'min', 'max', 'count', 'cardinality', 'value_count',
            'percentiles', 'percentile_ranks', 'stats', 'extended_stats',
            'geo_distance', 'geo_hash_grid', 'nested', 'reverse_nested',
            'children', 'sampler', 'diversified_sampler', 'global',
            'filter', 'filters', 'missing', 'significant_terms', 'top_hits'
        }

        sanitized = {}

        for key, value in agg_dict.items():
            clean_key = self._sanitize_string(key, SanitizationConfig.for_opensearch_query())
            if not clean_key:
                continue

            if isinstance(value, dict):
                # Check if this is an aggregation definition
                agg_type = None
                for agg in safe_agg_types:
                    if agg in value:
                        agg_type = agg
                        break

                if agg_type:
                    # Sanitize the aggregation configuration
                    clean_agg_config = self._sanitize_opensearch_dict(value[agg_type],
                                                                    SanitizationConfig.for_opensearch_query())
                    sanitized[clean_key] = {agg_type: clean_agg_config}

                    # Handle sub-aggregations recursively
                    if 'aggs' in value:
                        sub_aggs = self.sanitize_aggregation_query(value['aggs'])
                        if sub_aggs:
                            sanitized[clean_key]['aggs'] = sub_aggs
                    elif 'aggregations' in value:
                        sub_aggs = self.sanitize_aggregation_query(value['aggregations'])
                        if sub_aggs:
                            sanitized[clean_key]['aggregations'] = sub_aggs

        return sanitized

    def validate_and_sanitize_filters(self, filters: Union[List, Dict],
                                    allowed_values: Dict[str, List] = None,
                                    max_items: int = 50) -> Union[List, Dict]:
        """Validate and sanitize filter values with whitelist support"""
        if isinstance(filters, list):
            return self._sanitize_filter_list(filters, allowed_values, max_items)
        elif isinstance(filters, dict):
            return self._sanitize_filter_dict(filters, allowed_values, max_items)
        else:
            return []

    def _sanitize_filter_list(self, filters: List, allowed_values: Dict[str, List], max_items: int, filter_key: str = None) -> List:
        """Sanitize list of filter values"""
        if not filters or len(filters) > max_items:
            filters = filters[:max_items] if filters else []

        sanitized = []
        for value in filters:
            if isinstance(value, str):
                clean_value = self._sanitize_string(value, SanitizationConfig.for_user_input())
                if clean_value and len(clean_value) >= 2:  # Minimum length check
                    if self._is_safe_filter_value(clean_value):
                        # Check against whitelist if provided and filter_key is specified
                        if not allowed_values or not filter_key or filter_key not in allowed_values or clean_value in allowed_values[filter_key]:
                            sanitized.append(clean_value)
            elif isinstance(value, (int, float)):
                # For numeric values, check against whitelist if provided and filter_key is specified
                if not allowed_values or not filter_key or filter_key not in allowed_values or value in allowed_values[filter_key]:
                    sanitized.append(value)

        return sanitized

    def _sanitize_filter_dict(self, filters: Dict, allowed_values: Dict[str, List], max_items: int) -> Dict:
        """Sanitize dictionary of filter values"""
        sanitized = {}

        for key, values in filters.items():
            clean_key = self._sanitize_string(key, SanitizationConfig.for_user_input())
            if not clean_key:
                continue

            if isinstance(values, list):
                clean_values = self._sanitize_filter_list(values, allowed_values, max_items, clean_key)
                if clean_values:
                    sanitized[clean_key] = clean_values
            elif isinstance(values, str):
                clean_value = self._sanitize_string(values, SanitizationConfig.for_user_input())
                if clean_value and self._is_safe_filter_value(clean_value):
                    # Check against whitelist if provided
                    if not allowed_values or clean_key not in allowed_values or clean_value in allowed_values[clean_key]:
                        sanitized[clean_key] = clean_value

        return sanitized

    def _is_safe_filter_value(self, value: str) -> bool:
        """Enhanced safety check for filter values"""
        if not value or len(value) < 2 or len(value) > 100:
            return False

        # Check for dangerous patterns
        if self.patterns.is_dangerous_string(value):
            return False

        # Check for excessive special characters
        special_char_count = self.patterns.count_special_chars(value)
        if special_char_count > len(value) * 0.3:  # More than 30% special chars
            return False

        return True

# Global instance for efficient reuse
unified_sanitizer = UnifiedSanitizer()

# Convenience functions for backward compatibility
def sanitize_input(input_str: str, max_length: int = 200, allow_basic_html: bool = False) -> str:
    """Backward compatible sanitization function"""
    config = SanitizationConfig(
        max_length=max_length,
        allow_html=allow_basic_html,
        security_level=SecurityLevel.MEDIUM
    )
    return unified_sanitizer.sanitize(input_str, config)

def sanitize_search_query(query: str) -> str:
    """Sanitize search query with optimized settings"""
    return unified_sanitizer.sanitize_search_query(query)

def sanitize_opensearch_query(query_dict: Dict) -> Dict:
    """Sanitize OpenSearch query dictionary"""
    return unified_sanitizer.sanitize_opensearch_query(query_dict)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe operations"""
    return unified_sanitizer.sanitize_filename(filename)
