// filters.js - Filter management, UI updates, and AJAX operations

let currentQuery = '';
let filtersVisible = false;
let filterUpdateTimeout = null;

// Track loading state to prevent duplicate calls
let isFilterUpdating = false;
let lastFilterUpdateParams = '';

// Track previous dropdown states to detect actual changes
let previousDropdownStates = {
  'country-select': [],
  'organization-select': [],
  'source-select': []
};

/**
 * Captures the current state of a dropdown
 * @param {string} dropdownId - The ID of the dropdown
 * @returns {Array} Array of selected values
 */
function captureDropdownState(dropdownId) {
  const dropdown = $(`#${dropdownId}`);
  return dropdown.length ? (dropdown.val() || []).slice() : [];
}

/**
 * Captures the current state of all dropdowns
 */
function captureAllDropdownStates() {
  previousDropdownStates['country-select'] = captureDropdownState('country-select');
  previousDropdownStates['organization-select'] = captureDropdownState('organization-select');
  previousDropdownStates['source-select'] = captureDropdownState('source-select');

  console.log('Captured dropdown states:', previousDropdownStates);
}

/**
 * Checks if any dropdown has actually changed
 * @returns {boolean} True if any dropdown has changed
 */
function hasAnyDropdownChanged() {
  const currentStates = {
    'country-select': captureDropdownState('country-select'),
    'organization-select': captureDropdownState('organization-select'),
    'source-select': captureDropdownState('source-select')
  };

  console.log('Comparing states:', {
    previous: previousDropdownStates,
    current: currentStates
  });

  // Check each dropdown for changes
  for (const dropdownId in currentStates) {
    const previous = previousDropdownStates[dropdownId] || [];
    const current = currentStates[dropdownId] || [];

    // Compare arrays - check if lengths are different or if any values are different
    if (previous.length !== current.length) {
      console.log(`${dropdownId} changed: length difference`);
      return true;
    }

    // Sort both arrays for comparison to handle order differences
    const sortedPrevious = [...previous].sort();
    const sortedCurrent = [...current].sort();

    for (let i = 0; i < sortedPrevious.length; i++) {
      if (sortedPrevious[i] !== sortedCurrent[i]) {
        console.log(`${dropdownId} changed: value difference`);
        return true;
      }
    }
  }

  console.log('No dropdown changes detected');
  return false;
}

/**
 * Toggles the visibility of filters panel
 */
function toggleFilters() {
  const filtersContainer = document.getElementById('filters');
  const toggleButton = document.getElementById('toggle-filters');
  const toggleText = document.getElementById('toggle-filters-text');

  if (!filtersContainer || !toggleButton || !toggleText) {
      console.log('Filter elements not found:', {
          filtersContainer: !!filtersContainer,
          toggleButton: !!toggleButton,
          toggleText: !!toggleText
      });
      return;
  }

  filtersVisible = !filtersVisible;
  console.log('Toggling filters. New state:', filtersVisible);

  if (filtersVisible) {
    // Show filters
    filtersContainer.classList.remove('hidden');
    filtersContainer.classList.add('show');
    toggleButton.classList.add('active');
    toggleText.textContent = 'Hide Filters';

    // Capture initial state when filters are shown
    captureAllDropdownStates();
  } else {
    // Hide filters
    filtersContainer.classList.remove('show');
    filtersContainer.classList.add('hidden');
    toggleButton.classList.remove('active');
    toggleText.textContent = 'Show Filters';
  }
}

/**
 * Initialize filters as hidden when on results page
 */
function initializeFiltersState() {
  const filtersContainer = document.getElementById('filters');
  const toggleButton = document.getElementById('toggle-filters');
  const toggleText = document.getElementById('toggle-filters-text');

  if (filtersContainer && toggleButton) {
    filtersContainer.classList.add('hidden');
    filtersContainer.classList.remove('show');
    if (toggleButton) toggleButton.classList.remove('active');
    if (toggleText) toggleText.textContent = 'Show Filters';
    filtersVisible = false;
  }

  // Capture initial dropdown states
  captureAllDropdownStates();
}

/**
 * Updates the results count display
 * @param {number} totalResults - Total number of results
 * @param {string} query - Search query
 */
