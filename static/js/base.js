document.addEventListener('DOMContentLoaded', () => {
  let currentQuery = '';
  let filtersVisible = false; // Track filter visibility state

  $('.selectpicker').selectpicker();

  function sanitizeInput(input, maxLength = 200, allowSpecialChars = false) {
    if (!input || typeof input !== 'string') {
        return '';
    }

    // Remove null bytes and control characters
    input = input.replace(/\x00/g, '');
    input = input.replace(/[\x00-\x1F\x7F-\x9F]/g, '');

    // Length limiting
    input = input.substring(0, maxLength);

    // Remove HTML tags
    input = input.replace(/<[^>]*>/g, '');

    // Remove dangerous characters
    if (!allowSpecialChars) {
        input = input.replace(/[<>"'`\\;(){}[\]]/g, '');
    }

    // Remove script-related content
    const scriptPatterns = [
        /javascript:/gi,
        /vbscript:/gi,
        /data:/gi,
        /on\w+\s*=/gi,
        /script/gi,
        /iframe/gi,
        /object/gi,
        /embed/gi
    ];

    scriptPatterns.forEach(pattern => {
        input = input.replace(pattern, '');
    });

    // Check for suspicious patterns
    const suspiciousPatterns = [
        /union\s+select/gi,
        /drop\s+table/gi,
        /delete\s+from/gi,
        /insert\s+into/gi,
        /exec\s*\(/gi
    ];

    suspiciousPatterns.forEach(pattern => {
        input = input.replace(pattern, '');
    });

    // Normalize whitespace
    input = input.replace(/\s+/g, ' ').trim();

    return input;
  }

  function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  }

  function fetchWithSecurity(url, options = {}) {
      options.headers = options.headers || {};
      options.headers['X-Requested-With'] = 'XMLHttpRequest';

      const csrfToken = getCSRFToken();
      if (csrfToken) {
          options.headers['X-CSRF-Token'] = csrfToken;
      }

      return fetch(url, options);
  }

  // Function to toggle filters visibility
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
      filtersContainer.classList.add('show'); // Use Bootstrap's show class
      toggleButton.classList.add('active');
      toggleText.textContent = 'Hide Filters';
    } else {
      // Hide filters
      filtersContainer.classList.remove('show');
      filtersContainer.classList.add('hidden');
      toggleButton.classList.remove('active');
      toggleText.textContent = 'Show Filters';
    }
  }

  // Initialize filters as hidden when on results page
  function initializeFiltersState() {
    const filtersContainer = document.getElementById('filters');
    const toggleButton = document.getElementById('toggle-filters');
    const toggleText = document.getElementById('toggle-filters-text');

    if (filtersContainer && toggleButton) {
      // On page load, filters should be hidden
      filtersContainer.classList.add('hidden');
      filtersContainer.classList.remove('show');
      if (toggleButton) toggleButton.classList.remove('active');
      if (toggleText) toggleText.textContent = 'Show Filters';
      filtersVisible = false;
    }
  }

  // Function to update the results count text
  function updateResultsCount(totalResults, query) {
    const resultsCountElement = document.querySelector('.text-muted.liner');
    if (resultsCountElement) {
      const formattedCount = totalResults.toLocaleString();
      const plural = totalResults !== 1 ? 's' : '';

      // Handle empty query display
      if (!query || query.trim() === '') {
        message = `Showing all jobs`;
      } else {
        if(totalResults >= 10000){
          message = `Showing all jobs`;
        }else{
          message = `Found ${formattedCount} result${plural} for "<strong>${query}</strong>"`;
        }
      }
      resultsCountElement.innerHTML = message;
    }
  }

  // Function to update country counts in Bootstrap Select
  function updateCountryCounts(countryCounts) {
    const countrySelect = $('#country-select');
    if (countrySelect.length && countryCounts && Object.keys(countryCounts).length > 0) {

      // Get currently selected values
      const selectedValues = countrySelect.val() || [];

      // Destroy the selectpicker first
      countrySelect.selectpicker('destroy');

      // Clear existing options
      countrySelect.empty();

      // Add new options with updated counts
      Object.entries(countryCounts).forEach(([country, count]) => {
        const option = $('<option></option>')
          .attr('value', country)
          .text(`${country} (${count})`);

        // Maintain selection state
        if (selectedValues.includes(country)) {
          option.attr('selected', 'selected');
        }

        countrySelect.append(option);
      });

      // Reinitialize selectpicker with the same options as before
      countrySelect.selectpicker({
        width: '100%',
        liveSearch: true,
        actionsBox: true,
        title: 'All Countries'
      });

    }
  }

  // Function to update organization counts in Bootstrap Select
  function updateOrganizationCounts(organizationCounts) {
    const organizationSelect = $('#organization-select');
    if (organizationSelect.length && organizationCounts && Object.keys(organizationCounts).length > 0) {

      // Get currently selected values
      const selectedValues = organizationSelect.val() || [];

      // Destroy the selectpicker first
      organizationSelect.selectpicker('destroy');

      // Clear existing options
      organizationSelect.empty();

      // Add new options with updated counts
      Object.entries(organizationCounts).forEach(([organization, count]) => {
        const option = $('<option></option>')
          .attr('value', organization)
          .text(`${organization} (${count})`);

        // Maintain selection state
        if (selectedValues.includes(organization)) {
          option.attr('selected', 'selected');
        }

        organizationSelect.append(option);
      });

      // Reinitialize selectpicker with the same options as before
      organizationSelect.selectpicker({
        width: '100%',
        liveSearch: true,
        actionsBox: true,
        title: 'All Organizations'
      });

    }
  }

  // Function to update source counts in Bootstrap Select
  function updateSourceCounts(sourceCounts) {
    const sourceSelect = $('#source-select');
    if (sourceSelect.length && sourceCounts && Object.keys(sourceCounts).length > 0) {

      // Get currently selected values
      const selectedValues = sourceSelect.val() || [];

      // Destroy the selectpicker first
      sourceSelect.selectpicker('destroy');

      // Clear existing options
      sourceSelect.empty();

      // Add new options with updated counts
      Object.entries(sourceCounts).forEach(([source, count]) => {
        const option = $('<option></option>')
          .attr('value', source)
          .text(`${source} (${count})`);

        // Maintain selection state
        if (selectedValues.includes(source)) {
          option.attr('selected', 'selected');
        }

        sourceSelect.append(option);
      });

      // Reinitialize selectpicker with the same options as before
      sourceSelect.selectpicker({
        width: '100%',
        liveSearch: true,
        actionsBox: true,
        title: 'All Sources'
      });

    }
  }

  // Function to reset load more button to initial state
  function resetLoadMoreButton() {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      loadMoreBtn.disabled = false;
      loadMoreBtn.textContent = 'Load More';
      loadMoreBtn.dataset.offset = '12';
      loadMoreBtn.dataset.query = '';
    }
  }

  // Function to update load more button
  function updateLoadMoreButton(showLoadMore, newOffset, query = '') {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      if (showLoadMore) {
        loadMoreBtn.style.display = 'block';
        loadMoreBtn.dataset.offset = newOffset || 12;
        loadMoreBtn.dataset.query = query || '';
        // Reset button state in case it was previously disabled
        loadMoreBtn.disabled = false;
        loadMoreBtn.textContent = 'Load More';
      } else {
        loadMoreBtn.style.display = 'none';
      }
    }
  }

  // When filters are updated/search is performed
  function handleFilterUpdate() {
    // Call this function whenever:
    // 1. Search form is submitted
    // 2. Filters are changed
    // 3. Any search parameters are updated
    // Clear the tab loading cache so fresh data is loaded
    if (typeof window.clearTabCache === 'function') {
        window.clearTabCache();
    }

    // Reset insights loading state
    if (typeof window.resetInsightsLoadingState === 'function') {
        window.resetInsightsLoadingState();
    }

    // If currently on insights tab, reload the data
    const activeTab = document.querySelector('#mainTabs .nav-link.active');
    if (activeTab && activeTab.getAttribute('data-bs-target') === '#insights') {
        const searchParams = getCurrentSearchParams();
        if (typeof window.loadInsights === 'function') {
            window.loadInsights(searchParams);
        }
    }
  }

  // Function to handle "Reset Filters" functionality
  window.resetFilters = function() {
    // Keep the current search query
    const queryInput = document.querySelector('input[name="q"]');
    const currentSearchQuery = queryInput ? queryInput.value : '';

    // Reset date slider
    if (slider) {
      slider.value = slider.max;
      updateLabelAndColor(slider.max);
    }

    // Reset Bootstrap Select dropdowns
    $('#country-select').selectpicker('deselectAll');
    $('#organization-select').selectpicker('deselectAll');
    $('#source-select').selectpicker('deselectAll');

    // Update currentQuery to keep the search term
    currentQuery = sanitizeInput(currentSearchQuery);

    // Get the form and create parameters with current query but reset filters
    const form = document.getElementById('search-form') || document.querySelector('form');
    if (form) {
      const formData = new FormData(form);
      formData.set('q', currentQuery); // Keep the search query
      formData.set('date_posted_days', '31'); // Reset to default
      // Remove all country, organization, and source filters
      formData.delete('country');
      formData.delete('organization');
      formData.delete('source');
      const params = new URLSearchParams(formData);
      fetchFilteredResults(params.toString());
    }

    refreshActiveTab();
    handleFilterUpdate();
  };

  window.fetchFilteredResults = function(queryParams) {
    // Reset load more button before fetching new results
    resetLoadMoreButton();

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
        // Update metadata FIRST if it's a JSON response (before replacing HTML)
        if (data.total_results !== undefined) {
          updateResultsCount(data.total_results, data.query);
          updateCountryCounts(data.country_counts || {});
          updateOrganizationCounts(data.organization_counts || {});
          updateSourceCounts(data.source_counts || {});
          updateLoadMoreButton(data.show_load_more, 12, data.query);
        }

        // Then update the results container HTML
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
          resultsContainer.innerHTML = data.html;
        }
      })
      .catch(error => {
        console.error('Error fetching filtered results:', error);
      });

    refreshActiveTab();
  };

  const slider = document.getElementById('date-slider');
  const label = document.getElementById('date-slider-label');

  if (slider) {
    function updateLabelAndColor(value) {
      const val = parseInt(value);
      const max = parseInt(slider.max);
      const percent = (val / max) * 100;

      // Update label
      label.textContent = val === 31
      ? "Showing all jobs"
      : `Showing jobs posted today${val === 0 ? '' : ` and past ${val} day${val > 1 ? 's' : ''}`}`;

      // Update background fill of slider
      slider.style.background = `linear-gradient(to right, #64748b 0%, #64748b ${percent}%, #dee2e6 ${percent}%, #dee2e6 100%)`;
    }

    updateLabelAndColor(slider.value);

    slider.addEventListener('input', (e) => {
      updateLabelAndColor(e.target.value);
    });

    // Added change event for when user finishes sliding
    slider.addEventListener('change', (e) => {
      // Auto-update when slider value changes
      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        formData.set('date_posted_days', e.target.value);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
        handleFilterUpdate();
      }
    });
  }

  // Function to refresh the active tab when filters change
  function refreshActiveTab() {
    const activeTab = document.querySelector('#mainTabs .nav-link.active');
    if (activeTab) {
      const targetTab = activeTab.getAttribute('data-bs-target');
      const searchParams = getCurrentSearchParams();

      if (targetTab === '#organizations' && typeof window.loadOrganizations === 'function') {
        window.loadOrganizations(searchParams);
      } else if (targetTab === '#insights' && typeof window.loadInsights === 'function') {
        window.loadInsights(searchParams);
      }
    }
  }

  // Helper function to get current search parameters (make it available globally)
  function getCurrentSearchParams() {
    const form = document.getElementById('search-form');
    if (!form) return '';

    const formData = new FormData(form);
    const params = new URLSearchParams();

    for (let [key, value] of formData.entries()) {
      if (value) params.append(key, value);
    }

    console.log('Current search params:', params.toString());
    return params.toString();
  }

  // Make functions globally available
  window.getCurrentSearchParams = getCurrentSearchParams;
  window.toggleFilters = toggleFilters;

  // Added Bootstrap Select change event listeners
  $(document).ready(function() {
    // Country select change
    $('#country-select').on('changed.bs.select', function(e) {
      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
        handleFilterUpdate();
      }
    });

    // Organization select change
    $('#organization-select').on('changed.bs.select', function(e) {
      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
        handleFilterUpdate();
      }
    });

    // Source select change
    $('#source-select').on('changed.bs.select', function(e) {
      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
        handleFilterUpdate();
      }
    });
  });

  // Handle Load More functionality
  document.getElementById('load-more')?.addEventListener('click', async function () {
    const btn = this;
    const query = currentQuery || btn.dataset.query || ''; // Allow empty query
    const offset = parseInt(btn.dataset.offset) || 0;

    btn.disabled = true;
    btn.textContent = 'Loading...';

    // Use the same method as filter functions to get all form data
    const form = document.getElementById('search-form');
    const formData = new FormData(form);

    // Override the offset for load more
    formData.set('from', offset);

    // Ensure the query is set (can be empty)
    const sanitizedQuery = sanitizeInput(query);
    formData.set('q', sanitizedQuery);

    const params = new URLSearchParams(formData);

    try {
      const res = await fetchWithSecurity(`/search?${params.toString()}`);

      if (res.ok) {
        const html = await res.text();
        if (!html.trim()) {
          btn.textContent = 'No more results';
          btn.disabled = true;
          return;
        }

        const container = document.getElementById('results-container');
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        container.insertAdjacentHTML('beforeend', html);

        const allCards = container.querySelectorAll('.card');
        const newCardsCount = tempDiv.querySelectorAll('.card').length;
        const firstNewCardIndex = allCards.length - newCardsCount;
        const firstNewCard = allCards[firstNewCardIndex];

        if (firstNewCard) {
          const navbarHeight = document.getElementById('topbar')?.offsetHeight || 0;
          const cardTop = firstNewCard.getBoundingClientRect().top + window.pageYOffset;

          window.scrollTo({
            top: cardTop - navbarHeight - 10,
            behavior: 'smooth'
          });
        }

        btn.dataset.offset = offset + 20;
        btn.disabled = false;
        btn.textContent = 'Load More';
      } else {
        btn.textContent = 'Error loading more results';
      }
    } catch (error) {
      console.error('Error loading more results:', error);
      btn.textContent = 'Error loading more results';
    }
  });

  // Handle search form submission (Search button)
  const searchForm = document.querySelector('.search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault(); // Prevent default form submission

      const input = document.getElementById('search-input');
      const rawQuery = input.value.trim();
      const query = sanitizeInput(rawQuery);

      // Set currentQuery
      currentQuery = query;

      // Reset ALL filters when searching
      if (slider) {
        slider.value = slider.max;
        updateLabelAndColor(slider.max);
      }

      // Reset Bootstrap Select dropdowns
      $('#country-select').selectpicker('deselectAll');
      $('#organization-select').selectpicker('deselectAll');
      $('#source-select').selectpicker('deselectAll');  // NEW: Reset source filter

      // Also update the main search input in the filters form to match
      const mainSearchInput = document.querySelector('input[name="q"]');
      if (mainSearchInput) {
        mainSearchInput.value = currentQuery;
      }

      // Create clean search with reset filters
      const params = new URLSearchParams();
      params.set('q', currentQuery);
      params.set('date_posted_days', '30'); // Reset to default
      // Don't add any country, organization, or source parameters (they're reset)

      // Fetch results with clean filters
      fetchFilteredResults(params.toString());

      refreshActiveTab();
      handleFilterUpdate();
    });
  }

  // Handle Toggle Filters button
  const toggleFiltersButton = document.getElementById('toggle-filters');
  if (toggleFiltersButton) {
    console.log('Toggle filters button found, adding event listener');
    toggleFiltersButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log('Toggle filters button clicked');
      toggleFilters();
    });
  } else {
    console.log('Toggle filters button NOT found');
  }

  // Handle Update Filters button
  const updateButton = document.getElementById('update-filters');
  if (updateButton) {
    updateButton.addEventListener('click', function(e) {
      e.preventDefault();

      // Get current search query
      const queryInput = document.querySelector('input[name="q"]');
      const rawQuery = queryInput ? queryInput.value.trim() : '';
      const query = sanitizeInput(rawQuery);
      currentQuery = query;

      // Get the form and create parameters with all current filter values
      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        formData.set('q', currentQuery); // Ensure sanitized query is sent
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
      }

      handleFilterUpdate();
    });
  }

  // Handle "Reset Filters" button
  const resetButton = document.getElementById('reset-filters');
  if (resetButton) {
    resetButton.addEventListener('click', function(e) {
      e.preventDefault();
      resetFilters();
    });
  }

  // Handle form submission from the filters form itself (if needed)
  const filtersForm = document.getElementById('search-form');
  if (filtersForm) {
    filtersForm.addEventListener('submit', function(e) {
      e.preventDefault(); // Prevent default form submission

      // Check if this is a search submission (search button clicked)
      const searchButton = document.getElementById('search-btn');
      const activeElement = document.activeElement;

      handleFilterUpdate(); // ORIGINAL: Already had this

      if (activeElement === searchButton || e.submitter === searchButton) {
        // This is a search - reset all filters
        const queryInput = document.querySelector('input[name="q"]');
        const rawQuery = queryInput ? queryInput.value.trim() : '';
        const query = sanitizeInput(rawQuery);
        currentQuery = query;

        // Reset ALL filters
        if (slider) {
          slider.value = slider.max;
          updateLabelAndColor(slider.max);
        }

        // Reset Bootstrap Select dropdowns
        $('#country-select').selectpicker('deselectAll');
        $('#organization-select').selectpicker('deselectAll');

        // Sync search inputs
        const navbarSearchInput = document.getElementById('search-input');
        if (navbarSearchInput) {
          navbarSearchInput.value = currentQuery;
        }

        // Create clean search with reset filters
        const params = new URLSearchParams();
        params.set('q', currentQuery);
        params.set('date_posted_days', '31'); // Reset to default
        fetchFilteredResults(params.toString());
      } else {
        // This is a regular filter update
        const queryInput = document.querySelector('input[name="q"]');
        const rawQuery = queryInput ? queryInput.value.trim() : '';
        const query = sanitizeInput(rawQuery);
        currentQuery = query;

        const formData = new FormData(this);
        formData.set('q', currentQuery);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
      }
    });
  }

  // Initialize filters state on page load
  initializeFiltersState();
});