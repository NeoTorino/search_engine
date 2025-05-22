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
        
        this.allOptions = [];
        this.filteredOptions = [];
        this.selectedValues = new Set(options.preselected || []);
        this.isOpen = false;
        this.placeholder = options.placeholder || 'All Countries';
        
        this.init();
    }
    
    async init() {
        await this.loadCountries();
        this.bindEvents();
        this.updateButtonText();
        this.updateHiddenInputs();
    }
    
    async loadCountries() {
        try {
            // Try to use countries passed from Flask first
            if (window.countriesFromFlask && window.countriesFromFlask.length > 0) {
                this.allOptions = window.countriesFromFlask;
            } else {
                // Fallback to API call
                const response = await fetch('/api/countries');
                this.allOptions = await response.json();
            }
            
            this.filteredOptions = [...this.allOptions];
            this.renderOptions();
        } catch (error) {
            console.error('Error loading countries:', error);
            this.optionsContainer.innerHTML = '<div class="no-results">Error loading countries</div>';
        }
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
                
                // Trigger search immediately when selection changes
                this.triggerSearch();
            });
        });
    }
    
    filterOptions(searchTerm) {
        const filtered = this.filteredOptions.filter(option => 
            option.label.toLowerCase().includes(searchTerm.toLowerCase())
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
            this.buttonText.innerHTML = `${count} countries selected <span class="selected-count">${count}</span>`;
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
        // If you have a search form, submit it
        const searchForm = document.querySelector('form');
        if (searchForm) {
            searchForm.submit();
        } else {
            // Or trigger a custom search function
            window.location.search = this.buildQueryString();
        }
    }
    
    buildQueryString() {
        const params = new URLSearchParams(window.location.search);
        
        // Remove existing country parameters
        params.delete('country');
        
        // Add selected countries
        this.selectedValues.forEach(value => {
            params.append('country', value);
        });
        
        return params.toString();
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
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
        this.renderOptions();
    }
    
    setSelectedValues(values) {
        this.selectedValues = new Set(values);
        this.renderOptions();
        this.updateButtonText();
        this.updateHiddenInputs();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const preselectedCountries = window.selected_countries || [];

    const countryMultiSelect = new JobSearchMultiSelect(
        document.getElementById('country-multiselect'),
        {
            preselected: preselectedCountries,
            placeholder: 'All Countries'
        }
    );
});