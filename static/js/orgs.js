// Load all data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadOrganizations();
    
    // Setup search functionality
    document.getElementById('searchOrgs').addEventListener('input', filterOrganizations);
});

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
            '<tr><td colspan="4" class="text-center"><div class="error-message">Error loading organizations</div></td></tr>';
    }
}


// Render organizations table
function renderOrganizationsTable(organizations) {
    const tbody = document.getElementById('orgsTableBody');
    
    if (organizations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No organizations found</td></tr>';
        return;
    }
    
    tbody.innerHTML = organizations.map(org => `
        <tr>
            <td><strong>${org.name}</strong></td>
            <td><span>${org.job_count}</span></td>
            <td>${formatDate(org.last_updated)}</td>
        </tr>
    `).join('');
}

// Filter organizations
function filterOrganizations() {
    const searchTerm = document.getElementById('searchOrgs').value.toLowerCase();
    const filtered = organizationsData.filter(org => 
        org.name.toLowerCase().includes(searchTerm) ||
        (org.country && org.country.toLowerCase().includes(searchTerm))
    );
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