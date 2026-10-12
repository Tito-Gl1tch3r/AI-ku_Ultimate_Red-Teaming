(function() {
    window.setDashboardMetric = function(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = String(value);
    };

    window.setChartCaption = function(id, text) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = text;
    };

    window.resetDashboardChartCaptions = function() {
        window.setChartCaption('dashboard-risk-caption', 'Click bar to open scan');
        window.setChartCaption('dashboard-trend-caption', 'Click bar to open scan');
    };

    window.bindChartHover = function(containerId, captionId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const handleEnter = (event) => {
            const point = event.target.closest('.chart-point[data-caption]');
            if (!point || !container.contains(point)) return;
            window.setChartCaption(captionId, point.getAttribute('data-caption') || '');
        };

        const handleLeave = () => {
            window.resetDashboardChartCaptions();
        };

        container.addEventListener('mouseover', handleEnter);
        container.addEventListener('focusin', handleEnter);
        container.addEventListener('mouseleave', handleLeave);
        container.addEventListener('focusout', handleLeave);
    };
})();
