let jobsPerDayChart = null;
let countriesChart = null;
let organizationsData = [];

// Load all data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadOverviewStats();
    loadJobsPerDay();
    loadTopCountries();
    loadWordCloud();
});

function showError(elementId) {
    document.getElementById(elementId).innerHTML = '<small style="color: #ff6b6b;">Error</small>';
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
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#667eea',
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

// Simplified word cloud implementation
async function loadWordCloud() {
    const canvas = document.getElementById('canvas');
    const container = canvas.parentElement;
    
    try {
        // Show loading state
        container.innerHTML = `
            <div class="loading-overlay">
                <div class="loading-spinner"></div>
                <p style="margin-top: 1rem; color: #666;">Loading word cloud...</p>
            </div>
        `;
        
        const response = await fetch('/api/stats/word-cloud');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Word cloud data received:', data);
        
        if (!data.words || data.words.length === 0) {
            throw new Error('No word data received');
        }

        // Restore canvas element
        container.innerHTML = '<canvas id="canvas"></canvas>';
        
        createHTMLWordCloud(data.words);
        
    } catch (error) {
        console.error('Error loading word cloud:', error);
        // Create fallback word list
        createSimpleWordList(data?.words || []);
    }
}

// HTML-based word cloud fallback (improved)
function createHTMLWordCloud(words) {
    const container = document.getElementById('canvas').parentElement;
    const limitedWords = words.slice(0, 30);
    
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
    
    // Add click handlers for interactivity
    container.querySelectorAll('.word-cloud-word').forEach(word => {
        word.addEventListener('click', function() {
            const count = this.getAttribute('data-count');
            const text = this.textContent;
            alert(`"${text}" appears ${count} times in job postings`);
        });
    });
}