document.getElementById('load-more')?.addEventListener('click', async function () {
    const btn = this;
    const query = btn.dataset.query;
    let offset = parseInt(btn.dataset.offset) || 0;

    btn.disabled = true;
    btn.textContent = 'Loading...';

    const res = await fetch(`/?q=${encodeURIComponent(query)}&from=${offset}`, {
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

        // Temporary element to parse new HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;

        // Append new results
        container.insertAdjacentHTML('beforeend', html);

        // Get all cards after insert
        const allCards = container.querySelectorAll('.card');
        const newCardsCount = tempDiv.querySelectorAll('.card').length;

        // Calculate index of first new card
        const firstNewCardIndex = allCards.length - newCardsCount;
        const firstNewCard = allCards[firstNewCardIndex];

        if (firstNewCard) {
            // Calculate offset position minus navbar height
            const navbarHeight = document.getElementById('topbar').offsetHeight || 0;
            const cardTop = firstNewCard.getBoundingClientRect().top + window.pageYOffset;

            window.scrollTo({
                top: cardTop - navbarHeight - 10, // 10px extra padding
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

// Get exact navbar height dynamically
window.addEventListener('load', () => {
    const topbar = document.getElementById('topbar');
    const mainContent = document.getElementById('main-content');
    if (topbar && mainContent) {
      const topbarHeight = topbar.offsetHeight;
      mainContent.style.paddingTop = `${topbarHeight + 16}px`; // 16px extra space
    }
});
  