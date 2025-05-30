// Ensure variables exist and have fallback values
window.countryCountsFromFlask = window.countryCountsFromFlask || {};
window.organizationCountsFromFlask = window.organizationCountsFromFlask || {};
window.selected_countries = window.selected_countries || [];
window.selected_organizations = window.selected_organizations || [];

// Generate countries array once at the top level
if (window.countryCountsFromFlask && typeof window.countryCountsFromFlask === 'object' && Object.keys(window.countryCountsFromFlask).length > 0) {
    window.countriesFromFlask = Object.entries(window.countryCountsFromFlask).map(([label, count]) => ({
        value: label,
        label: `${label} (${count})`
    }));
} else {
    window.countriesFromFlask = [];
}

// Generate organizations array once at the top level
if (window.organizationCountsFromFlask && typeof window.organizationCountsFromFlask === 'object' && Object.keys(window.organizationCountsFromFlask).length > 0) {
    window.organizationsFromFlask = Object.entries(window.organizationCountsFromFlask).map(([label, count]) => ({
        value: label,
        label: `${label} (${count})`
    }));
} else {
    window.organizationsFromFlask = [];
}

class JobSearchMultiSelect {
    constructor(container, options = {}) {
        this.container = container;
        this.button = container.querySelector('.multiselect-button');
        this.dropdown = container.querySelector('.multiselect-dropdown');
        this.searchInput = container.querySelector('input[type="text"]');
        this.optionsContainer = container.querySelector('.multiselect-options');
        this.arrow = container.querySelector('.multiselect-arrow');
        this.buttonText = container.querySelector('.multiselect-text');
        
        // Determine filter type based on container ID
        this.filterType = container.id.includes('country') ? 'country' : 'organization';
        this.hiddenInputsContainer = document.getElementById(`${this.filterType}-hidden-inputs`);

        this.selectedValues = new Set(options.preselected || []);
        
        // Use the appropriate data source
        this.allOptions = this.filterType === 'country' ? 
            (window.countriesFromFlask || []) : 
            (window.organizationsFromFlask || []);
        this.filteredOptions = [...this.allOptions];
        this.isOpen = false;
        this.placeholder = options.placeholder || (this.filterType === 'country' ? 'All Countries' : 'All Organizations');

        // Store reference to this instance on the container for external access
        this.container.multiselectInstance = this;

        this.init();
    }

    init() {
        this.bindEvents();
        this.renderOptions();
        this.updateButtonText();
        this.updateHiddenInputs();
    }

    // Method to update options with new data (called when counts change)
    updateOptions(newOptions) {
        const previouslySelected = new Set(this.selectedValues);
        
        this.allOptions = newOptions || [];
        this.filteredOptions = [...this.allOptions];
        
        // Keep only selections that still exist in the new options
        const availableValues = new Set(this.allOptions.map(opt => opt.value));
        this.selectedValues = new Set([...previouslySelected].filter(val => availableValues.has(val)));
        
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
            const noResultsText = this.filterType === 'country' ? 'No countries found' : 'No organizations found';
            this.optionsContainer.innerHTML = `<div class="no-results">${noResultsText}</div>`;
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
            const itemType = this.filterType === 'country' ? 'countries' : 'organizations';
            this.buttonText.innerHTML = `${count} ${itemType} selected`;
        }
    }

    updateHiddenInputs() {
        this.hiddenInputsContainer.innerHTML = '';
        this.selectedValues.forEach(value => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = this.filterType;
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

        // Add country selections
        const countryMultiselect = document.getElementById('country-multiselect');
        if (countryMultiselect && countryMultiselect.multiselectInstance) {
            countryMultiselect.multiselectInstance.selectedValues.forEach(value => {
                params.append('country', value);
            });
        }

        // Add organization selections
        const organizationMultiselect = document.getElementById('organization-multiselect');
        if (organizationMultiselect && organizationMultiselect.multiselectInstance) {
            organizationMultiselect.multiselectInstance.selectedValues.forEach(value => {
                params.append('organization', value);
            });
        }

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
    // Initialize country multiselect
    const countryContainer = document.getElementById('country-multiselect');
    if (countryContainer && window.countriesFromFlask && window.countriesFromFlask.length > 0) {
        new JobSearchMultiSelect(countryContainer, {
            preselected: window.selected_countries || [],
            placeholder: 'All Countries'
        });
    } else if (countryContainer) {
        console.log("Country multiselect container found but no country data available");
    }

    // Initialize organization multiselect
    const organizationContainer = document.getElementById('organization-multiselect');
    if (organizationContainer && window.organizationsFromFlask && window.organizationsFromFlask.length > 0) {
        new JobSearchMultiSelect(organizationContainer, {
            preselected: window.selected_organizations || [],
            placeholder: 'All Organizations'
        });
    } else if (organizationContainer) {
        console.log("Organization multiselect container found but no organization data available");
    }
});