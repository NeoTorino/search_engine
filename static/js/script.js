$(document).ready(function() {
    const filterBtn = $('[data-target="#filtersCollapse"]');
    $('#filtersCollapse').on('show.bs.collapse', function () {
      filterBtn.addClass('btn-filter-active');
    });
    $('#filtersCollapse').on('hide.bs.collapse', function () {
      filterBtn.removeClass('btn-filter-active');
    });
  });

document.getElementById('load-more')?.addEventListener('click', async function () {
    const btn = this;
    const query = btn.dataset.query;
    const offset = parseInt(btn.dataset.offset) || 0;
    const countries = btn.dataset.country ? btn.dataset.country.split(',') : [];
    const datePosted = btn.dataset.date || '';

    btn.disabled = true;
    btn.textContent = 'Loading...';

    // Build query string
    const params = new URLSearchParams();
    params.append('q', query);
    params.append('from', offset);
    countries.forEach(c => params.append('country', c));
    if (datePosted) params.append('date_posted', datePosted);

    const res = await fetch(`/?${params.toString()}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

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

        // Scroll into view
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
});
