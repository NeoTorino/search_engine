document.addEventListener('DOMContentLoaded', () => {
  let currentQuery = '';

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

  // Function to update country counts in the multiselect
  function updateCountryCounts(countryCounts) {
    // Update the global variable so the multiselect can use it
    window.countryCountsFromFlask = countryCounts;
    
    // Regenerate the countries array with new counts
    if (countryCounts && typeof countryCounts === 'object' && Object.keys(countryCounts).length > 0) {
      window.countriesFromFlask = Object.entries(countryCounts).map(([label, count]) => ({
        value: label,
        label: `${label} (${count})`
      }));
    } else {
      window.countriesFromFlask = [];
    }

    // If multiselect instance exists, update its options
    const multiselectContainer = document.getElementById('country-multiselect');
    if (multiselectContainer && multiselectContainer.multiselectInstance) {
      multiselectContainer.multiselectInstance.updateOptions(window.countriesFromFlask);
    }
  }

  // Function to update organization counts in the multiselect
  function updateOrganizationCounts(organizationCounts) {
    // Update the global variable so the multiselect can use it
    window.organizationCountsFromFlask = organizationCounts;
    
    // Regenerate the organizations array with new counts
    if (organizationCounts && typeof organizationCounts === 'object' && Object.keys(organizationCounts).length > 0) {
      window.organizationsFromFlask = Object.entries(organizationCounts).map(([label, count]) => ({
        value: label,
        label: `${label} (${count})`
      }));
    } else {
      window.organizationsFromFlask = [];
    }

    // If multiselect instance exists, update its options
    const multiselectContainer = document.getElementById('organization-multiselect');
    if (multiselectContainer && multiselectContainer.multiselectInstance) {
      multiselectContainer.multiselectInstance.updateOptions(window.organizationsFromFlask);
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

    // Reset country multiselect
    const countryMultiselect = document.getElementById('country-multiselect');
    if (countryMultiselect && countryMultiselect.multiselectInstance) {
      countryMultiselect.multiselectInstance.setSelectedValues([]);
    }

    // Reset organization multiselect
    const organizationMultiselect = document.getElementById('organization-multiselect');
    if (organizationMultiselect && organizationMultiselect.multiselectInstance) {
      organizationMultiselect.multiselectInstance.setSelectedValues([]);
    }

    // Legacy checkbox reset (if any exist)
    const checkboxes = document.querySelectorAll('input[name="country"], input[name="organization"]');
    checkboxes.forEach(cb => cb.checked = false);

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
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
          resultsContainer.innerHTML = data.html;
        }

        // Update metadata if it's a JSON response (filter changes)
        if (data.total_results !== undefined) {
          updateResultsCount(data.total_results, data.query);
          updateCountryCounts(data.country_counts || {});
          updateOrganizationCounts(data.organization_counts || {});
          updateLoadMoreButton(data.show_load_more, 12, data.query);
        }
      })
      .catch(error => {
        console.error('Error fetching filtered results:', error);
      });
  };

  const slider = document.getElementById('date-slider');
  const label = document.getElementById('date-slider-label');

  if (slider) {
    function debounce(func, wait) {
      let timeout;
      return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    }

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

    const debounceFetchFilteredResults = debounce(() => {
      const form = slider.closest('form');
      const formData = new FormData(form);
      const sanitizedQuery = sanitizeInput(currentQuery);
      formData.set('q', sanitizedQuery); // ensure sanitized query is sent (can be empty)
      const params = new URLSearchParams(formData);
      fetchFilteredResults(params.toString());
    }, 300);
    
    slider.addEventListener('input', (e) => {
      updateLabelAndColor(e.target.value);
      debounceFetchFilteredResults();
    });
    
    slider.addEventListener('change', (e) => {
      const form = slider.closest('form');
      const formData = new FormData(form);
      const sanitizedQuery = sanitizeInput(currentQuery);
      formData.set('q', sanitizedQuery); // ensure sanitized query is sent (can be empty)
      const params = new URLSearchParams(formData);
      fetchFilteredResults(params.toString());
    });
    
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

  // Handle navbar form submission
  const navbarForm = document.querySelector('.navbar-search-form');
  if (navbarForm) {
    navbarForm.addEventListener('submit', (e) => {
      const input = document.getElementById('navbar-search-input');
      const rawQuery = input.value.trim();
      const query = sanitizeInput(rawQuery);
      
      // Allow empty queries - set currentQuery to empty string if no query
      currentQuery = query;

      // Reset filters
      if (slider) {
        slider.value = slider.max;
        updateLabelAndColor(slider.max);
      }

      // Reset country multiselect
      const countryMultiselect = document.getElementById('country-multiselect');
      if (countryMultiselect && countryMultiselect.multiselectInstance) {
        countryMultiselect.multiselectInstance.setSelectedValues([]);
      }

      // Reset organization multiselect
      const organizationMultiselect = document.getElementById('organization-multiselect');
      if (organizationMultiselect && organizationMultiselect.multiselectInstance) {
        organizationMultiselect.multiselectInstance.setSelectedValues([]);
      }

      // Legacy checkbox reset (if any exist)
      const checkboxes = document.querySelectorAll('input[name="country"], input[name="organization"]');
      checkboxes.forEach(cb => cb.checked = false);
    });
  }

  // Add event listener for "Reset Filters" button if it exists
  const resetButton = document.getElementById('reset-filters');
  if (resetButton) {
    resetButton.addEventListener('click', function(e) {
      e.preventDefault();
      resetFilters();
    });
  }
});