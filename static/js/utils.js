// utils.js - Utility functions for security, validation, and common operations

/**
 * Sanitizes user input to prevent XSS and other security issues
 * @param {string} input - The input string to sanitize
 * @param {number} maxLength - Maximum allowed length (default: 200)
 * @param {boolean} allowSpecialChars - Whether to allow special characters (default: false)
 * @returns {string} - Sanitized input string
 */
function sanitizeInput(input, maxLength = 200, allowSpecialChars = false) {
  if (!input || typeof input !== 'string') {
      return '';
  }

  // Remove null bytes and control characters
  input = input.replace(/\x00/g, '');
  input = input.replace(/[\x00-\x1F\x7F-\x9F]/g, '');

  // Length limiting
  input = input.substring(0, maxLength);

  // Remove HTML tags
  input = input.replace(/<[^>]*>/g, '');

  // Remove dangerous characters
  if (!allowSpecialChars) {
      input = input.replace(/[<>"'`\\;(){}[\]]/g, '');
  }

  // Remove script-related content
  const scriptPatterns = [
      /javascript:/gi,
      /vbscript:/gi,
      /data:/gi,
      /on\w+\s*=/gi,
      /script/gi,
      /iframe/gi,
      /object/gi,
      /embed/gi
  ];

  scriptPatterns.forEach(pattern => {
      input = input.replace(pattern, '');
  });

  // Check for suspicious patterns
  const suspiciousPatterns = [
      /union\s+select/gi,
      /drop\s+table/gi,
      /delete\s+from/gi,
      /insert\s+into/gi,
      /exec\s*\(/gi
  ];

  suspiciousPatterns.forEach(pattern => {
      input = input.replace(pattern, '');
  });

  // Normalize whitespace
  input = input.replace(/\s+/g, ' ').trim();

  return input;
}

/**
 * Gets CSRF token from meta tag
 * @returns {string|null} - CSRF token or null if not found
 */
function getCSRFToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}

/**
 * Enhanced fetch with security headers
 * @param {string} url - URL to fetch
 * @param {object} options - Fetch options
 * @returns {Promise} - Fetch promise
 */
function fetchWithSecurity(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['X-Requested-With'] = 'XMLHttpRequest';

    const csrfToken = getCSRFToken();
    if (csrfToken) {
        options.headers['X-CSRF-Token'] = csrfToken;
    }

    return fetch(url, options);
}

/**
 * Helper function to get current search parameters
 * @returns {string} - URL encoded search parameters
 */
function getCurrentSearchParams() {
  const form = document.getElementById('search-form');
  if (!form) return '';

  const formData = new FormData(form);
  const params = new URLSearchParams();

  for (let [key, value] of formData.entries()) {
    if (value) params.append(key, value);
  }

  console.log('Current search params:', params.toString());
  return params.toString();
}

// Make functions globally available
window.sanitizeInput = sanitizeInput;
window.getCSRFToken = getCSRFToken;
window.fetchWithSecurity = fetchWithSecurity;
window.getCurrentSearchParams = getCurrentSearchParams;