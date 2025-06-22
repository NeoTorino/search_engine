// Update your search.js with this enhanced version

document.addEventListener('DOMContentLoaded', function() {
    const tabTriggerList = document.querySelectorAll('#mainTabs button[data-bs-toggle="tab"]');
    const resultsCountContainer = document.getElementById('results-count');
    const orgSearchContainer = document.getElementById('org-search-container');

    // Track loaded tabs to prevent duplicate loading
    const loadedTabs = new Set();

    // Function to show/hide results count and organization search
    function toggleHeaderElements(targetTab) {
        if (resultsCountContainer) {
            if (targetTab === '#results') {
                resultsCountContainer.classList.remove('hidden');
            } else {
                resultsCountContainer.classList.add('hidden');
            }
        }

        if (orgSearchContainer) {
            if (targetTab === '#organizations') {
                orgSearchContainer.classList.remove('hidden');
            } else {
                orgSearchContainer.classList.add('hidden');
            }
        }
    }

    tabTriggerList.forEach(tabTrigger => {
        tabTrigger.addEventListener('shown.bs.tab', event => {
            const targetTab = event.target.getAttribute('data-bs-target');
            const searchParams = getCurrentSearchParams();

            // Toggle header elements visibility
            toggleHeaderElements(targetTab);

            // Create a unique key for this tab + search params combination
            const tabKey = `${targetTab}-${searchParams}`;

            // Load organizations data when organizations tab is shown
            if (targetTab === '#organizations' && typeof window.loadOrganizations === 'function') {
                if (!loadedTabs.has(`orgs-${searchParams}`)) {
                    loadedTabs.add(`orgs-${searchParams}`);
                    window.loadOrganizations(searchParams);
                }
            }

            // Load insights data when insights tab is shown
            if (targetTab === '#insights' && typeof window.loadInsights === 'function') {
                if (!loadedTabs.has(`insights-${searchParams}`)) {
                    loadedTabs.add(`insights-${searchParams}`);
                    window.loadInsights(searchParams);
                }
            }
        });
    });

    // Clear the loaded tabs cache when search parameters change
    window.clearTabCache = function() {
        loadedTabs.clear();
    };

    // Make getCurrentSearchParams available globally for filter updates
    window.getCurrentSearchParams = getCurrentSearchParams;

    // If insights tab is active on page load, load the data
    const activeTab = document.querySelector('#mainTabs .nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#insights') {
        const searchParams = getCurrentSearchParams();
        if (typeof window.loadInsights === 'function') {
            loadedTabs.add(`insights-${searchParams}`);
            window.loadInsights(searchParams);
        }
    }

    // Set initial header elements visibility
    const initialActiveTab = document.querySelector('#mainTabs .nav-link.active');
    if (initialActiveTab) {
        toggleHeaderElements(initialActiveTab.getAttribute('data-bs-target'));
    }
});