function updateResultsCount(totalResults, query) {
  // Look for the new results count element in the header
  const resultsCountElement = document.querySelector('#results-count p');

  if (resultsCountElement) {
    const formattedCount = totalResults.toLocaleString();
    const plural = totalResults !== 1 ? 's' : '';

    let message;
    if (!query || query.trim() === '') {
      message = `Showing all jobs`;
    } else {
      if(totalResults >= 10000){
        message = `Showing all jobs`;
      }else{
        message = `About ${formattedCount} result${plural} for "<strong>${query}</strong>"`;
      }
    }
    resultsCountElement.innerHTML = message;
  }
}

/**
 * Updates country dropdown with new counts
 * @param {object} countryCounts - Object with country names and counts
 */
function updateCountryCounts(countryCounts) {
  const countrySelect = $('#country-select');
  if (countrySelect.length && countryCounts && Object.keys(countryCounts).length > 0) {
    const selectedValues = countrySelect.val() || [];

    countrySelect.selectpicker('destroy');
    countrySelect.empty();

    Object.entries(countryCounts).forEach(([country, count]) => {
      const option = $('<option></option>')
        .attr('value', country)
        .text(`${country} (${count})`);

      if (selectedValues.includes(country)) {
        option.attr('selected', 'selected');
      }

      countrySelect.append(option);
    });

    countrySelect.selectpicker();
  }
}

/**
 * Updates organization dropdown with new counts
 * @param {object} organizationCounts - Object with organization names and counts
 */
function updateOrganizationCounts(organizationCounts) {
  const organizationSelect = $('#organization-select');
  if (organizationSelect.length && organizationCounts && Object.keys(organizationCounts).length > 0) {
    const selectedValues = organizationSelect.val() || [];

    organizationSelect.selectpicker('destroy');
    organizationSelect.empty();

    Object.entries(organizationCounts).forEach(([organization, count]) => {
      const option = $('<option></option>')
        .attr('value', organization)
        .text(`${organization} (${count})`);

      if (selectedValues.includes(organization)) {
        option.attr('selected', 'selected');
      }

      organizationSelect.append(option);
    });

    organizationSelect.selectpicker();
  }
}

/**
 * Updates source dropdown with new counts
 * @param {object} sourceCounts - Object with source names and counts
 */
function updateSourceCounts(sourceCounts) {
  const sourceSelect = $('#source-select');
  if (sourceSelect.length && sourceCounts && Object.keys(sourceCounts).length > 0) {
    const selectedValues = sourceSelect.val() || [];

    sourceSelect.selectpicker('destroy');
    sourceSelect.empty();

    Object.entries(sourceCounts).forEach(([source, count]) => {
      const option = $('<option></option>')
        .attr('value', source)
        .text(`${source} (${count})`);

      if (selectedValues.includes(source)) {
        option.attr('selected', 'selected');
      }

      sourceSelect.append(option);
    });

    sourceSelect.selectpicker();
  }
}

/**
 * Fetches filtered results via AJAX
 * @param {string} queryParams - URL encoded query parameters
 */
function fetchFilteredResults(queryParams) {
  resetLoadMoreButton();

  // Temporarily remove event listeners before updating dropdowns
  $('#country-select, #organization-select, #source-select').off('hidden.bs.select.customFilter');

  const url = `/search?${queryParams}`;
  fetchWithSecurity(url)
    .then(response => {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return response.json();
      } else {
        return response.text().then(html => ({ html }));
      }
    })
    .then(data => {
      if (data.total_results !== undefined) {
        updateResultsCount(data.total_results, data.query);
        updateCountryCounts(data.country_counts || {});
        updateOrganizationCounts(data.organization_counts || {});
        updateSourceCounts(data.source_counts || {});
        updateLoadMoreButton(data.show_load_more, 12, data.query);
      }

      const resultsContainer = document.getElementById('results-container');
      if (resultsContainer) {
        resultsContainer.innerHTML = data.html;
      }

      // Re-attach event listeners after updating dropdowns
      attachDropdownListeners();

      // Update dropdown states after successful update
      captureAllDropdownStates();
    })
    .catch(error => {
      console.error('Error fetching filtered results:', error);
      attachDropdownListeners();
    });

  refreshActiveTab();
}

/**
 * Resets all filters while keeping the search query
 */
