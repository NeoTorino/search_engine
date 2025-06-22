let jobsPerDayChart = null;
let countriesChart = null;

// Enhanced loading state management
let isLoading = false;
let currentSearchParams = '';
let loadingPromise = null; // Track the current loading promise

// Main load function that accepts search parameters
async function loadInsights(searchParams = '') {
    // Normalize search parameters for comparison
    const normalizedParams = searchParams.trim();

    // If same parameters and already loading, return the existing promise
    if (isLoading && currentSearchParams === normalizedParams) {
        console.log('Insights already loading for these parameters, returning existing promise');
        return loadingPromise;
    }

    // If different parameters, cancel any existing load and start fresh
    if (currentSearchParams !== normalizedParams) {
        console.log('Different search parameters detected, allowing new load');
        isLoading = false;
        loadingPromise = null;
    }

    // If still loading but with different params, wait a bit and retry
    if (isLoading) {
        console.log('Still loading previous request, waiting...');
        await new Promise(resolve => setTimeout(resolve, 100));
        return loadInsights(searchParams); // Retry
    }

    // Set loading state
    isLoading = true;
    currentSearchParams = normalizedParams;

    // Create and store the loading promise
    loadingPromise = performInsightsLoad(normalizedParams);

    try {
        const result = await loadingPromise;
        return result;
    } finally {
        // Reset loading state
        isLoading = false;
        loadingPromise = null;
    }
}

// Separate function to perform the actual loading
async function performInsightsLoad(searchParams) {
    try {
        console.log('Starting insights load with params:', searchParams);

        // Show loading state for all components
        showLoadingState();

        // Make single API call to get all insights data
        const url = searchParams ? `/insights?${searchParams}` : '/insights';
        console.log('Loading insights from:', url);

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Process all insights data from single response
        loadOverviewInsightsFromData(data.overview);
        loadJobsPerDayFromData(data.jobs_per_day);
        loadTopCountriesFromData(data.top_countries);
        loadWordCloudFromData(data.word_cloud);

        console.log('Insights loaded successfully');
        return data;

    } catch (error) {
        console.error('Error loading insights:', error);
        showAllErrors();
        throw error;
    }
}

// Reset loading state when search parameters change - improved
window.resetInsightsLoadingState = function() {
    console.log('Resetting insights loading state');
    isLoading = false;
    currentSearchParams = '';
    loadingPromise = null;
};

// Load all data when page loads (but don't auto-load - wait for tab switch)
document.addEventListener('DOMContentLoaded', function() {
    // Don't auto-load insights - wait for tab switch
    // The tab switching in search.html will call loadInsights() when needed
});

function showLoadingState() {
    // Show loading for overview stats
    const totalJobsEl = document.getElementById('totalJobs');
    const totalOrgsEl = document.getElementById('totalOrgs');
    const avgJobsPerOrgEl = document.getElementById('avgJobsPerOrg');

    if (totalJobsEl) totalJobsEl.innerHTML = '<small style="color: #666;">Loading...</small>';
    if (totalOrgsEl) totalOrgsEl.innerHTML = '<small style="color: #666;">Loading...</small>';
    if (avgJobsPerOrgEl) avgJobsPerOrgEl.innerHTML = '<small style="color: #666;">Loading...</small>';

    // Show loading for charts - with proper null checks
    const jobsChartEl = document.getElementById('jobsPerDayChart');
    if (jobsChartEl && jobsChartEl.parentElement) {
        jobsChartEl.parentElement.innerHTML = '<div class="loading-message" style="text-align: center; padding: 2rem; color: #666;">Loading jobs per day chart...</div><canvas id="jobsPerDayChart"></canvas>';
    }

    const countriesChartEl = document.getElementById('countriesChart');
    if (countriesChartEl && countriesChartEl.parentElement) {
        countriesChartEl.parentElement.innerHTML = '<div class="loading-message" style="text-align: center; padding: 2rem; color: #666;">Loading countries chart...</div><canvas id="countriesChart"></canvas>';
    }

    // Show loading for word cloud
    const canvas = document.getElementById('canvas');
    const container = canvas ? canvas.parentElement : document.querySelector('.word-cloud-container');
    if (container) {
        container.innerHTML = `
            <div class="loading-overlay">
                <div class="loading-spinner"></div>
                <p style="margin-top: 1rem; color: #666;">Loading word cloud...</p>
            </div>
        `;
    }
}

