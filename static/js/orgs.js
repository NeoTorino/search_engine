// Global variables
let organizationsData = [];
let currentSort = { column: null, direction: 'asc' };

// Load all data when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Setup search functionality for the header search input
    const headerSearchInput = document.querySelector('#org-search-container #searchOrgs');
    if (headerSearchInput) {
        headerSearchInput.addEventListener('input', filterOrganizations);
    }

    // Also setup for the table search input (if it exists) as fallback
    const tableSearchInput = document.querySelector('.stats-container #searchOrgs');
    if (tableSearchInput) {
        tableSearchInput.addEventListener('input', filterOrganizations);
    }

    // Setup sorting functionality
    setupSortingHeaders();
});

// Setup sorting headers
function setupSortingHeaders() {
    const headers = document.querySelectorAll('#orgsTable thead th');

    // Make headers clickable and add sort indicators
    headers[0].innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <div id="sort-header-name" style="display: flex; align-items: center; cursor: pointer;">
                <span>Organization</span>
                <span id="sort-name" class="sort-indicator">⇅</span>
            </div>
        </div>
    `;

    headers[1].innerHTML = `
        <div id="sort-header-jobs" style="cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.25rem;">
            <span>Total Jobs</span>
            <span id="sort-jobs" class="sort-indicator">⇅</span>
        </div>
    `;

    headers[2].innerHTML = `
        <div id="sort-header-date" style="cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.25rem;">
            <span>Last Updated</span>
            <span id="sort-date" class="sort-indicator">⇅</span>
        </div>
    `;

    // New headers for the action columns (non-sortable)
    headers[3].innerHTML = `<span>Careers Page</span>`;
    headers[4].innerHTML = `<span>View Jobs</span>`;

    // Add event listeners for sorting
    document.getElementById('sort-header-name').addEventListener('click', () => sortTable('name'));
    document.getElementById('sort-header-jobs').addEventListener('click', () => sortTable('jobs'));
    document.getElementById('sort-header-date').addEventListener('click', () => sortTable('date'));

    // Re-attach search event listener for header input
    const headerSearchInput = document.querySelector('#org-search-container #searchOrgs');
    if (headerSearchInput) {
        headerSearchInput.addEventListener('input', filterOrganizations);
    }
}

// Sort table function
function sortTable(column) {
    // Toggle direction if same column, otherwise start with ascending
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }

    // Update sort indicators
    updateSortIndicators();

    // Get current filtered data
    const searchTerm = document.getElementById('searchOrgs').value.toLowerCase();
    let dataToSort = organizationsData.filter(org =>
        org.name.toLowerCase().includes(searchTerm) ||
        (org.country && org.country.toLowerCase().includes(searchTerm))
    );

    // Sort the data
    dataToSort.sort((a, b) => {
        let valueA, valueB;

        switch (column) {
            case 'name':
                valueA = a.name.toLowerCase();
                valueB = b.name.toLowerCase();
                break;
            case 'jobs':
                valueA = a.job_count || 0;
                valueB = b.job_count || 0;
                break;
            case 'date':
                valueA = new Date(a.last_updated || 0);
                valueB = new Date(b.last_updated || 0);
                break;
        }

        if (valueA < valueB) {
            return currentSort.direction === 'asc' ? -1 : 1;
        }
        if (valueA > valueB) {
            return currentSort.direction === 'asc' ? 1 : -1;
        }
        return 0;
    });

    // Render the sorted data
    renderOrganizationsTable(dataToSort);
}

// Update sort indicators
function updateSortIndicators() {
    // Reset all indicators
    const indicators = document.querySelectorAll('.sort-indicator');
    indicators.forEach(indicator => {
        indicator.textContent = '⇅';
        indicator.style.opacity = '0.5';
    });

    // Set active indicator
    if (currentSort.column) {
        const activeIndicator = document.getElementById(`sort-${currentSort.column}`);
        if (activeIndicator) {
            activeIndicator.textContent = currentSort.direction === 'asc' ? '↑' : '↓';
            activeIndicator.style.opacity = '1';
        }
    }
}

// Function to navigate to search with organization filter
function viewJobsByOrganization(organizationName) {
    // Get current search query
    const currentQuery = new URLSearchParams(window.location.search).get('q') || '';

    // Build the new URL with the organization filter
    const params = new URLSearchParams();

    // Keep the current search query if it exists
    if (currentQuery) {
        params.set('q', currentQuery);
    }

    // Add the organization filter
    params.set('organization', organizationName);

    // Navigate to search page with filters and switch to results tab
    const newUrl = `/search?${params.toString()}`;
    window.location.href = newUrl;
}

// Setup event delegation for view jobs buttons
function setupViewJobsButtons() {
    const tbody = document.getElementById('orgsTableBody');

    // Remove existing event listener to prevent duplicates
    tbody.removeEventListener('click', handleViewJobsClick);

    // Add event listener using event delegation
    tbody.addEventListener('click', handleViewJobsClick);
}

// Handle click events on view jobs buttons
function handleViewJobsClick(event) {
    if (event.target.matches('.view-jobs-btn') || event.target.closest('.view-jobs-btn')) {
        const button = event.target.matches('.view-jobs-btn') ? event.target : event.target.closest('.view-jobs-btn');
        const organizationName = button.getAttribute('data-organization');
        if (organizationName) {
            viewJobsByOrganization(organizationName);
        }
    }
}

// Load organizations table
async function loadOrganizations(searchParams = '') {
    try {
        const url = searchParams ? `/organizations?${searchParams}` : '/organizations';
        const response = await fetch(url);
        const data = await response.json();

        organizationsData = data.organizations;
        renderOrganizationsTable(organizationsData);

        // Setup event listeners for view jobs buttons after rendering
        setupViewJobsButtons();
    } catch (error) {
        console.error('Error loading organizations:', error);
        document.getElementById('orgsTableBody').innerHTML =
            '<tr><td colspan="5" class="text-center"><div class="error-message">Error loading organizations</div></td></tr>';
    }
}

// Render organizations table
function renderOrganizationsTable(organizations) {
    const tbody = document.getElementById('orgsTableBody');

    if (organizations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No organizations found</td></tr>';
        return;
    }

    tbody.innerHTML = organizations
        .filter(org => org.name && org.last_updated) // Skip rows with missing name or last_updated
        .map(org => {
            const careersUrl = org.url_careers || '#';
            const name = org.name;
            const jobCount = org.job_count || 0;
            const lastUpdated = formatDate(org.last_updated);

            // Create careers page link
            const careersLink = careersUrl !== '#'
                ? `<a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-outline-primary btn-sm">
                     <i class="fas fa-external-link-alt me-1"></i>Visit Careers
                   </a>`
                : '<span class="text-muted">N/A</span>';

            // Create view jobs button with data attribute instead of onclick
            const viewJobsButton = `<button type="button" class="btn btn-outline-success btn-sm view-jobs-btn" data-organization="${name.replace(/"/g, '&quot;')}">
                                      <i class="fas fa-search me-1"></i>View Jobs
                                    </button>`;

            return `
                <tr>
                    <td><strong>${name}</strong></td>
                    <td class="text-center"><span class="job-count-badge">${jobCount}</span></td>
                    <td class="text-center">${lastUpdated}</td>
                    <td class="text-center">${careersLink}</td>
                    <td class="text-center">${viewJobsButton}</td>
                </tr>
            `;
        }).join('');

    // Setup event listeners after rendering
    setupViewJobsButtons();
}

function filterOrganizations() {
    // Get search term from header input first, then fallback to table input
    const headerSearchInput = document.querySelector('#org-search-container #searchOrgs');
    const tableSearchInput = document.querySelector('.stats-container #searchOrgs');

    let searchTerm = '';
    if (headerSearchInput) {
        searchTerm = headerSearchInput.value.toLowerCase();
    } else if (tableSearchInput) {
        searchTerm = tableSearchInput.value.toLowerCase();
    }

    let filtered = organizationsData.filter(org =>
        org.name.toLowerCase().includes(searchTerm) ||
        (org.country && org.country.toLowerCase().includes(searchTerm))
    );

    // Apply current sort to filtered results
    if (currentSort.column) {
        filtered.sort((a, b) => {
            let valueA, valueB;

            switch (currentSort.column) {
                case 'name':
                    valueA = a.name.toLowerCase();
                    valueB = b.name.toLowerCase();
                    break;
                case 'jobs':
                    valueA = a.job_count || 0;
                    valueB = b.job_count || 0;
                    break;
                case 'date':
                    valueA = new Date(a.last_updated || 0);
                    valueB = new Date(b.last_updated || 0);
                    break;
            }

            if (valueA < valueB) {
                return currentSort.direction === 'asc' ? -1 : 1;
            }
            if (valueA > valueB) {
                return currentSort.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }

    renderOrganizationsTable(filtered);
}

// Utility functions.
// Output format is: Jun 12, 2025
function formatDateLocale(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);

    // Check if the date is valid
    if (isNaN(date.getTime())) {
        return 'Error: Invalid date';
    }

    // Round the time to the start of the day (00:00:00)
    date.setHours(0, 0, 0, 0);

    const now = new Date();
    now.setHours(0, 0, 0, 0); // Also round the current date to the start of the day

    // Calculate the difference in time
    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)); // Convert time difference to days

    if (diffDays < 0) return 'Error: Future date';
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 30) return `${diffDays} days ago`;
    return '30+ days ago';
}