function resetFilters() {
  const queryInput = document.querySelector('input[name="q"]');
  const currentSearchQuery = queryInput ? queryInput.value : '';

  // Reset date slider
  if (window.slider) {
    window.slider.value = window.slider.max;
    updateLabelAndColor(window.slider.max);
  }

  // Reset Bootstrap Select dropdowns
  $('#country-select').selectpicker('deselectAll');
  $('#organization-select').selectpicker('deselectAll');
  $('#source-select').selectpicker('deselectAll');

  currentQuery = sanitizeInput(currentSearchQuery);

  const form = document.getElementById('search-form') || document.querySelector('form');
  if (form) {
    const formData = new FormData(form);
    formData.set('q', currentQuery);
    formData.set('date_posted_days', '31');
    formData.delete('country');
    formData.delete('organization');
    formData.delete('source');
    const params = new URLSearchParams(formData);
    fetchFilteredResults(params.toString());
  }

  refreshActiveTab();
  handleFilterUpdate();

  // Capture new state after reset
  captureAllDropdownStates();
}

/**
 * Checks if insights tab is currently active and visible
 * @returns {boolean} True if insights tab is active and visible
 */
function isInsightsTabActiveAndVisible() {
  const activeTab = document.querySelector('#mainTabs .nav-link.active');
  const insightsTab = document.querySelector('#mainTabs .nav-link[data-bs-target="#insights"]');
  const insightsPane = document.getElementById('insights');

  // Check if insights tab is active
  const isInsightsActive = activeTab && activeTab.getAttribute('data-bs-target') === '#insights';

  // Check if insights pane is visible (not hidden)
  const isInsightsVisible = insightsPane && insightsPane.classList.contains('active');

  console.log('Insights tab check:', {
    isInsightsActive,
    isInsightsVisible,
    activeTabTarget: activeTab ? activeTab.getAttribute('data-bs-target') : 'none'
  });

  return isInsightsActive && isInsightsVisible;
}

/**
 * Gets current search parameters as string for comparison
 * @returns {string} Current search parameters
 */
function getCurrentSearchParams() {
  const form = document.getElementById('search-form') || document.querySelector('form');
  if (!form) return '';

  const formData = new FormData(form);
  const params = new URLSearchParams(formData);
  return params.toString();
}

/**
 * Handles filter update events with improved duplicate prevention
 */
function handleFilterUpdate() {
  console.log('handleFilterUpdate called');

  // Clear tab cache if available
  if (typeof window.clearTabCache === 'function') {
      window.clearTabCache();
  }

  // Reset insights loading state to allow fresh loads
  if (typeof window.resetInsightsLoadingState === 'function') {
      window.resetInsightsLoadingState();
  }

  // Get current search parameters
  const searchParams = getCurrentSearchParams();
  const normalizedParams = searchParams.trim();

  console.log('Filter update - current params:', normalizedParams);
  console.log('Filter update - last params:', lastFilterUpdateParams);

  // Prevent duplicate calls with same parameters
  if (isFilterUpdating && lastFilterUpdateParams === normalizedParams) {
    console.log('Filter update already in progress with same parameters, skipping');
    return;
  }

  // Check if insights tab is actually active and visible
  if (isInsightsTabActiveAndVisible()) {
    console.log('Insights tab is active and visible, loading insights');

    // Set loading state
    isFilterUpdating = true;
    lastFilterUpdateParams = normalizedParams;

    // Load insights with current parameters
    if (typeof window.loadInsights === 'function') {
      window.loadInsights(searchParams)
        .then(() => {
          console.log('Insights loaded successfully from filter update');
        })
        .catch(error => {
          console.error('Error loading insights from filter update:', error);
        })
        .finally(() => {
          // Reset loading state after a short delay
          setTimeout(() => {
            isFilterUpdating = false;
          }, 1000);
        });
    }
  } else {
    console.log('Insights tab not active/visible, skipping insights load');
    // Reset the loading state since we're not loading
    isFilterUpdating = false;
    lastFilterUpdateParams = '';
  }
}

/**
 * Refreshes the active tab when filters change
 */
