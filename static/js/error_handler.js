/**
 * Global AJAX error handler to properly handle HTTP errors
 */
function setupGlobalErrorHandling() {
    // Handle fetch API errors
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args)
            .then(response => {
                if (!response.ok) {
                    return handleHttpError(response);
                }
                return response;
            })
            .catch(error => {
                console.error('Network error:', error);
                showErrorMessage('Network error occurred. Please check your connection and try again.');
                throw error;
            });
    };

    // Handle jQuery AJAX errors if you're using jQuery
    if (typeof $ !== 'undefined') {
        $(document).ajaxError(function(event, xhr, settings, thrownError) {
            handleAjaxError(xhr, settings, thrownError);
        });
    }
}

/**
 * Handle HTTP errors from fetch requests
 */
async function handleHttpError(response) {
    const status = response.status;

    try {
        const errorData = await response.json();

        switch (status) {
            case 429:
                handleRateLimitError(errorData);
                break;
            case 404:
                handleNotFoundError(errorData);
                break;
            case 500:
                handleServerError(errorData);
                break;
            default:
                handleGenericError(errorData, status);
        }
    } catch (e) {
        // If we can't parse JSON, redirect to error page for non-AJAX requests
        if (status === 429) {
            window.location.href = '/error/429';
        } else {
            showErrorMessage(`Error ${status}: ${response.statusText}`);
        }
    }

    throw new Error(`HTTP ${status}: ${response.statusText}`);
}

/**
 * Handle jQuery AJAX errors
 */
function handleAjaxError(xhr, settings, thrownError) {
    const status = xhr.status;

    try {
        const errorData = JSON.parse(xhr.responseText);

        switch (status) {
            case 429:
                handleRateLimitError(errorData);
                break;
            case 404:
                handleNotFoundError(errorData);
                break;
            case 500:
                handleServerError(errorData);
                break;
            default:
                handleGenericError(errorData, status);
        }
    } catch (e) {
        // If we can't parse JSON response
        if (status === 429) {
            window.location.href = '/error/429';
        } else {
            showErrorMessage(`Error ${status}: ${xhr.statusText || thrownError}`);
        }
    }
}

/**
 * Handle rate limit (429) errors
 */
function handleRateLimitError(errorData) {
    const retryAfter = errorData.retry_after || 60;

    showErrorModal({
        title: 'Too Many Requests',
        message: errorData.message || 'You have made too many requests. Please wait before trying again.',
        type: 'warning',
        showRetryButton: true,
        retryAfter: retryAfter
    });
}

/**
 * Handle not found (404) errors
 */
function handleNotFoundError(errorData) {
    showErrorMessage(errorData.message || 'The requested resource was not found.');
}

/**
 * Handle server (500) errors
 */
function handleServerError(errorData) {
    showErrorMessage(errorData.message || 'An unexpected server error occurred. Please try again later.');
}

/**
 * Handle generic errors
 */
function handleGenericError(errorData, status) {
    showErrorMessage(errorData.message || `An error occurred (${status}). Please try again.`);
}

/**
 * Show error message in a toast or alert
 */
function showErrorMessage(message) {
    // If you have a toast system, use it
    if (typeof showToast === 'function') {
        showToast(message, 'error');
        return;
    }

    // If you have Bootstrap alerts, create one
    if (typeof bootstrap !== 'undefined') {
        createBootstrapAlert(message, 'danger');
        return;
    }

    // Fallback to browser alert
    alert(message);
}

/**
 * Show error modal for more complex errors
 */
function showErrorModal(options) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${options.title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>${options.message}</p>
                    ${options.retryAfter ? `<p class="text-muted">Please wait ${options.retryAfter} seconds before trying again.</p>` : ''}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    ${options.showRetryButton ? '<button type="button" class="btn btn-primary" id="retryButton">Retry</button>' : ''}
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    // Handle retry button
    if (options.showRetryButton) {
        const retryButton = modal.querySelector('#retryButton');
        if (options.retryAfter) {
            retryButton.disabled = true;
            retryButton.textContent = `Retry (${options.retryAfter}s)`;

            const countdown = setInterval(() => {
                options.retryAfter--;
                retryButton.textContent = `Retry (${options.retryAfter}s)`;

                if (options.retryAfter <= 0) {
                    clearInterval(countdown);
                    retryButton.disabled = false;
                    retryButton.textContent = 'Retry';
                }
            }, 1000);
        }

        retryButton.addEventListener('click', () => {
            bsModal.hide();
            window.location.reload();
        });
    }

    // Clean up modal when hidden
    modal.addEventListener('hidden.bs.modal', () => {
        document.body.removeChild(modal);
    });
}

/**
 * Create Bootstrap alert
 */
function createBootstrapAlert(message, type = 'danger') {
    const alertContainer = document.querySelector('.alert-container') || document.querySelector('.container');
    if (!alertContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.insertBefore(alert, alertContainer.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Initialize error handling when DOM is loaded
document.addEventListener('DOMContentLoaded', setupGlobalErrorHandling);