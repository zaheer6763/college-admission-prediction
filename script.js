// Global variables
let resultsData = null;

// DOM Elements
document.addEventListener('DOMContentLoaded', function() {
    // Load data on page load
    loadData();

    // Add event listeners
    document.getElementById('predict-btn').addEventListener('click', predictColleges);
    document.getElementById('download-btn').addEventListener('click', downloadCSV);

    // Add input listeners for validation
    document.getElementById('rank').addEventListener('input', validateRange);
    document.getElementById('range').addEventListener('input', validateRange);
});

// Validate range against rank
function validateRange() {
    const rank = parseInt(document.getElementById('rank').value);
    const range = parseInt(document.getElementById('range').value);
    const infoDiv = document.getElementById('range-warning');
    const messageSpan = document.getElementById('warning-message');

    if (rank && range >= 0) {
        if (range > rank && range > 0) {
            infoDiv.style.display = 'flex';
            messageSpan.textContent = `Range (${range}) exceeds rank (${rank}). Showing colleges with cutoff ≤ ${rank}`;
        } else if (range === 0) {
            infoDiv.style.display = 'flex';
            messageSpan.textContent = `Showing all colleges with cutoff ≤ ${rank}`;
        } else {
            infoDiv.style.display = 'none';
        }
    } else {
        infoDiv.style.display = 'none';
    }
}

