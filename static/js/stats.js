let jobsPerDayChart = null;
let countriesChart = null;
let organizationsData = [];
let wordCloudSearchTimeout = null;

// Load all data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadOverviewStats();
    loadJobsPerDay();
    loadTopCountries();
    loadWordCloud();
    setupWordCloudSearch();
});

function showError(elementId) {
    document.getElementById(elementId).innerHTML = '<small style="color: #ff6b6b;">Error</small>';
}

// Setup word cloud search functionality
function setupWordCloudSearch() {
    const searchInput = document.getElementById('wordCloudSearch');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        // Clear previous timeout
        if (wordCloudSearchTimeout) {
            clearTimeout(wordCloudSearchTimeout);
        }
        
        // Debounce the search - wait 500ms after user stops typing
        wordCloudSearchTimeout = setTimeout(() => {
            const searchTerm = this.value.trim();
            loadWordCloud(searchTerm);
        }, 500);
    });
    
    // Also trigger search on Enter key
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            if (wordCloudSearchTimeout) {
                clearTimeout(wordCloudSearchTimeout);
            }
            const searchTerm = this.value.trim();
            loadWordCloud(searchTerm);
        }
    });
}

// Load overview statistics
async function loadOverviewStats() {
    try {
        const response = await fetch('/api/stats/overview');
        const data = await response.json();
        
        document.getElementById('totalJobs').textContent = data.total_jobs.toLocaleString();
        document.getElementById('totalOrgs').textContent = data.total_organizations.toLocaleString();
        document.getElementById('avgJobsPerOrg').textContent = Math.round(data.avg_jobs_per_org);
    } catch (error) {
        console.error('Error loading overview stats:', error);
        showError('totalJobs');
        showError('totalOrgs');
        showError('avgJobsPerOrg');
    }
}

// Load jobs per day chart
async function loadJobsPerDay() {
    try {
        const response = await fetch('/api/stats/jobs-per-day');
        const data = await response.json();
        
        const ctx = document.getElementById('jobsPerDayChart').getContext('2d');
        
        if (jobsPerDayChart) {
            jobsPerDayChart.destroy();
        }
        
        jobsPerDayChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Jobs Posted',
                    data: data.counts,
                    borderColor: '#000064',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#000064',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading jobs per day:', error);
        document.getElementById('jobsPerDayChart').parentElement.innerHTML = 
            '<div class="error-message">Error loading jobs per day chart</div>';
    }
}

