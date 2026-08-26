# Robot Shop Architecture

## Overview

Robot Shop is a Flask-based robot e-commerce demo application. The current codebase has been refactored from a large single-file `app.py` into focused Blueprint and service modules while keeping the original URLs, endpoints, templates, and database behavior unchanged.

## Technology Stack

- Flask: application factory, routing, request handling, and templates.
- Bootstrap: frontend layout and UI styling in the existing templates.
- SQLite: local development and test database engine.
- Flask-SQLAlchemy: ORM layer and database session management.
- pytest: smoke tests and lightweight flow tests.

## Current Project Structure

```text
robot_shop/
  app.py
  config.py
  models.py
  ai_assistant_service.py
  blueprints/
  services/
  utils/
  tests/
  scripts/
  templates/
  static/
  docs/
```

## app.py Responsibilities

`app.py` is now the application entry point rather than the main business module. It is responsible for:

- Creating the Flask app with `create_app()`.
- Loading configuration from `config.py`.
- Initializing `db` and `login_manager`.
- Defining the `admin_required` permission wrapper.
- Registering all Blueprint modules.
- Injecting global template values such as cart count and unread notification counts.
- Registering the `403` error handler.
- Exposing `init_database` for local startup and tests.
- Running the local development server when executed directly.

## Blueprints

- `public.py`: public storefront pages, including home, product list, and product detail.
- `auth.py`: registration, login, logout, and user center.
- `cart.py`: shopping cart operations and wishlist operations.
- `orders.py`: foreground order creation, order list/detail, payment, payment confirmation, and cart checkout.
- `reviews.py`: foreground product review submission.
- `consultations.py`: foreground consultation list/submission and legacy `/consultation` redirect.
- `appointments.py`: foreground service appointment list/submission.
- `notifications.py`: user messages, message detail, mark-as-read actions, and admin message pages.
- `ai.py`: AI assistant admin page and chat API endpoints.
- `admin_dashboard.py`: admin dashboard and statistics page.
- `admin_products.py`: admin product list, create, edit, and delete actions.
- `admin_orders.py`: admin order list and order status/logistics update.
- `admin_users.py`: admin user list.
- `admin_consultations.py`: admin consultation list, status update, and reply handling.
- `admin_appointments.py`: admin appointment list, status update, and process note handling.
- `admin_reviews.py`: admin review list and review deletion.

All Blueprint registrations preserve the existing URL paths and endpoint names so existing `url_for(...)` calls continue to work.

## Services

- `services/notifications.py`: contains `notify_user` and `notify_admin`, preserving the original notification creation logic.
- `services/database.py`: contains database compatibility checks and seed data setup:
  - `ensure_schema`
  - `add_columns`
  - `init_database`
  - `seed_users`
  - `seed_product_data`
  - `seed_demo_records`
  - `seed_products`

## Tests

The `tests/` directory provides a lightweight protection net using a temporary SQLite test database. Current coverage includes:

- Smoke checks for home, products, login, and admin access protection.
- Login flows for regular users and admins.
- Product detail access and AI assistant fallback behavior.
- Cart and wishlist access and mutation flows.
- Foreground review, consultation, legacy consultation redirect, and appointment flows.
- Order creation, generated `Order` records, stock changes, payment confirmation, and login protection.
- Admin dashboard and statistics access.
- Admin product, order, user, consultation, appointment, and review management.
- Permission checks for unauthenticated users, regular users, and admin users.

## Refactoring Results

- Split the former large `app.py` into focused Blueprint modules.
- Preserved all existing URLs and endpoint names during route extraction.
- Added a pytest-based test protection net for core user and admin workflows.
- Separated configuration into `config.py`.
- Moved notification helpers into `services/notifications.py`.
- Moved database initialization and seed logic into `services/database.py`.
- Replaced legacy SQLAlchemy `Query.get()` paths with `db.session.get(...)` to remove warnings.

## Current Boundaries

- `models.py` remains the central model definition file.
- Database migrations are still handled by the existing compatibility logic, not Flask-Migrate.
- Business rules such as order stock deduction, sales increments, payment state updates, notifications, and permission checks remain in the existing route/service flow.
- Templates and static assets remain unchanged by the refactor.
