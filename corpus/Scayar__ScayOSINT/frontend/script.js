// ScayOSINT - Clean JavaScript Implementation
console.log('🚀 ScayOSINT JavaScript loaded');

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM loaded, initializing ScayOSINT...');
    
    // Initialize the app
    initializeScayOSINT();
});

function initializeScayOSINT() {
    console.log('🔧 Initializing ScayOSINT...');
    
    // Set up scan form
    const scanForm = document.getElementById('scan-form');
    if (scanForm) {
        console.log('✅ Found scan form, setting up event listener');
        scanForm.addEventListener('submit', handleScan);
        console.log('🔗 Scan form event listener attached successfully');
    } else {
        console.error('❌ Scan form not found!');
    }
    
    // Set up settings form
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        console.log('✅ Found settings form, setting up event listener');
        settingsForm.addEventListener('submit', handleSettings);
    } else {
        console.error('❌ Settings form not found!');
    }
    
    // Set up navigation
    setupNavigation();
    
    // Load configuration
    loadConfiguration();
    
    console.log('✅ ScayOSINT initialized successfully');
}

function setupNavigation() {
    console.log('🔗 Setting up navigation...');
    
    // Navigation links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth' });
                
                // Update active nav link
                document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });
}

async function handleScan(e) {
    e.preventDefault();
    console.log('🔍 Scan form submitted');
    
    const email = document.getElementById('email').value.trim();
    console.log('📧 Email:', email);
    
    if (!email) {
        showToast('Please enter an email address', 'error');
        return;
    }
    
    // Show loading state
    showLoading(true);
    updateScanButton('Scanning...', true);
    
    try {
        console.log('🌐 Sending scan request to backend...');
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📊 Scan results:', data);
        
        renderResults(data);
        showToast('Scan completed successfully!', 'success');
        
    } catch (error) {
        console.error('❌ Scan error:', error);
        renderError('Failed to perform scan. Please try again.');
        showToast('Scan failed. Please check your connection.', 'error');
    } finally {
        showLoading(false);
        updateScanButton('Launch Intelligence Scan', false);
    }
}

async function handleSettings(e) {
    e.preventDefault();
    console.log('⚙️ Settings form submitted');
    
    const config = {
        services: {
            email_rep: { 
                api_key: document.getElementById('emailrep-key').value, 
                enabled: true 
            },
            haveibeenpwned: { 
                api_key: document.getElementById('hibp-key').value, 
                enabled: true 
            },
            breach_directory: { 
                api_key: document.getElementById('breachdirectory-key').value, 
                enabled: true 
            },
            intelx: { 
                api_key: document.getElementById('intelx-key').value, 
                enabled: true 
            },
            spotify: { enabled: true },
            twitter: { enabled: true },
            instagram: { enabled: true }
        }
    };
    
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ config })
        });
        
        if (response.ok) {
            showToast('Configuration saved successfully!', 'success');
        } else {
            throw new Error('Failed to save configuration');
        }
    } catch (error) {
        console.error('❌ Settings error:', error);
        showToast('Failed to save configuration', 'error');
    }
}

