// --- Excel Summary panel bootstrap (safe to re-define) ---
(function() {
  const tableBody = document.getElementById('cost-grid-table-body');
  if (!tableBody) return;

  const triggerRefresh = () => {
    document.dispatchEvent(new CustomEvent('cost-grid:refresh'));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', triggerRefresh);
  } else {
    triggerRefresh();
  }
})();
