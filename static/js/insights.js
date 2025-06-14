let jobsPerDayChart = null;
let countriesChart = null;

// Main load function that accepts search parameters
async function loadInsights(searchParams = '') {
    loadOverviewInsights(searchParams);
    loadJobsPerDay(searchParams);
    loadTopCountries(searchParams);
    loadWordCloud(searchParams);
}

// Load all data when page loads (but don't auto-load - wait for tab switch)
document.addEventListener('DOMContentLoaded', function() {
    // Don't auto-load insights - wait for tab switch
    // The tab switching in search.html will call loadInsights() when needed
});

function showError(elementId) {
    document.getElementById(elementId).innerHTML = '<small style="color: #ff6b6b;">Error</small>';
}

// Load overview statistics
async function loadOverviewInsights(searchParams = '') {
    try {
        const url = searchParams ? `/api/insights/overview?${searchParams}` : '/api/insights/overview';
        const response = await fetch(url);
        const data = await response.json();

        document.getElementById('totalJobs').textContent = data.total_jobs.toLocaleString();
        document.getElementById('totalOrgs').textContent = data.total_organizations.toLocaleString();
        document.getElementById('avgJobsPerOrg').textContent = Math.round(data.avg_jobs_per_org);
    } catch (error) {
        console.error('Error loading overview insights:', error);
        showError('totalJobs');
        showError('totalOrgs');
        showError('avgJobsPerOrg');
    }
}

// Load jobs per day chart
async function loadJobsPerDay(searchParams = '') {
    try {
        const url = searchParams ? `/api/insights/jobs-per-day?${searchParams}` : '/api/insights/jobs-per-day';
        const response = await fetch(url);
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
async function loadTopCountries(searchParams = '') {
    try {
        const url = searchParams ? `/api/insights/top-countries?${searchParams}` : '/api/insights/top-countries';
        const response = await fetch(url);
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

// Load word cloud (no search input needed - uses main search parameters)
async function loadWordCloud(searchParams = '') {
    const canvas = document.getElementById('canvas');
    const container = canvas ? canvas.parentElement : document.querySelector('.word-cloud-container');

    if (!container) {
        console.error('Word cloud container not found');
        return;
    }

    try {
        // Show loading state
        container.innerHTML = `
            <div class="loading-overlay">
                <div class="loading-spinner"></div>
                <p style="margin-top: 1rem; color: #666;">Loading word cloud...</p>
            </div>
        `;

        // Build URL with search parameters
        const url = searchParams ? `/api/insights/word-cloud?${searchParams}` : '/api/insights/word-cloud';

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (!data.words || data.words.length === 0) {
            // Show no results message
            container.innerHTML = `
                <div class="no-results-message" style="text-align: center; padding: 2rem; color: #666;">
                    <p>No word data available for the current filters.</p>
                </div>
            `;
            return;
        }

        // Restore canvas element
        container.innerHTML = '<canvas id="canvas"></canvas>';

        createHTMLWordCloud(data.words);

    } catch (error) {
        console.error('Error loading word cloud:', error);

        container.innerHTML = `
            <div class="error-message" style="text-align: center; padding: 2rem; color: #ff6b6b;">
                <p>Error loading word cloud. Please try again.</p>
                <button onclick="loadWordCloud('${searchParams}')" class="btn btn-sm btn-outline-primary">Retry</button>
            </div>
        `;
    }
}

// HTML-based word cloud (simplified - no search context needed)
function createHTMLWordCloud(words) {
    const container = document.getElementById('canvas').parentElement;
    const limitedWords = words.slice(0, 50);

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

        return `<span class="word-cloud-word" 
                      style="font-size: ${fontSize}px; 
                             color: ${color}; 
                             font-weight: ${ratio > 0.7 ? 'bold' : ratio > 0.4 ? '600' : 'normal'};
                             transform: rotate(${rotation}deg);
                             opacity: ${0.8 + ratio * 0.2};" 
                      title="${word.text}: ${word.count} mentions"
                      data-count="${word.count}">
                    ${word.text}
                </span>`;
    }).join(' ');

    container.innerHTML = `
        <div class="html-word-cloud" id="html-word-cloud">
            ${wordElements}
        </div>
    `;

    // Add hover effects
    container.querySelectorAll('.word-cloud-word').forEach(word => {
        word.addEventListener('mouseenter', function() {
            this.style.transform = this.style.transform.replace('scale(1)', '') + ' scale(1.1)';
            this.style.transition = 'transform 0.2s ease';
        });

        word.addEventListener('mouseleave', function() {
            this.style.transform = this.style.transform.replace(' scale(1.1)', '');
        });
    });
}