function renderResults(data) {
    console.log('🎨 Rendering results...');
    const resultsDiv = document.getElementById('results');
    
    if (!data || !data.results) {
        resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
        return;
    }
    
    let html = `
        <div class="results-header">
            <h3>Scan Results</h3>
            <div class="scan-info">
                <span><strong>Email:</strong> ${data.email}</span>
                <span><strong>Time:</strong> ${new Date(data.timestamp).toLocaleString()}</span>
            </div>
        </div>
    `;
    
    for (const [service, result] of Object.entries(data.results)) {
        const serviceName = formatServiceName(service);
        const serviceIcon = getServiceIcon(service);
        
        html += `
            <div class="result-card ${result.success ? 'success' : 'error'}">
                <div class="result-header">
                    <i class="${serviceIcon}"></i>
                    <span class="service-name">${serviceName}</span>
                    <span class="status-badge ${result.success ? 'success' : 'error'}">
                        ${result.success ? '✓ Success' : '✗ Error'}
                    </span>
                </div>
                <div class="result-content">
                    ${result.success ? 
                        `<pre>${JSON.stringify(result.data, null, 2)}</pre>` : 
                        `<span class="error-message">${result.error || 'Unknown error'}</span>`
                    }
                </div>
            </div>
        `;
    }
    
    resultsDiv.innerHTML = html;
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderError(message) {
    console.log('❌ Rendering error:', message);
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `
        <div class="error-card">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Scan Failed</h3>
            <p>${message}</p>
        </div>
    `;
}

function getServiceIcon(service) {
    const icons = {
        email_rep: 'fas fa-shield-alt',
        haveibeenpwned: 'fas fa-exclamation-triangle',
        breach_directory: 'fas fa-database',
        intelx: 'fas fa-search',
        spotify: 'fab fa-spotify',
        twitter: 'fab fa-twitter',
        instagram: 'fab fa-instagram'
    };
    return icons[service] || 'fas fa-cog';
}

function formatServiceName(service) {
    return service.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

async function loadConfiguration() {
    console.log('⚙️ Loading configuration...');
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        const config = data.config.services;
        
        // Populate settings form
        document.getElementById('emailrep-key').value = config.email_rep.api_key || '';
        document.getElementById('hibp-key').value = config.haveibeenpwned.api_key || '';
        document.getElementById('breachdirectory-key').value = config.breach_directory.api_key || '';
        document.getElementById('intelx-key').value = config.intelx.api_key || '';
        
        console.log('✅ Configuration loaded');
    } catch (error) {
        console.error('❌ Failed to load configuration:', error);
    }
}

function showLoading(show) {
    console.log('🔄 Setting loading state:', show);
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

function updateScanButton(text, loading = false) {
    console.log('🔘 Updating scan button:', text, loading);
    const button = document.querySelector('.scan-button');
    const buttonText = button.querySelector('.button-text');
    const buttonIcon = button.querySelector('.button-icon');
    
    buttonText.textContent = text;
    
    if (loading) {
        button.disabled = true;
        button.classList.add('loading');
        buttonIcon.className = 'fas fa-spinner fa-spin button-icon';
    } else {
        button.disabled = false;
        button.classList.remove('loading');
        buttonIcon.className = 'fas fa-rocket button-icon';
    }
}

function showToast(message, type = 'info') {
    console.log('🍞 Showing toast:', message, type);
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.error('❌ Toast container not found');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${getToastIcon(type)}"></i>
        <span>${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

function getToastIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Handle history button click
document.addEventListener('click', function(e) {
    if (e.target && e.target.textContent.includes('History')) {
        console.log('📚 History button clicked');
        loadHistory();
    }
});

async function loadHistory() {
    console.log('📚 Loading history...');
    try {
        const response = await fetch('/api/history');
        const history = await response.json();
        renderHistory(history);
    } catch (error) {
        console.error('❌ Failed to load history:', error);
    }
}

function renderHistory(history) {
    console.log('📚 Rendering history...');
    const historyList = document.getElementById('history-list');
    
    if (!history || history.length === 0) {
        historyList.innerHTML = '<div class="no-history">No scan history found</div>';
        return;
    }
    
    let html = '';
    history.reverse().forEach(item => {
        html += `
            <div class="history-item">
                <div class="history-header">
                    <span class="email">${item.email}</span>
                    <span class="timestamp">${new Date(item.timestamp).toLocaleString()}</span>
                </div>
                <div class="history-services">
                    ${Object.entries(item.results).map(([service, result]) => `
                        <span class="service-status ${result.success ? 'success' : 'error'}">
                            ${formatServiceName(service)}: ${result.success ? '✓' : '✗'}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    });
    
    historyList.innerHTML = html;
}

console.log('✅ ScayOSINT JavaScript file loaded completely'); 