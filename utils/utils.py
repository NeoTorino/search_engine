def calculate_depth(obj, max_iterations=1000):
    """
    Calculate the maximum depth of a nested list or dictionary with iteration limit.

    Args:
        obj: The object to analyze (list, dict, or any other type)
        max_iterations: Maximum number of iterations to prevent infinite recursion

    Returns:
        int: The maximum depth of nesting, or -1 if iteration limit exceeded
    """
    iteration_count = [0]  # Use list to make it mutable in nested function

    def _calculate_depth_helper(obj):
        iteration_count[0] += 1
        if iteration_count[0] > max_iterations:
            return -1

        if isinstance(obj, dict):
            if not obj:  # Empty dict has depth 1
                return 1
            depths = []
            for value in obj.values():
                depth = _calculate_depth_helper(value)
                if depth == -1:  # Limit exceeded
                    return -1
                depths.append(depth)
            return 1 + max(depths)

        elif isinstance(obj, list):
            if not obj:  # Empty list has depth 1
                return 1
            depths = []
            for item in obj:
                depth = _calculate_depth_helper(item)
                if depth == -1:  # Limit exceeded
                    return -1
                depths.append(depth)
            return 1 + max(depths)

        else:
            # Base case: not a container type
            return 0

    return _calculate_depth_helper(obj)


def is_numeric_string(s):
    """
    Enhanced check to determine if a string represents a number.

    This function is more robust than str.isdigit() as it handles:
    - Negative numbers ("-123")
    - Decimal numbers ("123.45")
    - Numbers with leading/trailing whitespace (" 123 ")
    - Edge cases like empty strings, just signs, multiple decimals

    Args:
        s: String to check

    Returns:
        bool: True if string represents a valid number, False otherwise
    """
    if not isinstance(s, str):
        return False

    # Strip whitespace
    s = s.strip()

    # Empty string is not numeric
    if not s:
        return False

    # Handle just a sign with no digits
    if s in ['+', '-', '.']:
        return False

    # Remove leading sign for checking
    check_str = s
    if s.startswith(('+', '-')):
        check_str = s[1:]

    # Must have at least one digit after removing sign
    if not check_str:
        return False

    # Count decimal points - should be 0 or 1
    decimal_count = check_str.count('.')
    if decimal_count > 1:
        return False

    # Check if remaining characters are digits and at most one decimal point
    digits_and_decimal = check_str.replace('.', '')
    if not digits_and_decimal.isdigit():
        return False

    # Additional validation: try to convert to ensure it's a valid number
    try:
        float(s)
        return True
    except (ValueError, OverflowError):
        return False
