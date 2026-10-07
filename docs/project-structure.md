# Project Structure

## Purpose

This document explains the structure of the backend repository, the responsibility of each major component, and the architectural boundaries used by the project.

The project follows a layered backend architecture designed for:

* Maintainability
* Testability
* Tenant isolation
* Clear separation of responsibilities
* Future SaaS expansion

---

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

---

## Directory Responsibilities

### `app/`

The main Python application package.

It contains the API, business logic, persistence layer, database models, schemas, shared infrastructure, and application utilities.

---

### `app/core/`

Application-wide infrastructure and shared backend concerns.

Responsibilities include:

* Environment configuration
* Application settings
* Authentication helpers
* Shared dependencies
* Security-related infrastructure
* Common application-level configuration

---

### `app/database/`

Database integration inside the Python application.

Current structure:

```text
app/database/
├── __init__.py
├── connection.py
├── base.py
└── models/
```

Responsibilities include:

* SQLAlchemy engine configuration
* Database session management
* Declarative Base
* SQLAlchemy model registration
* Database-related application infrastructure

---

### `app/database/models/`

SQLAlchemy ORM models representing database entities.

This layer contains the persistence models used by the application.

The project currently includes models covering core business areas such as:

* Tenants
* Branches
* Users
* Customers
* Customer addresses
* Products and product variants
* Orders and order items
* Order status history
* Recipes
* Inventory-related entities
* Other supporting business entities

The model layer is responsible for database structure and relationships, while business rules remain in the service layer.

---

### `app/models/`

Reserved space for application or domain models that are not direct SQLAlchemy persistence models.

The project currently keeps the main database entities under:

```text
app/database/models/
```

This separation keeps persistence concerns distinct from future domain-level abstractions.

---

### `app/schemas/`

Pydantic request and response schemas used by FastAPI.

Examples include:

* Customer creation and update schemas
* Product schemas
* Order creation schemas
* Order response schemas
* Order status update schemas
* Inventory-related schemas

Schemas are intentionally separated from SQLAlchemy ORM models.

This prevents API contracts from becoming tightly coupled to the database representation.

---

### `app/repositories/`

Database access layer.

Repositories encapsulate persistence operations and keep direct SQLAlchemy query logic away from the business logic.

Responsibilities include:

* Creating records
* Retrieving records
* Updating records
* Filtering and ordering
* Pagination
* Tenant-scoped queries
* Database-specific persistence operations

Repositories should not contain API-specific behavior.

---

### `app/services/`

Business logic layer.

Services contain application and business rules that should not live inside FastAPI routes.

Examples include:

* Order creation
* Order status transitions
* Order cancellation
* Kitchen workflow
* Inventory consumption
* Recipe ingredient requirements
* Customer address validation
* Product validation
* Tenant-aware business operations
* Future purchasing, analytics, reporting and recommendation logic

Complex business rules are centralized here so that they can be reused by different API endpoints and tested independently.

---

### `app/api/`

FastAPI routes and API organization.

The project uses versioned API endpoints:

```text
/api/v1/...
```

The API layer is responsible for:

* HTTP request handling
* Request validation through Pydantic schemas
* Authentication dependency integration
* Calling service-layer operations
* Returning API responses
* HTTP-specific error handling

Business logic should remain outside the route handlers whenever possible.

---

### `app/reports/`

Reporting-related functionality.

This layer is reserved for business reports and reporting-oriented functionality such as future:

* Daily business summaries
* Sales reports
* Inventory reports
* Supplier performance reports
* Operational analytics

---

### `app/utils/`

Small reusable utilities that do not belong to a specific business domain.

Utilities should remain focused and should not contain major business rules.

---

## PostgreSQL Database Assets

### `database/`

Root-level PostgreSQL-specific assets.

This directory is intentionally separate from:

```text
app/database/
```

because the responsibilities are different.

`app/database/` contains Python/SQLAlchemy database integration.

`database/` is intended for PostgreSQL-specific SQL assets.

Possible structure:

```text
database/
├── rls/
├── functions/
├── triggers/
└── seed/
```

These assets can contain functionality such as:

* Row-Level Security policies
* PostgreSQL functions
* Database triggers
* Seed data
* Other PostgreSQL-specific definitions

---

## `migrations/`

Alembic migration history.

Database schema changes are versioned through migrations instead of being manually applied to production databases.

This allows the database schema to evolve in a controlled and reproducible way.

---

## `tests/`

Automated backend test suite.

The test suite covers multiple architectural layers.

### API / Integration Tests

Validate real HTTP behavior through FastAPI endpoints.

Examples include:

* Order creation
* Order listing
* Order filtering
* Pagination
* Order status updates
* Status history
* Customer addresses
* Delivery validation
* Product validation
* Tenant isolation
* Missing-resource behavior

### Service Tests

Validate business rules independently from the HTTP layer.

Examples include:

* Order lifecycle rules
* Status transition validation
* Kitchen capacity
* Inventory consumption
* Cancellation rules
* Rollback behavior
* Business validation

### Repository Tests

Validate database-access behavior.

Examples include:

* Tenant-scoped queries
* Filtering
* Ordering
* Pagination
* Record lookup
* Not-found behavior

### Multi-Tenant Isolation Tests

Validate that data belonging to one tenant cannot be accessed or modified through another tenant's context.

Tenant isolation is treated as a core architectural requirement.

### Workflow Tests

Validate complete business workflows across multiple layers.

Examples include:

```text
REGISTERED
    ↓
PREPARING
    ↓
READY
    ↓
COMPLETED
```

and cancellation workflows such as:

```text
REGISTERED → CANCELLED
PREPARING  → CANCELLED
READY      → CANCELLED
```

These tests also verify inventory-consumption behavior and transactional rollback where applicable.

---

## Architecture Flow

The main request flow follows:

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

Each layer has a specific responsibility.

This separation reduces coupling and makes the system easier to test and extend.

---

## Order Workflow Architecture

A typical order lifecycle is:

```text
REGISTERED
    |
    v
PREPARING
    |
    v
READY
    |
    v
COMPLETED
```

Cancellation is allowed from appropriate active states:

```text
REGISTERED ──────> CANCELLED

PREPARING ───────> CANCELLED

READY ───────────> CANCELLED
```

Terminal states are protected from invalid transitions.

When an order reaches `COMPLETED`, inventory consumption is performed as part of the workflow.

The completion process is transactional so that a failure during inventory consumption does not leave the order in an inconsistent state.

---

## Multi-Tenant Data Flow

The application is designed around tenant-aware data access.

Conceptually:

```text
Tenant
   |
   +---- Branches
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

Tenant-specific records carry the appropriate tenant context.

Branch-level entities also carry branch context where required.

Application-level tenant filtering is enforced through repository and service logic, while PostgreSQL Row-Level Security is intended to provide an additional database-level isolation layer.

---

## API Documentation

The backend exposes OpenAPI documentation through FastAPI.

Development documentation endpoints include:

```text
/docs
/redoc
```

The API uses versioned routes under:

```text
/api/v1/
```

API schemas and behavior are covered by automated tests to reduce the risk of breaking the documented contract.

---

## Current Development State

The backend has progressed beyond the initial architecture setup phase and is currently in the:

```text
Teacher-Ready Hardening Phase
```

Major completed areas include:

* FastAPI backend foundation
* PostgreSQL integration
* SQLAlchemy and Alembic setup
* Layered architecture
* Tenant-aware data access
* Order management
* Order lifecycle and status transitions
* Order status history
* Kitchen capacity and workload handling
* Customer addresses
* Delivery-order validation
* Product and product-variant validation
* Recipe ingredient requirements
* Inventory consumption
* Transactional rollback behavior
* Tenant-isolation validation
* API integration testing
* Service testing
* Repository testing
* OpenAPI contract validation
* Backend architecture documentation

The remaining work before the next development phase is focused on final verification and project readiness rather than adding unnecessary duplicate functionality.

---

## Documentation

The repository maintains documentation for:

* Project overview
* Project proposal
* Project structure
* Database architecture
* API/OpenAPI documentation
* Meaningful Python docstrings

Documentation should be updated alongside significant architectural changes so that the written project structure remains consistent with the implementation.