// Load top countries chart
async function loadTopCountries() {
    try {
        const response = await fetch('/api/stats/top-countries');
        const data = await response.json();
        
        const ctx = document.getElementById('countriesChart').getContext('2d');
        
        if (countriesChart) {
            countriesChart.destroy();
        }
        
        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c',
            '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'
        ];
        
        // Calculate total for percentage calculation
        const total = data.counts.reduce((sum, count) => sum + count, 0);
        
        countriesChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.countries,
                datasets: [{
                    data: data.counts,
                    backgroundColor: colors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${percentage}%`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading top countries:', error);
        document.getElementById('countriesChart').parentElement.innerHTML = 
            '<div class="error-message">Error loading countries chart</div>';
    }
}

// Load word cloud with optional search term
async function loadWordCloud(searchTerm = '') {
    const canvas = document.getElementById('canvas');
    const container = canvas ? canvas.parentElement : document.querySelector('.word-cloud-container');
    
    if (!container) {
        console.error('Word cloud container not found');
        return;
    }
    
    try {
        // Show loading state
        const loadingMessage = searchTerm ? 
            `Searching for "${searchTerm}"...` : 
            'Loading word cloud...';
            
        container.innerHTML = `
            <div class="loading-overlay">
                <div class="loading-spinner"></div>
                <p style="margin-top: 1rem; color: #666;">${loadingMessage}</p>
            </div>
        `;
        
        // Build URL with search parameter
        const url = searchTerm ? 
            `/api/stats/word-cloud?q=${encodeURIComponent(searchTerm)}` : 
            '/api/stats/word-cloud';
            
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Word cloud data received:', data);
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (!data.words || data.words.length === 0) {
            // Show no results message
            const noResultsMessage = searchTerm ? 
                `No results found for "${searchTerm}". Try a different search term.` : 
                'No word data available.';
                
            container.innerHTML = `
                <div class="no-results-message" style="text-align: center; padding: 2rem; color: #666;">
                    <p>${noResultsMessage}</p>
                    ${searchTerm ? '<p><small>Try searching for job titles like "manager", "developer", or "analyst"</small></p>' : ''}
                </div>
            `;
            return;
        }

        // Restore canvas element
        container.innerHTML = '<canvas id="canvas"></canvas>';
        
        createHTMLWordCloud(data.words, searchTerm);
        
    } catch (error) {
        console.error('Error loading word cloud:', error);
        
        const errorMessage = searchTerm ? 
            `Error searching for "${searchTerm}". Please try again.` : 
            'Error loading word cloud. Please try again.';
            
        container.innerHTML = `
            <div class="error-message" style="text-align: center; padding: 2rem; color: #ff6b6b;">
                <p>${errorMessage}</p>
                <button onclick="loadWordCloud('${searchTerm}')" class="btn btn-sm btn-outline-primary">Retry</button>
            </div>
        `;
    }
}

// HTML-based word cloud (improved with search context)
function createHTMLWordCloud(words, searchTerm = '') {
    const container = document.getElementById('canvas').parentElement;
    const limitedWords = words.slice(0, 50); // Show more words for better search results
    
    if (limitedWords.length === 0) {
        return;
    }
    
    const maxCount = Math.max(...limitedWords.map(w => w.count));
    const minCount = Math.min(...limitedWords.map(w => w.count));
    
    const colors = [
        '#667eea', '#764ba2', '#f093fb', '#f5576c',
        '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
        '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4',
        '#a8e6cf', '#fdcb6e', '#6c5ce7', '#fd79a8'
    ];
    
    // Shuffle words for more natural distribution
    const shuffledWords = [...limitedWords].sort(() => Math.random() - 0.5);
    
    const wordElements = shuffledWords.map((word, index) => {
        const ratio = maxCount > minCount ? (word.count - minCount) / (maxCount - minCount) : 0.5;
        const fontSize = Math.round(16 + ratio * 32);
        const color = colors[index % colors.length];
        
        // Add some random rotation for visual interest
        const rotations = [0, -15, -10, -5, 5, 10, 15];
        const rotation = rotations[Math.floor(Math.random() * rotations.length)];
        
        // Highlight search terms
        const isSearchMatch = searchTerm && 
            word.text.toLowerCase().includes(searchTerm.toLowerCase());
        const extraStyle = isSearchMatch ? 
            'border: 2px solid #667eea; background: rgba(102, 126, 234, 0.1); padding: 2px 6px; border-radius: 4px;' : '';
        
        return `<span class="word-cloud-word" 
                      style="font-size: ${fontSize}px; 
                             color: ${color}; 
                             font-weight: ${ratio > 0.7 ? 'bold' : ratio > 0.4 ? '600' : 'normal'};
                             transform: rotate(${rotation}deg);
                             opacity: ${0.8 + ratio * 0.2};
                             ${extraStyle}" 
                      title="${word.text}: ${word.count} mentions"
                      data-count="${word.count}">
                    ${word.text}
                </span>`;
    }).join(' ');
    
    // Add search context message
    const searchMessage = searchTerm ? 
        `<div class="search-context" style="text-align: center; padding: 0.5rem; background: #ffffff; border-radius: 4px;">
            <small class="text-muted">Showing words from jobs matching: "<strong>${searchTerm}</strong>" (${limitedWords.length} most common words)</small>
         </div>` : '';
    
    container.innerHTML = `
        ${searchMessage}
        <div class="html-word-cloud" id="html-word-cloud">
            ${wordElements}
        </div>
    `;
    
    // Add click handlers for interactivity
    container.querySelectorAll('.word-cloud-word').forEach(word => {
        // word.addEventListener('click', function() {
        //     const count = this.getAttribute('data-count');
        //     const text = this.textContent;
        //     const contextMessage = searchTerm ? 
        //         ` in jobs matching "${searchTerm}"` : 
        //         ' across all job postings';
        //     alert(`"${text}" appears ${count} times${contextMessage}`);
        // });
        
        // Add hover effect
        word.addEventListener('mouseenter', function() {
            this.style.transform = this.style.transform.replace('scale(1)', '') + ' scale(1.1)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        word.addEventListener('mouseleave', function() {
            this.style.transform = this.style.transform.replace(' scale(1.1)', '');
        });
    });
}