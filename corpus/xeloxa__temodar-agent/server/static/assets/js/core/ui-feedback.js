(function() {
// Custom Confirm Implementation
window.showConfirm = function(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm-modal');
        const msgEl = document.getElementById('confirm-message');
        const btnYes = document.getElementById('btn-confirm-yes');
        const btnCancel = document.getElementById('btn-confirm-cancel');

        if (!modal || !msgEl || !btnYes || !btnCancel) {
            resolve(window.confirm(message));
            return;
        }

        msgEl.textContent = message;
        modal.classList.add('active');

        function handleYes() {
            cleanup();
            resolve(true);
        }

        function handleCancel() {
            cleanup();
            resolve(false);
        }

        function handleKeydown(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                handleCancel();
            }
        }

        function cleanup() {
            modal.classList.remove('active');
            btnYes.removeEventListener('click', handleYes);
            btnCancel.removeEventListener('click', handleCancel);
            modal.removeEventListener('click', handleOverlayClick);
            document.removeEventListener('keydown', handleKeydown);
        }

        function handleOverlayClick(event) {
            if (event.target === modal) {
                handleCancel();
            }
        }

        btnYes.addEventListener('click', handleYes);
        btnCancel.addEventListener('click', handleCancel);
        modal.addEventListener('click', handleOverlayClick);
        document.addEventListener('keydown', handleKeydown);
    });
};

window.showPrompt = function({ title = 'Enter text', message = '', defaultValue = '', confirmText = 'Save', cancelText = 'Cancel' } = {}) {
    return new Promise((resolve) => {
        const modal = document.getElementById('prompt-modal');
        const titleEl = document.getElementById('prompt-title');
        const msgEl = document.getElementById('prompt-message');
        const inputEl = document.getElementById('prompt-input');
        const btnYes = document.getElementById('btn-prompt-yes');
        const btnCancel = document.getElementById('btn-prompt-cancel');

        if (!modal || !titleEl || !msgEl || !inputEl || !btnYes || !btnCancel) {
            resolve(window.prompt(message || title, defaultValue));
            return;
        }

        titleEl.textContent = title;
        msgEl.textContent = message;
        inputEl.value = String(defaultValue ?? '');
        btnYes.textContent = confirmText;
        btnCancel.textContent = cancelText;
        modal.classList.add('active');

        function handleConfirm() {
            const value = String(inputEl.value || '');
            cleanup();
            resolve(value);
        }

        function handleCancel() {
            cleanup();
            resolve(null);
        }

        function handleKeydown(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                handleCancel();
            } else if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleConfirm();
            }
        }

        function handleOverlayClick(event) {
            if (event.target === modal) {
                handleCancel();
            }
        }

        function cleanup() {
            modal.classList.remove('active');
            btnYes.removeEventListener('click', handleConfirm);
            btnCancel.removeEventListener('click', handleCancel);
            modal.removeEventListener('click', handleOverlayClick);
            document.removeEventListener('keydown', handleKeydown);
            inputEl.removeEventListener('keydown', handleKeydown);
        }

        btnYes.addEventListener('click', handleConfirm);
        btnCancel.addEventListener('click', handleCancel);
        modal.addEventListener('click', handleOverlayClick);
        document.addEventListener('keydown', handleKeydown);
        inputEl.addEventListener('keydown', handleKeydown);

        requestAnimationFrame(() => {
            inputEl.focus();
            inputEl.select();
        });
    });
};

// Custom Toast Implementation
window.showToast = function(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');

    // Style logic
    let bg = '#141416';
    let color = '#fff';
    let border = '#333';

    if (type === 'success') { bg = 'rgba(0, 255, 157, 0.1)'; color = '#00FF9D'; border = 'rgba(0, 255, 157, 0.3)'; }
    if (type === 'error') { bg = 'rgba(255, 0, 85, 0.1)'; color = '#FF0055'; border = 'rgba(255, 0, 85, 0.3)'; }
    if (type === 'warn') { bg = 'rgba(255, 189, 46, 0.1)'; color = '#FFBD2E'; border = 'rgba(255, 189, 46, 0.3)'; }
    if (type === 'info') { bg = 'rgba(0, 243, 255, 0.1)'; color = '#00F3FF'; border = 'rgba(0, 243, 255, 0.3)'; }

    toast.style.cssText = `
        background: ${bg};
        color: ${color};
        border: 1px solid ${border};
        padding: 12px 15px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        min-width: 250px;
        max-width: 400px;
        animation: slideIn 0.3s ease-out forwards;
        display: flex;
        align-items: center;
        gap: 12px;
        backdrop-filter: blur(5px);
    `;

    let icon = 'ℹ';
    if (type === 'success') icon = '✓';
    if (type === 'error') icon = '✕';
    if (type === 'warn') icon = '⚠';

    toast.innerHTML = `<span style="font-weight: bold; font-size: 14px;">${icon}</span> <span style="line-height: 1.4;">${escapeHtml(message)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add animation keyframes
if (!document.getElementById('toast-style')) {
    const style = document.createElement('style');
    style.id = 'toast-style';
    style.innerHTML = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
}


})();
