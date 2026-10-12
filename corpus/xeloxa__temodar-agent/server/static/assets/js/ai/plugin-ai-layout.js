(function() {
    function updatePluginAiExpandButton(isExpanded) {
        const button = document.getElementById('plugin-ai-expand-btn');
        if (!button) return;
        button.setAttribute('aria-label', isExpanded ? 'Collapse AI chat' : 'Expand AI chat');
        button.setAttribute('title', isExpanded ? 'Collapse AI chat' : 'Expand AI chat');
        button.classList.toggle('is-expanded', !!isExpanded);
        button.innerHTML = isExpanded
            ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 14 10 14 10 20"></polyline><polyline points="20 10 14 10 14 4"></polyline><line x1="14" y1="10" x2="21" y2="3"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>`
            : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>`;
    }

    function setPluginAiExpanded(expanded) {
        const layout = document.querySelector('#plugin-detail-view .plugin-detail-layout');
        if (!layout) return;
        layout.classList.toggle('is-ai-expanded', !!expanded);
        updatePluginAiExpandButton(!!expanded);
    }

    function togglePluginAiExpanded() {
        const layout = document.querySelector('#plugin-detail-view .plugin-detail-layout');
        if (!layout) return;
        setPluginAiExpanded(!layout.classList.contains('is-ai-expanded'));
    }

    function bindPluginAiLayoutEvents() {
        const button = document.getElementById('plugin-ai-expand-btn');
        if (button && !button.dataset.bound) {
            button.addEventListener('click', () => {
                togglePluginAiExpanded();
            });
            button.dataset.bound = '1';
        }
        updatePluginAiExpandButton(false);
    }

    window.setPluginAiExpanded = setPluginAiExpanded;
    window.togglePluginAiExpanded = togglePluginAiExpanded;
    window.bindPluginAiLayoutEvents = bindPluginAiLayoutEvents;
})();
