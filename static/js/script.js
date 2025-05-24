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

// Date slider functionality
const slider = document.getElementById('date-slider');
const label = document.getElementById("date-slider-label");

if (slider) {
  function updateLabelAndColor(value) {
    const val = parseInt(value);
    const max = parseInt(slider.max);
    const percent = (val / max) * 100;

    label.textContent = val === 30
      ? "Showing all jobs"
      : `Showing jobs posted today${val === 0 ? '' : ` and past ${val} day${val > 1 ? 's' : ''}`}`;

    slider.style.background = `linear-gradient(to right, #007bff 0%, #007bff ${percent}%, #dee2e6 ${percent}%, #dee2e6 100%)`;
  }

  // Initialize appearance
  updateLabelAndColor(slider.value);

  // Update visuals only while dragging
  slider.addEventListener('input', (e) => {
    updateLabelAndColor(e.target.value);
  });

  // Fetch results only when mouse is released or keyboard confirms
  slider.addEventListener('change', (e) => {
    const form = slider.closest('form');
    const formData = new FormData(form);
    const params = new URLSearchParams(formData);

    fetchFilteredResults(params.toString());
  });
}

// Load More functionality
document.getElementById('load-more')?.addEventListener('click', async function () {
  const btn = this;
  const offset = parseInt(btn.dataset.offset) || 0;

  // Find the filter form
  const form = document.getElementById('filter-form'); // Make sure your form has this ID

  const params = new URLSearchParams();
  params.append('from', offset);

  if (form) {
    const formData = new FormData(form);

    // Preserve query, date_posted, and selected countries
    for (const [key, value] of formData.entries()) {
      params.append(key, value);
    }
  }

  btn.disabled = true;
  btn.textContent = 'Loading...';

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

      // Append new results
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = html;
      container.insertAdjacentHTML('beforeend', html);

      // Scroll into view of first new card
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

      // Update offset
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
