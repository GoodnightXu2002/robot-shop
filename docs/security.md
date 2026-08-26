# Security Notes

## Completed Hardening

### Safe login redirects

Login redirects now validate the `next` parameter before redirecting users after authentication. Only site-local relative paths such as `/cart` are allowed.

Blocked examples include:

- `https://evil.com`
- `http://example.com`
- `//evil.com`

Unsafe `next` values fall back to the normal default pages:

- Regular users: `/user/center`
- Admin users: `/admin`

### Required production SECRET_KEY

Production configuration now requires `SECRET_KEY` to be set through the environment. If the application is started with `ProductionConfig` and `SECRET_KEY` is missing or empty, startup fails clearly instead of silently using an unsafe value.

Development and testing remain convenient:

- Development can still use the local default secret key.
- Testing can still create the app without a production secret.

### Debug mode from configuration

Direct `app.py` startup no longer hard-codes `debug=True`. The debug flag is derived from the active Flask configuration:

- Development: debug can be enabled.
- Production: debug is disabled.

### AI API rate limiting

The AI chat endpoints now use local in-memory rate limiting before normal AI request handling:

- `/api/ai-assistant/chat`
- `/api/ai-chat`

Rate limit identity rules:

- Anonymous users are limited by IP address.
- Authenticated users are limited by `user_id`.

Default configuration:

- `AI_RATE_LIMIT_WINDOW_SECONDS = 60`
- `AI_RATE_LIMIT_ANON_MAX = 10`
- `AI_RATE_LIMIT_USER_MAX = 20`

Requests over the configured limit return HTTP `429` with a JSON error response.

This is intentionally a lightweight local-memory implementation for the current Flask prototype. A production deployment can later migrate the same policy to Flask-Limiter with Redis or another shared backend, so limits work correctly across multiple processes or servers.

## Pending Security Work

### CSRF protection

The project still has many POST-based forms for login, registration, cart, orders, admin actions, consultations, appointments, and reviews. A later step should introduce CSRF protection and update templates and tests carefully.

### Field length and URL validation

Form fields should receive stricter validation for length, numeric ranges, and URL formats. Product image/video/source URLs, consultation text, appointment data, and admin product fields are good candidates.

### Permission strategy layer

Admin routes currently use consistent `admin_required` protection, with tests around major admin modules. A later phase can introduce a clearer permission strategy layer to make future admin route additions harder to misconfigure.