// Load data from server
async function loadData() {
    showLoading(true);

    try {
        const response = await fetch('/api/load-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            showToast('Data loaded successfully', 'success');
            renderCategories(data.categories);
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('Error loading data: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Render category options
function renderCategories(categories) {
    const container = document.getElementById('category-container');

    if (!categories || categories.length === 0) {
        container.innerHTML = '<div class="loading-message">No categories available</div>';
        return;
    }

    let html = '';
    categories.forEach(category => {
        const isChecked = category === 'OC' ? 'checked' : '';
        html += `
            <label class="option-card">
                <input type="radio" name="category" value="${category}" ${isChecked}>
                <div class="option-content">
                    <i class="fas fa-tag"></i>
                    <span>${category}</span>
                </div>
            </label>
        `;
    });

    container.innerHTML = html;
}

// Predict colleges
async function predictColleges() {
    // Get form values
    const rank = parseInt(document.getElementById('rank').value);
    let range = parseInt(document.getElementById('range').value);
    const category = document.querySelector('input[name="category"]:checked')?.value;
    const gender = document.querySelector('input[name="gender"]:checked')?.value;

    // Validate inputs
    if (!rank) {
        showToast('Please enter your rank', 'error');
        document.getElementById('rank').focus();
        return;
    }

    if (rank < 0) {
        showToast('Rank cannot be negative', 'error');
        return;
    }

    if (range < 0) {
        showToast('Range cannot be negative', 'error');
        return;
    }

    // Auto-adjust range if greater than rank
    if (range > rank && range > 0) {
        range = rank;
        document.getElementById('range').value = rank;
    }

    if (!category) {
        showToast('Please select a category', 'error');
        return;
    }

    // Show loading
    showLoading(true);

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rank, range, category, gender })
        });

        const data = await response.json();

        if (data.success) {
            resultsData = data;
            displayResults(data);
            showToast(`Found ${data.total} matching colleges`, 'success');
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('Error predicting: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Display results
function displayResults(data) {
    // Show results section
    const resultsSection = document.getElementById('results-section');
    resultsSection.style.display = 'block';

    // Scroll to results smoothly
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);

    // Update badges
    document.getElementById('rank-badge').innerHTML = `<i class="fas fa-hashtag"></i> Rank: ${data.rank.toLocaleString()}`;
    document.getElementById('range-badge').innerHTML = `<i class="fas fa-chart-line"></i> ${data.range_display}`;
    document.getElementById('category-badge').innerHTML = `<i class="fas fa-tag"></i> ${data.category}`;
    document.getElementById('gender-badge').innerHTML = `<i class="fas fa-${data.gender === 'BOYS' ? 'male' : 'female'}"></i> ${data.gender}`;

    // Update summary cards with original colors
    const results = data.results;
    const total = results.length;
    const excellent = results.filter(r => r.chance >= 80).length;
    const good = results.filter(r => r.chance >= 60 && r.chance < 80).length;
    const moderate = results.filter(r => r.chance >= 40 && r.chance < 60).length;
    const low = results.filter(r => r.chance < 40).length;

    animateValue('total-matches', 0, total, 500);
    animateValue('excellent-count', 0, excellent, 500);
    animateValue('good-count', 0, good, 500);
    animateValue('moderate-count', 0, moderate, 500);
    animateValue('low-count', 0, low, 500);

    // Update chart - Original colors preserved
    if (data.plot) {
        document.getElementById('chart-wrapper').innerHTML = `<img src="data:image/png;base64,${data.plot}" alt="Recommendations Chart" style="max-width: 100%; max-height: 100%; width: auto; height: auto; object-fit: contain;">`;
    }

    // Update table
    renderTable(results);

    // Update table info
    document.getElementById('table-info').innerHTML = `Showing ${total} colleges • Sorted by admission chance`;
}

// Animate counting numbers
function animateValue(elementId, start, end, duration) {
    const element = document.getElementById(elementId);
    const range = end - start;
    const increment = range / (duration / 10);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if (current >= end) {
            element.textContent = end;
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, 10);
}

// Render table with original colors for chance badges
function renderTable(results) {
    const tbody = document.getElementById('table-body');
    let html = '';

    results.forEach((row, index) => {
        let badgeStyle = '';
        let badgeClass = '';

        // Original colors for admission chance
        if (row.chance >= 80) {
            badgeStyle = 'background: #10B98120; color: #10B981; border: 1px solid #10B981; font-weight: 600;';
            badgeClass = 'chance-excellent';
        } else if (row.chance >= 60) {
            badgeStyle = 'background: #F59E0B20; color: #F59E0B; border: 1px solid #F59E0B; font-weight: 600;';
            badgeClass = 'chance-good';
        } else if (row.chance >= 40) {
            badgeStyle = 'background: #8B5CF620; color: #8B5CF6; border: 1px solid #8B5CF6; font-weight: 600;';
            badgeClass = 'chance-moderate';
        } else {
            badgeStyle = 'background: #6B728020; color: #6B7280; border: 1px solid #6B7280; font-weight: 600;';
            badgeClass = 'chance-low';
        }

        html += `
            <tr>
                <td>${index + 1}</td>
                <td><strong>${row.branch}</strong></td>
                <td>${row.cutoff.toLocaleString()}</td>
                <td>
                    <span class="chance-badge ${badgeClass}" style="${badgeStyle}">
                        ${row.chance}%
                    </span>
                </td>
                <td>${row.institute}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// Download CSV
async function downloadCSV() {
    if (!resultsData) {
        showToast('No data to download', 'error');
        return;
    }

    // Show loading on button
    const downloadBtn = document.getElementById('download-btn');
    const originalText = downloadBtn.innerHTML;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
    downloadBtn.disabled = true;

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(resultsData)
        });

        const data = await response.json();

        if (data.success) {
            // Create download link
            const blob = new Blob([data.csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `TSEAMCET_Predictions_Rank${resultsData.rank}_${resultsData.category}_${resultsData.gender}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showToast('CSV downloaded successfully', 'success');
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('Error downloading: ' + error.message, 'error');
    } finally {
        // Restore button
        downloadBtn.innerHTML = originalText;
        downloadBtn.disabled = false;
    }
}

// Show loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    } else {
        overlay.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastIcon = toast.querySelector('.toast-icon');
    const toastMessage = toast.querySelector('.toast-message');

    // Set icon based on type
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    else if (type === 'error') icon = 'fa-exclamation-circle';
    else if (type === 'warning') icon = 'fa-exclamation-triangle';

    toastIcon.className = `fas ${icon} toast-icon`;
    toastMessage.textContent = message;

    // Show toast
    toast.classList.add('show');

    // Auto hide after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Add keyboard support for Enter key
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        const activeElement = document.activeElement;
        if (activeElement.classList.contains('modern-input')) {
            predictColleges();
        }
    }
});

// Export functions for testing if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateRange,
        renderCategories,
        predictColleges,
        displayResults,
        animateValue,
        renderTable,
        downloadCSV,
        showLoading,
        showToast
    };
}