function showAllErrors() {
    showError('totalJobs');
    showError('totalOrgs');
    showError('avgJobsPerOrg');

    const jobsChartEl = document.getElementById('jobsPerDayChart');
    if (jobsChartEl && jobsChartEl.parentElement) {
        jobsChartEl.parentElement.innerHTML = '<div class="error-message">Error loading jobs per day chart</div><canvas id="jobsPerDayChart"></canvas>';
    }

    const countriesChartEl = document.getElementById('countriesChart');
    if (countriesChartEl && countriesChartEl.parentElement) {
        countriesChartEl.parentElement.innerHTML = '<div class="error-message">Error loading countries chart</div><canvas id="countriesChart"></canvas>';
    }

    const canvas = document.getElementById('canvas');
    const container = canvas ? canvas.parentElement : document.querySelector('.word-cloud-container');
    if (container) {
        container.innerHTML = `
            <div class="error-message" style="text-align: center; padding: 2rem; color: #ff6b6b;">
                <p>Error loading insights data. Please try again.</p>
            </div>
        `;
    }
}

function showError(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<small style="color: #ff6b6b;">Error</small>';
    }
}

// Load overview statistics from provided data
function loadOverviewInsightsFromData(data) {
    try {
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid overview data');
        }

        const totalJobs = data.total_jobs || 0;
        const totalOrgs = data.total_organizations || 0;
        const avgJobsPerOrg = data.avg_jobs_per_org || 0;

        const totalJobsEl = document.getElementById('totalJobs');
        const totalOrgsEl = document.getElementById('totalOrgs');
        const avgJobsPerOrgEl = document.getElementById('avgJobsPerOrg');

        if (totalJobsEl) totalJobsEl.textContent = totalJobs.toLocaleString();
        if (totalOrgsEl) totalOrgsEl.textContent = totalOrgs.toLocaleString();
        if (avgJobsPerOrgEl) avgJobsPerOrgEl.textContent = Math.round(avgJobsPerOrg);

    } catch (error) {
        console.error('Error processing overview data:', error);
        showError('totalJobs');
        showError('totalOrgs');
        showError('avgJobsPerOrg');
    }
}

