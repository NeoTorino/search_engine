document.addEventListener('DOMContentLoaded', () => {
  let currentQuery = '';
  let filtersVisible = false; // Track filter visibility state

  $('.selectpicker').selectpicker();

  function sanitizeInput(input) {
    // Remove script tags or HTML tags
    return input.replace(/<[^>]*>?/gm, '')  // Strip HTML
                .replace(/["'`\\]/g, '')    // Remove quotes/backslashes
                .trim();                   // Trim whitespace
  }

  function fetchWithAjaxHeader(url, options = {}) {
    options.headers = options.headers || {};
    options.headers['X-Requested-With'] = 'XMLHttpRequest';
    return fetch(url, options);
  }

  // Function to toggle filters visibility
  function toggleFilters() {
    const filtersContainer = document.getElementById('filters');
    const toggleButton = document.getElementById('toggle-filters');
    const toggleText = document.getElementById('toggle-filters-text');
    
    if (!filtersContainer || !toggleButton || !toggleText) return;
    
    filtersVisible = !filtersVisible;
    
    if (filtersVisible) {
      // Show filters
      filtersContainer.classList.remove('hidden');
      filtersContainer.classList.add('visible');
      toggleButton.classList.add('active');
      toggleText.textContent = 'Hide Filters';
    } else {
      // Hide filters
      filtersContainer.classList.remove('visible');
      filtersContainer.classList.add('hidden');
      toggleButton.classList.remove('active');
      toggleText.textContent = 'Show Filters';
    }
  }

  // Initialize filters as hidden when on results page
  function initializeFiltersState() {
    const filtersContainer = document.getElementById('filters');
    const toggleButton = document.getElementById('toggle-filters');
    
    if (filtersContainer && toggleButton) {
      // On page load, filters should be hidden
      filtersContainer.classList.add('hidden');
      filtersContainer.classList.remove('visible');
      toggleButton.classList.remove('active');
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
        resultsCountElement.innerHTML = `About ${formattedCount} result${plural} (showing all jobs)`;
      } else {
        resultsCountElement.innerHTML = `About ${formattedCount} result${plural} for "<strong>${query}</strong>"`;
      }
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

  // Function to update load more button
  function updateLoadMoreButton(showLoadMore, newOffset, query = '') {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      if (showLoadMore) {
        loadMoreBtn.style.display = 'block';
        loadMoreBtn.dataset.offset = newOffset || 12;
        loadMoreBtn.dataset.query = query || '';
      } else {
        loadMoreBtn.style.display = 'none';
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

    // Update currentQuery to keep the search term
    currentQuery = sanitizeInput(currentSearchQuery);
    
    // Get the form and create parameters with current query but reset filters
    const form = document.getElementById('filters-form') || document.querySelector('form');
    if (form) {
      const formData = new FormData(form);
      formData.set('q', currentQuery); // Keep the search query
      formData.set('date_posted_days', '30'); // Reset to default
      // Remove all country and organization filters
      formData.delete('country');
      formData.delete('organization');
      const params = new URLSearchParams(formData);
      fetchFilteredResults(params.toString());
    }
  };

  window.fetchFilteredResults = function(queryParams) {
    const url = `/search?${queryParams}`;
    fetchWithAjaxHeader(url)
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
  };

  const slider = document.getElementById('date-slider');
  const label = document.getElementById('date-slider-label');

  if (slider) {
    function updateLabelAndColor(value) {
      const val = parseInt(value);
      const max = parseInt(slider.max);
      const percent = (val / max) * 100;

      // Update label
      label.textContent = val === 30
      ? "Showing all jobs"
      : `Showing jobs posted today${val === 0 ? '' : ` and past ${val} day${val > 1 ? 's' : ''}`}`;

      // Update background fill of slider
      slider.style.background = `linear-gradient(to right, #007bff 0%, #007bff ${percent}%, #dee2e6 ${percent}%, #dee2e6 100%)`;
    }

    updateLabelAndColor(slider.value);

    // REMOVED: Real-time slider updates - now only updates the visual label
    slider.addEventListener('input', (e) => {
      updateLabelAndColor(e.target.value);
      // No longer triggers fetchFilteredResults automatically
    });
    
    // REMOVED: Real-time slider change event
    // slider.addEventListener('change', (e) => { ... });
  }

  // Handle Load More functionality
  document.getElementById('load-more')?.addEventListener('click', async function () {
    const btn = this;
    const query = currentQuery || btn.dataset.query || ''; // Allow empty query
    const offset = parseInt(btn.dataset.offset) || 0;

    btn.disabled = true;
    btn.textContent = 'Loading...';

    // Use the same method as filter functions to get all form data
    const form = document.getElementById('filters-form');
    const formData = new FormData(form);
    
    // Override the offset for load more
    formData.set('from', offset);
    
    // Ensure the query is set (can be empty)
    const sanitizedQuery = sanitizeInput(query);
    formData.set('q', sanitizedQuery);

    const params = new URLSearchParams(formData);

    try {
      const res = await fetchWithAjaxHeader(`/search?${params.toString()}`);

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

  // Handle navbar form submission (Search button)
  const navbarForm = document.querySelector('.navbar-search-form');
  if (navbarForm) {
    navbarForm.addEventListener('submit', (e) => {
      e.preventDefault(); // Prevent default form submission
      
      const input = document.getElementById('navbar-search-input');
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

      // Also update the main search input in the filters form to match
      const mainSearchInput = document.querySelector('input[name="q"]');
      if (mainSearchInput) {
        mainSearchInput.value = currentQuery;
      }

      // Create clean search with reset filters
      const params = new URLSearchParams();
      params.set('q', currentQuery);
      params.set('date_posted_days', '30'); // Reset to default
      // Don't add any country or organization parameters (they're reset)
      
      // Fetch results with clean filters
      fetchFilteredResults(params.toString());
    });
  }

  // NEW: Handle Toggle Filters button
  const toggleFiltersButton = document.getElementById('toggle-filters');
  if (toggleFiltersButton) {
    toggleFiltersButton.addEventListener('click', function(e) {
      e.preventDefault();
      toggleFilters();
    });
  }

  // NEW: Handle Update Filters button
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
      const form = document.getElementById('filters-form');
      if (form) {
        const formData = new FormData(form);
        formData.set('q', currentQuery); // Ensure sanitized query is sent
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
      }
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

  // NEW: Also handle form submission from the filters form itself (if needed)
  const filtersForm = document.getElementById('filters-form');
  if (filtersForm) {
    filtersForm.addEventListener('submit', function(e) {
      e.preventDefault(); // Prevent default form submission
      
      // Check if this is a search submission (search button clicked)
      const searchButton = document.getElementById('search-btn');
      const activeElement = document.activeElement;
      
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
        const navbarSearchInput = document.getElementById('navbar-search-input');
        if (navbarSearchInput) {
          navbarSearchInput.value = currentQuery;
        }

        // Create clean search with reset filters
        const params = new URLSearchParams();
        params.set('q', currentQuery);
        params.set('date_posted_days', '30'); // Reset to default
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