# Gates — Phase 1
- Ensure `python run.py` binds :5580/:5581 and logs both.
- Fix CORS preflight for Origin http://localhost:5580 with proper methods/headers.
- Make `/api/health` return 200 JSON and include `trace_id` in logs.
- Frontend static paths correct (no 404 on /assets/app.css or /app.js).