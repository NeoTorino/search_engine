// Ensure variables exist and have fallback values
window.countryCountsFromFlask = window.countryCountsFromFlask || {};
window.selected_countries = window.selected_countries || [];

// Generate countries array once at the top level
if (window.countryCountsFromFlask && typeof window.countryCountsFromFlask === 'object' && Object.keys(window.countryCountsFromFlask).length > 0) {
    window.countriesFromFlask = Object.entries(window.countryCountsFromFlask).map(([label, count]) => ({
        value: label,
        label: `${label} (${count})`
    }));
} else {
    window.countriesFromFlask = [];
}


class JobSearchMultiSelect {
    constructor(container, options = {}) {
        this.container = container;
        this.button = container.querySelector('.multiselect-button');
        this.dropdown = container.querySelector('.multiselect-dropdown');
        this.searchInput = container.querySelector('#country-search');
        this.optionsContainer = container.querySelector('#country-options');
        this.arrow = container.querySelector('.multiselect-arrow');
        this.buttonText = container.querySelector('.multiselect-text');
        this.hiddenInputsContainer = document.getElementById('country-hidden-inputs');

        this.selectedValues = new Set(options.preselected || []);
        
        // Use the globally generated countriesFromFlask
        this.allOptions = window.countriesFromFlask || [];
        this.filteredOptions = [...this.allOptions];
        this.isOpen = false;
        this.placeholder = options.placeholder || 'All Countries';

        this.init();
    }

    init() {
        this.bindEvents();
        this.renderOptions();
        this.updateButtonText();
        this.updateHiddenInputs();
    }

    bindEvents() {
        this.button.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggle();
        });

        this.searchInput.addEventListener('input', (e) => {
            this.filterOptions(e.target.value);
        });

        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.close();
            }
        });

        this.dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    renderOptions(optionsToRender = null) {
        const options = optionsToRender || this.filteredOptions;

        if (options.length === 0) {
            this.optionsContainer.innerHTML = '<div class="no-results">No countries found</div>';
            return;
        }

        this.optionsContainer.innerHTML = options.map(option => `
            <div class="multiselect-option ${this.selectedValues.has(option.value) ? 'selected' : ''}" 
                 data-value="${option.value}">
                <input type="checkbox" 
                       class="multiselect-checkbox" 
                       ${this.selectedValues.has(option.value) ? 'checked' : ''}>
                <span>${option.label}</span>
            </div>
        `).join('');

        this.optionsContainer.querySelectorAll('.multiselect-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const value = option.dataset.value;
                const checkbox = option.querySelector('.multiselect-checkbox');

                if (this.selectedValues.has(value)) {
                    this.selectedValues.delete(value);
                    checkbox.checked = false;
                    option.classList.remove('selected');
                } else {
                    this.selectedValues.add(value);
                    checkbox.checked = true;
                    option.classList.add('selected');
                }

                this.updateButtonText();
                this.updateHiddenInputs();
                this.triggerSearch();
            });
        });
    }

    filterOptions(searchTerm) {
        const lower = searchTerm.toLowerCase();
        const filtered = this.allOptions.filter(option =>
            option.value.toLowerCase().includes(lower)
        );
        this.renderOptions(filtered);
    }

    updateButtonText() {
        const count = this.selectedValues.size;
        if (count === 0) {
            this.buttonText.innerHTML = this.placeholder;
        } else if (count === 1) {
            const selectedOption = this.allOptions.find(opt => this.selectedValues.has(opt.value));
            this.buttonText.innerHTML = selectedOption ? selectedOption.label : 'Selected';
        } else {
            this.buttonText.innerHTML = `${count} countries selected`;
        }
    }

    updateHiddenInputs() {
        this.hiddenInputsContainer.innerHTML = '';
        this.selectedValues.forEach(value => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'country';
            input.value = value;
            this.hiddenInputsContainer.appendChild(input);
        });
    }

    triggerSearch() {
        const queryString = this.buildQueryString();
        window.fetchFilteredResults(queryString);
    }

    buildQueryString() {
        const params = new URLSearchParams();

        const q = document.querySelector('input[name="q"]');
        if (q && q.value) {
            params.set('q', q.value);
        }

        const dateSlider = document.getElementById('date-slider');
        if (dateSlider) {
            params.set('date_posted_days', dateSlider.value);
        }

        this.selectedValues.forEach(value => {
            params.append('country', value);
        });

        return params.toString();
    }

    toggle() {
        this.isOpen ? this.close() : this.open();
    }

    open() {
        this.isOpen = true;
        this.dropdown.classList.add('show');
        this.button.classList.add('open');
        this.arrow.classList.add('up');
        this.searchInput.focus();
    }

    close() {
        this.isOpen = false;
        this.dropdown.classList.remove('show');
        this.button.classList.remove('open');
        this.arrow.classList.remove('up');
        this.searchInput.value = '';
        this.renderOptions();  // Reset to all options
    }

    setSelectedValues(values) {
        this.selectedValues = new Set(values);
        this.renderOptions();
        this.updateButtonText();
        this.updateHiddenInputs();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('country-multiselect');
    if (container && window.countriesFromFlask && window.countriesFromFlask.length > 0) {
        new JobSearchMultiSelect(container, {
            preselected: window.selected_countries || [],
            placeholder: 'All Countries'
        });
    } else if (container) {
        console.log("Multiselect container found but no country data available");
        // You could show a message or hide the component here
    }
});