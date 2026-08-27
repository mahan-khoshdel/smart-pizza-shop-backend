# Project Structure

## Purpose

This document explains the directory structure of the backend repository and the responsibility of each major component.

## Root Structure

```text
smart-pizza-shop-backend/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── docs/
│   ├── proposal/
│   └── project-structure.md
│
├── app/
│   ├── main.py
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── api/
│   ├── reports/
│   └── utils/
│
├── database/
├── migrations/
└── tests/
```

## Directory Responsibilities

### `app/`

Main Python application package.

### `app/core/`

Application-wide configuration and infrastructure concerns.

Planned responsibilities:

- Environment configuration
- Security configuration
- Authentication helpers
- Shared dependencies
- Application-level settings

### `app/database/`

Database integration inside the Python application.

Current files:

```text
app/database/
├── __init__.py
├── connection.py
├── base.py
└── models/
```

Responsibilities:

- SQLAlchemy engine
- Database sessions
- Declarative Base
- SQLAlchemy model registration

### `app/database/models/`

SQLAlchemy ORM models representing the application's database tables.

The first models are expected to include:

- Tenant
- Branch
- User

Later models will cover customers, products, recipes, inventory, purchasing, orders, payments and other business entities.

### `app/models/`

Reserved application/domain model space.

This directory is currently kept minimal while the project establishes its SQLAlchemy model architecture.

### `app/schemas/`

Pydantic request and response schemas for FastAPI.

Examples:

- Create customer request
- Product response
- Order creation request
- Inventory response

Schemas are kept separate from SQLAlchemy models.

### `app/repositories/`

Database access layer.

Repositories will encapsulate data-access operations and keep raw persistence details away from business logic.

### `app/services/`

Business logic layer.

Examples:

- Order service
- Inventory service
- Purchase service
- Recommendation service
- Restocking service
- Analytics service
- Report service

Complex business rules should live here rather than inside API routes.

### `app/api/`

FastAPI routes and API organization.

The API will use versioned endpoints such as:

```text
/api/v1/...
```

### `app/reports/`

Business report generation and reporting-related functionality.

### `app/utils/`

Small shared utilities that do not belong to a specific business domain.

### `database/`

Root-level PostgreSQL-specific assets.

This directory is intentionally separate from `app/database/`.

Potential future contents:

```text
database/
├── rls/
├── functions/
├── triggers/
└── seed/
```

These are for PostgreSQL-specific SQL and database assets, not the main ORM table definitions.

### `migrations/`

Alembic migration history.

Database schema changes will be versioned here rather than manually changing production databases.

### `tests/`

Automated tests for the backend.

Planned test layers include:

- API tests
- Service tests
- Repository/database tests
- Authentication tests
- Multi-tenant isolation tests
- Inventory and order workflow tests

## Architecture Flow

```text
Frontend
    |
    | HTTP / REST
    v
FastAPI Route
    |
    v
Pydantic Schema
    |
    v
Service
    |
    v
Repository
    |
    v
SQLAlchemy
    |
    v
Psycopg
    |
    v
PostgreSQL
```

## Multi-Tenant Data Flow

```text
Tenant
   |
   +---- Branch
   |
   +---- Users
   |
   +---- Products
   |
   +---- Customers
   |
   +---- Orders
   |
   +---- Inventory
   |
   +---- Purchases
   |
   +---- Reports
```

Tenant-specific records will carry the appropriate tenant context, and branch-level records will also carry branch context where required.

PostgreSQL Row-Level Security will provide an additional database-level isolation layer.

## Documentation

The repository will maintain:

- README
- Project structure documentation
- Database architecture documentation
- API documentation
- OpenAPI documentation
- Meaningful Python docstrings
