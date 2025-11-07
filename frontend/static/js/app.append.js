// --- Excel Summary panel bootstrap (safe to re-define) ---
(function() {
  // If the HTML doesn't include the 3rd panel, nothing happens.
  const ok = document.getElementById('excel-summary-body');
  if (!ok) return;
  // DOMContentLoaded handler is inside index.html inline script,
  // but keep this here as a safety reload if app.js is loaded before body end.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      const refresh = document.getElementById('excel-refresh');
      if (refresh) refresh.click();
    });
  } else {
    const refresh = document.getElementById('excel-refresh');
    if (refresh) refresh.click();
  }
})();
