
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

  window.fetchFilteredResults = function(queryParams) {
    const url = `/search?${queryParams}`;
    fetchWithAjaxHeader(url)
      .then(response => response.text())
      .then(html => {
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
          resultsContainer.innerHTML = html;
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
      formData.append('q', sanitizedQuery); // ensure sanitized query is sent
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
      // const sanitized = DOMPurify.sanitize(input.value);
      formData.append('q', sanitizedQuery); // ensure sanitized query is sent
      const params = new URLSearchParams(formData);
      fetchFilteredResults(params.toString());
    });
    
  }

  // Handle Load More functionality
  document.getElementById('load-more')?.addEventListener('click', async function () {
    const btn = this;
    const query = currentQuery || btn.dataset.query;
    const offset = parseInt(btn.dataset.offset) || 0;

    const checkedCountries = [...document.querySelectorAll('input[name="country"]:checked')].map(cb => cb.value);
    const datePosted = document.getElementById('date-slider')?.value || '';

    btn.disabled = true;
    btn.textContent = 'Loading...';

    const params = new URLSearchParams();
    params.append('q', query);
    params.append('from', offset);
    checkedCountries.forEach(c => params.append('country', c));
    if (datePosted) params.append('date_posted', datePosted);

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
      if (query) {
        currentQuery = query;

        // Reset filters
        if (slider) {
          slider.value = slider.max;
          updateLabelAndColor(slider.max);
        }

        const checkboxes = document.querySelectorAll('input[name="country"]');
        checkboxes.forEach(cb => cb.checked = false);

      }
    });
  }
});
