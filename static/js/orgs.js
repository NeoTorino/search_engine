// Global variables
let organizationsData = [];
let currentSort = { column: null, direction: 'asc' };

// Load all data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadOrganizations();
    
    // Setup search functionality
    document.getElementById('searchOrgs').addEventListener('input', filterOrganizations);
    
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
    
    // Add event listeners for sorting
    document.getElementById('sort-header-name').addEventListener('click', () => sortTable('name'));
    document.getElementById('sort-header-jobs').addEventListener('click', () => sortTable('jobs'));
    document.getElementById('sort-header-date').addEventListener('click', () => sortTable('date'));
    
    // Re-attach search event listener since we recreated the input
    document.getElementById('searchOrgs').addEventListener('input', filterOrganizations);
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

// Load organizations table
async function loadOrganizations() {
    try {
        const response = await fetch('/api/stats/organizations');
        const data = await response.json();
        
        organizationsData = data.organizations;
        renderOrganizationsTable(organizationsData);
    } catch (error) {
        console.error('Error loading organizations:', error);
        document.getElementById('orgsTableBody').innerHTML = 
            '<tr><td colspan="3" class="text-center"><div class="error-message">Error loading organizations</div></td></tr>';
    }
}

// Render organizations table
function renderOrganizationsTable(organizations) {
    const tbody = document.getElementById('orgsTableBody');
    
    if (organizations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">No organizations found</td></tr>';
        return;
    }
    
    tbody.innerHTML = organizations
        .filter(org => org.name && org.last_updated) // Skip rows with missing name or last_updated
        .map(org => `
            <tr>
                <td>
                    ${org.url_careers ? 
                        `<a href="${org.url_careers}" target="_blank" rel="noopener noreferrer"><strong>${org.name}</strong></a>` : 
                        `<strong>${org.name}</strong>`
                    }
                </td>
                <td><span>${org.job_count || 0}</span></td>
                <td>${formatDate(org.last_updated)}</td>
            </tr>
        `).join('');
}

// Filter organizations
function filterOrganizations() {
    const searchTerm = document.getElementById('searchOrgs').value.toLowerCase();
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

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}