function refreshActiveTab() {
  const activeTab = document.querySelector('#mainTabs .nav-link.active');
  if (activeTab) {
    const targetTab = activeTab.getAttribute('data-bs-target');
    const searchParams = getCurrentSearchParams();

    console.log('Refreshing active tab:', targetTab);

    if (targetTab === '#organizations' && typeof window.loadOrganizations === 'function') {
      console.log('Loading organizations for active tab');
      window.loadOrganizations(searchParams);
    }
    // Note: We don't call loadInsights here anymore to prevent duplicates
    // Insights loading is now handled exclusively by handleFilterUpdate() and tab switching
  }
}

/**
 * Attaches dropdown event listeners with improved debouncing and change detection
 */
function attachDropdownListeners() {
  $('#country-select, #organization-select, #source-select').off('hidden.bs.select.customFilter');
  $('#country-select, #organization-select, #source-select').off('shown.bs.select.customFilter');

  // Capture state when dropdown is opened
  $('#country-select, #organization-select, #source-select').on('shown.bs.select.customFilter', function() {
    console.log('Dropdown opened:', this.id);
    captureAllDropdownStates();
  });

  $('#country-select, #organization-select, #source-select').on('hidden.bs.select.customFilter', function() {
    console.log('Dropdown closed:', this.id);

    // Check if any dropdown actually changed
    if (!hasAnyDropdownChanged()) {
      console.log('No changes detected in dropdowns, skipping AJAX call');
      return;
    }

    console.log('Changes detected in dropdowns, proceeding with AJAX call');

    // Clear any existing timeout
    if (filterUpdateTimeout) {
      clearTimeout(filterUpdateTimeout);
    }

    // Debounce the filter update to prevent rapid-fire calls
    filterUpdateTimeout = setTimeout(() => {
      console.log('Processing dropdown change after debounce');

      const queryInput = document.querySelector('input[name="q"]');
      const rawQuery = queryInput ? queryInput.value.trim() : '';
      const query = sanitizeInput(rawQuery);
      currentQuery = query;

      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        formData.set('q', currentQuery);
        const params = new URLSearchParams(formData);

        // Fetch filtered results first
        fetchFilteredResults(params.toString());

        // Then handle filter update (which may load insights if tab is active)
        handleFilterUpdate();
      }
    }, 300); // Increased debounce time slightly for better UX
  });
}

/**
 * Reset filter update tracking (called when search parameters change significantly)
 */
function resetFilterUpdateTracking() {
  console.log('Resetting filter update tracking');
  isFilterUpdating = false;
  lastFilterUpdateParams = '';

  if (filterUpdateTimeout) {
    clearTimeout(filterUpdateTimeout);
    filterUpdateTimeout = null;
  }

  // Also reset dropdown state tracking
  captureAllDropdownStates();
}

// Function to update the slider background gradient based on current value
function updateSliderBackground(slider) {
    if (!slider) return;

    const min = parseFloat(slider.min) || 1;
    const max = parseFloat(slider.max) || 31;
    const value = parseFloat(slider.value) || min;

    // Calculate percentage - note that lower values (closer to "today") should show more color
    // Since min=1 is "today" and max=31 is "all time", we need to invert the calculation
    const percentage = ((value - min) / (max - min)) * 100;

    // Update background gradient
    slider.style.background = `linear-gradient(to right, var(--secondary-color) ${percentage}%, var(--border-color) ${percentage}%)`;
}

// Function to initialize slider on page load
function initializeDateSlider() {
    const slider = document.getElementById('date-slider');
    if (slider) {
        // Set initial background
        updateSliderBackground(slider);

        // Add event listener for input changes
        slider.addEventListener('input', function() {
            updateSliderBackground(this);
        });

        // Also update on change event for better compatibility
        slider.addEventListener('change', function() {
            updateSliderBackground(this);
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeDateSlider);

// Make functions globally available (in case it's called from other scripts)
window.toggleFilters = toggleFilters;
window.fetchFilteredResults = fetchFilteredResults;
window.resetFilters = resetFilters;
window.currentQuery = currentQuery;
window.initializeFiltersState = initializeFiltersState;
window.attachDropdownListeners = attachDropdownListeners;
window.handleFilterUpdate = handleFilterUpdate;
window.getCurrentSearchParams = getCurrentSearchParams;
window.resetFilterUpdateTracking = resetFilterUpdateTracking;
window.updateSliderBackground = updateSliderBackground;
window.initializeDateSlider = initializeDateSlider;