// Load jobs per day chart from provided data
function loadJobsPerDayFromData(data) {
    try {
        if (!data || typeof data !== 'object' || !Array.isArray(data.dates) || !Array.isArray(data.counts)) {
            throw new Error('Invalid jobs per day data');
        }

        console.log("Original data length:", data.dates.length);
        console.log("Sample dates:", data.dates.slice(0, 5));
        console.log("Sample counts:", data.counts.slice(0, 5));

        // Check if the chart element exists first
        let chartElement = document.getElementById('jobsPerDayChart');
        if (!chartElement) {
            console.warn('jobsPerDayChart element not found, attempting to create it');

            const chartContainer = document.querySelector('.chart-container canvas#jobsPerDayChart')?.parentElement ||
                                document.querySelector('canvas#jobsPerDayChart')?.parentElement ||
                                document.querySelector('.chart-container:has(h3:contains("Jobs Posted Per Day"))') ||
                                document.querySelector('.chart-container');

            if (chartContainer) {
                // Create the canvas element with fixed height
                chartContainer.innerHTML = `
                    <h3 class="mb-4">Jobs Posted Per Day</h3>
                    <div style="position: relative; height: 400px; width: 100%;">
                        <canvas id="jobsPerDayChart"></canvas>
                    </div>
                `;
                chartElement = document.getElementById('jobsPerDayChart');
            } else {
                throw new Error('Chart container not found');
            }
        } else {
            // Clear any loading messages
            const loadingMessage = chartElement.parentElement?.querySelector('.loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }
        }

        const ctx = chartElement.getContext('2d');

        if (jobsPerDayChart) {
            jobsPerDayChart.destroy();
        }

        // Process data for better visualization
        let processedData = processChartData(data.dates, data.counts);

        // Updated Chart.js configuration in loadJobsPerDayFromData function
        jobsPerDayChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Jobs Posted',
                    data: processedData.dates.map((date, index) => ({
                        x: date,
                        y: processedData.counts[index]
                    })),
                    borderColor: '#000064',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#000064',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                // Add layout padding to prevent clipping
                layout: {
                    padding: {
                        bottom: 5, // Extra space for x-axis labels
                        left: 10,
                        right: 10,
                        top: 10
                    }
                },
                color: '#333',
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            display: true,
                            color: '#333',
                            maxTicksLimit: 8,
                            maxRotation: 45,
                            minRotation: 0, // Allow horizontal labels when space permits
                            font: {
                                size: 12
                            },
                            // Add padding to prevent clipping
                            padding: 10
                        },
                        title: {
                            display: true,
                            text: 'Date',
                            color: '#333',
                            padding: {
                                top: 10
                            }
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            display: true,
                            color: '#333',
                            font: {
                                size: 12
                            },
                            padding: 5
                        },
                        title: {
                            display: true,
                            text: 'Jobs Posted',
                            color: '#333'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Jobs Posted Per Day',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        color: '#333',
                        padding: {
                            top: 10,
                            bottom: 20
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading jobs per day chart:', error);

        const chartContainer = document.querySelector('.chart-container canvas#jobsPerDayChart')?.parentElement ||
                             document.querySelector('canvas#jobsPerDayChart')?.parentElement ||
                             document.querySelector('.chart-container');

        if (chartContainer) {
            chartContainer.innerHTML = '<div class="error-message">Error loading jobs per day chart</div>';
        }
    }
}

function processChartData(dates, counts) {
    const dataLength = dates.length;

    // If data is reasonable size (< 90 days), show all
    if (dataLength <= 90) {
        return { dates, counts };
    }

    // If data is large (90-180 days), show every other day
    if (dataLength <= 180) {
        const filteredDates = [];
        const filteredCounts = [];
        for (let i = 0; i < dataLength; i += 2) {
            filteredDates.push(dates[i]);
            filteredCounts.push(counts[i]);
        }
        return { dates: filteredDates, counts: filteredCounts };
    }

    // If data is very large (> 180 days), aggregate by week
    if (dataLength > 180) {
        return aggregateByWeek(dates, counts);
    }

    return { dates, counts };
}

function aggregateByWeek(dates, counts) {
    const weeklyData = [];
    const weeklyDates = [];

    // Group by weeks (every 7 days)
    for (let i = 0; i < dates.length; i += 7) {
        const weekEnd = Math.min(i + 6, dates.length - 1);

        // Sum counts for the week
        let weeklyTotal = 0;
        for (let j = i; j <= weekEnd; j++) {
            weeklyTotal += counts[j] || 0;
        }

        // Use the last date of the week as label
        weeklyDates.push(`Week of ${dates[i]}`);
        weeklyData.push(weeklyTotal);
    }

    return { dates: weeklyDates, counts: weeklyData };
}

function updateChartData(dates, counts) {
    if (jobsPerDayChart) {
        jobsPerDayChart.data.labels = dates;
        jobsPerDayChart.data.datasets[0].data = counts;

        // Adjust point size based on data density
        const pointSize = dates.length > 100 ? 2 : dates.length > 50 ? 3 : 4;
        jobsPerDayChart.data.datasets[0].pointRadius = pointSize;

        jobsPerDayChart.update('none'); // No animation for better performance
    }
}

// Load top countries chart from provided data
function loadTopCountriesFromData(data) {
    try {
        if (!data || typeof data !== 'object' || !Array.isArray(data.countries) || !Array.isArray(data.counts)) {
            throw new Error('Invalid top countries data');
        }

        // Check if the chart element exists first
        let chartElement = document.getElementById('countriesChart');
        if (!chartElement) {
            console.warn('countriesChart element not found, attempting to create it');

            // Try to find the parent container
            const chartContainer = document.querySelector('.chart-container canvas#countriesChart')?.parentElement ||
                                document.querySelector('canvas#countriesChart')?.parentElement ||
                                document.querySelector('.chart-container:has(h3:contains("Top Countries"))') ||
                                document.querySelectorAll('.chart-container')[1]; // Second chart container

            if (chartContainer) {
                // Create the canvas element with FIXED dimensions optimized for col-lg-4
                chartContainer.innerHTML = `
                    <h3 class="mb-4">Top Countries</h3>
                    <div style="position: relative; height: 400px; width: 100%;">
                        <canvas id="countriesChart"></canvas>
                    </div>
                `;
                chartElement = document.getElementById('countriesChart');
            } else {
                throw new Error('Chart container not found');
            }
        } else {
            // Clear any loading messages
            const loadingMessage = chartElement.parentElement?.querySelector('.loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }
        }

        // Destroy existing chart before creating new one
        if (countriesChart) {
            countriesChart.destroy();
            countriesChart = null;
        }

        const ctx = chartElement.getContext('2d');

        // Limit to top 10 countries to prevent overcrowding
        const maxCountries = 10;
        let displayCountries = data.countries.slice(0, maxCountries);
        let displayCounts = data.counts.slice(0, maxCountries);

        // If there are more countries, group the rest as "Others"
        if (data.countries.length > maxCountries) {
            const othersCounts = data.counts.slice(maxCountries).reduce((sum, count) => sum + count, 0);
            if (othersCounts > 0) {
                displayCountries.push('Others');
                displayCounts.push(othersCounts);
            }
        }

        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c',
            '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
            '#ff6b6b', '#4ecdc4', '#45b7d1'
        ];

        // Calculate total for percentage calculation
        const total = displayCounts.reduce((sum, count) => sum + count, 0);

        countriesChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: displayCountries,
                datasets: [{
                    data: displayCounts,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverBorderWidth: 3,
                    hoverBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // Allow full height usage in narrow column
                layout: {
                    padding: {
                        top: 5,
                        bottom: 5,
                        left: 5,
                        right: 5
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Jobs by Country',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        color: '#333',
                        padding: {
                            top: 5,
                            bottom: 10
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 8, // Optimized for narrow column
                            usePointStyle: true,
                            boxWidth: 10,
                            font: {
                                size: 11 // Slightly smaller for narrow column
                            },
                            generateLabels: function(chart) {
                                const data = chart.data;
                                return data.labels.map((label, index) => {
                                    const value = data.datasets[0].data[index];
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';

                                    // Shorter truncation for narrow column
                                    const truncatedLabel = label.length > 8 ? label.substring(0, 6) + '...' : label;

                                    return {
                                        text: `${truncatedLabel} (${percentage}%)`,
                                        fillStyle: data.datasets[0].backgroundColor[index],
                                        strokeStyle: data.datasets[0].borderColor,
                                        lineWidth: data.datasets[0].borderWidth,
                                        pointStyle: 'circle',
                                        hidden: false,
                                        index: index
                                    };
                                });
                            }
                        },
                        maxHeight: 140, // More space for legend to compensate for narrower width
                        onClick: function(event, legendItem, legend) {
                            const index = legendItem.index;
                            const chart = legend.chart;
                            const meta = chart.getDatasetMeta(0);
                            meta.data[index].hidden = !meta.data[index].hidden;
                            chart.update();
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                                const formattedValue = value.toLocaleString();
                                return `${context.label}: ${formattedValue} (${percentage}%)`;
                            }
                        },
                        titleFont: {
                            size: 14
                        },
                        bodyFont: {
                            size: 13
                        },
                        padding: 12
                    }
                },
                animation: {
                    animateScale: false,
                    animateRotate: true
                }
            }
        });

    } catch (error) {
        console.error('Error loading top countries chart:', error);

        // Try to find any suitable container for error message
        const chartContainer = document.querySelector('.chart-container canvas#countriesChart')?.parentElement ||
                             document.querySelector('canvas#countriesChart')?.parentElement ||
                             document.querySelectorAll('.chart-container')[1];

        if (chartContainer) {
            chartContainer.innerHTML = `
                <h3 class="mb-4">Top Countries</h3>
                <div class="error-message" style="height: 400px; display: flex; align-items: center; justify-content: center;">
                    <p>Error loading countries chart</p>
                </div>
            `;
        }
    }
}

// Load word cloud from provided data
function loadWordCloudFromData(data) {
    const canvas = document.getElementById('canvas');
    const container = canvas ? canvas.parentElement : document.querySelector('.word-cloud-container');

    if (!container) {
        console.error('Word cloud container not found');
        return;
    }

    try {
        if (!data || typeof data !== 'object' || !Array.isArray(data.words)) {
            throw new Error('Invalid word cloud data');
        }

        if (data.words.length === 0) {
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
            </div>
        `;
    }
}

// HTML-based word cloud (simplified - no search context needed)
function createHTMLWordCloud(words) {
    const container = document.getElementById('canvas')?.parentElement;
    if (!container) {
        console.error('Word cloud container not found');
        return;
    }

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