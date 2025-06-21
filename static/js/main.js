// main.js - Main application logic, event handlers, and initialization

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Bootstrap selectpickers
  $('.selectpicker').selectpicker();

  // Date slider functionality
  const slider = document.getElementById('date-slider');
  const label = document.getElementById('date-slider-label');

  // Make slider globally available for filters.js
  window.slider = slider;

  /**
   * Updates date slider label and visual appearance
   * @param {number} value - Slider value
   */
  function updateLabelAndColor(value) {
    const val = parseInt(value);
    const max = parseInt(slider.max);
    const percent = (val / max) * 100;

    label.textContent = val === 31
    ? "Showing all jobs"
    : `Showing jobs posted today${val === 0 ? '' : ` and past ${val} day${val > 1 ? 's' : ''}`}`;

    slider.style.background = `linear-gradient(to right, #64748b 0%, #64748b ${percent}%, #dee2e6 ${percent}%, #dee2e6 100%)`;
  }

  // Make updateLabelAndColor globally available
  window.updateLabelAndColor = updateLabelAndColor;

  if (slider) {
    updateLabelAndColor(slider.value);

    slider.addEventListener('input', (e) => {
      updateLabelAndColor(e.target.value);
    });

    slider.addEventListener('change', (e) => {
      const queryInput = document.querySelector('input[name="q"]');
      const rawQuery = queryInput ? queryInput.value.trim() : '';
      const query = sanitizeInput(rawQuery);
      window.currentQuery = query;

      const form = document.getElementById('search-form');
      if (form) {
        const formData = new FormData(form);
        formData.set('q', window.currentQuery);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
      }

      handleFilterUpdate();
    });
  }

  /**
   * Resets load more button to initial state
   */
  function resetLoadMoreButton() {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      loadMoreBtn.disabled = false;
      loadMoreBtn.textContent = 'Load More';
      loadMoreBtn.dataset.offset = '12';
      loadMoreBtn.dataset.query = '';
    }
  }

  /**
   * Updates load more button state
   * @param {boolean} showLoadMore - Whether to show the button
   * @param {number} newOffset - New offset value
   * @param {string} query - Current query
   */
  function updateLoadMoreButton(showLoadMore, newOffset, query = '') {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      if (showLoadMore) {
        loadMoreBtn.style.display = 'block';
        loadMoreBtn.dataset.offset = newOffset || 12;
        loadMoreBtn.dataset.query = query || '';
        loadMoreBtn.disabled = false;
        loadMoreBtn.textContent = 'Load More';
      } else {
        loadMoreBtn.style.display = 'none';
      }
    }
  }

  // Make functions globally available
  window.resetLoadMoreButton = resetLoadMoreButton;
  window.updateLoadMoreButton = updateLoadMoreButton;

  // Initialize jQuery selectpickers and attach listeners
  $(document).ready(function() {
    $('#country-select').selectpicker();
    $('#organization-select').selectpicker();
    $('#source-select').selectpicker();
    attachDropdownListeners();
  });

  // Load More functionality
  document.getElementById('load-more')?.addEventListener('click', async function () {
    const btn = this;
    const query = window.currentQuery || btn.dataset.query || '';
    const offset = parseInt(btn.dataset.offset) || 0;

    btn.disabled = true;
    btn.textContent = 'Loading...';

    const form = document.getElementById('search-form');
    const formData = new FormData(form);
    formData.set('from', offset);
    const sanitizedQuery = sanitizeInput(query);
    formData.set('q', sanitizedQuery);
    const params = new URLSearchParams(formData);

    try {
      const res = await fetchWithSecurity(`/search?${params.toString()}`);

      if (res.ok) {
        const contentType = res.headers.get('content-type');
        let html;

        if (contentType && contentType.includes('application/json')) {
          const data = await res.json();
          html = data.html;
        } else {
          html = await res.text();
        }

        if (!html || !html.trim()) {
          btn.textContent = 'No more results';
          btn.disabled = true;
          return;
        }

        const container = document.getElementById('results-container');
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        const newCards = tempDiv.querySelectorAll('.card');
        if (newCards.length === 0) {
          btn.textContent = 'No more results';
          btn.disabled = true;
          return;
        }

        container.insertAdjacentHTML('beforeend', html);

        // Scroll to first new card
        const allCards = container.querySelectorAll('.card');
        const newCardsCount = newCards.length;
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
        btn.disabled = true;
      }
    } catch (error) {
      console.error('Error loading more results:', error);
      btn.textContent = 'Error loading more results';
      btn.disabled = true;
    }
  });

  // Search form submission (navbar search)
  const searchForm = document.querySelector('.search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const input = document.getElementById('search-input');
      const rawQuery = input.value.trim();
      const query = sanitizeInput(rawQuery);
      window.currentQuery = query;

      // Reset ALL filters when searching
      if (slider) {
        slider.value = slider.max;
        updateLabelAndColor(slider.max);
      }

      $('#country-select').selectpicker('deselectAll');
      $('#organization-select').selectpicker('deselectAll');
      $('#source-select').selectpicker('deselectAll');

      // Update the main search input to match
      const mainSearchInput = document.querySelector('input[name="q"]');
      if (mainSearchInput) {
        mainSearchInput.value = window.currentQuery;
      }

      const params = new URLSearchParams();
      params.set('q', window.currentQuery);
      params.set('date_posted_days', '31');

      fetchFilteredResults(params.toString());
      handleFilterUpdate();
    });
  }

  // Toggle Filters button
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

  // Reset Filters button
  const resetButton = document.getElementById('reset-filters');
  if (resetButton) {
    resetButton.addEventListener('click', function(e) {
      e.preventDefault();
      resetFilters();
    });
  }

  // Filters form submission
  const filtersForm = document.getElementById('search-form');
  if (filtersForm) {
    filtersForm.addEventListener('submit', function(e) {
      e.preventDefault();

      const searchButton = document.getElementById('search-btn');
      const activeElement = document.activeElement;

      handleFilterUpdate();

      if (activeElement === searchButton || e.submitter === searchButton) {
        // Search submission - reset all filters
        const queryInput = document.querySelector('input[name="q"]');
        const rawQuery = queryInput ? queryInput.value.trim() : '';
        const query = sanitizeInput(rawQuery);
        window.currentQuery = query;

        if (slider) {
          slider.value = slider.max;
          updateLabelAndColor(slider.max);
        }

        $('#country-select').selectpicker('deselectAll');
        $('#organization-select').selectpicker('deselectAll');
        $('#source-select').selectpicker('deselectAll');

        const navbarSearchInput = document.getElementById('search-input');
        if (navbarSearchInput) {
          navbarSearchInput.value = window.currentQuery;
        }

        const params = new URLSearchParams();
        params.set('q', window.currentQuery);
        params.set('date_posted_days', '31');
        fetchFilteredResults(params.toString());
      } else {
        // Filter update
        const queryInput = document.querySelector('input[name="q"]');
        const rawQuery = queryInput ? queryInput.value.trim() : '';
        const query = sanitizeInput(rawQuery);
        window.currentQuery = query;

        const formData = new FormData(this);
        formData.set('q', window.currentQuery);
        const params = new URLSearchParams(formData);
        fetchFilteredResults(params.toString());
      }
    });
  }

  // Initialize filters state on page load
  initializeFiltersState();
});