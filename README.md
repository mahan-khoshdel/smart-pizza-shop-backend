# Smart Pizza Shop Backend

## Overview

This repository contains the backend and database layer of a commercial-oriented web platform for businesses that receive customer orders.

The initial use case is a pizza shop, but the platform is **not limited to pizza or restaurants**. The architecture is designed to support cafes, fast-food businesses, bakeries, sandwich shops, dessert shops, beverage shops, and other order-based businesses.

The platform is designed from the beginning with **multi-tenant, multi-branch, AI-ready, and SaaS-ready architecture** so that multiple independent businesses can use the same platform while keeping their data isolated.

> Product/brand name is intentionally not finalized yet.

## Product Vision

The goal is to build more than a traditional CRUD or POS application.

The platform will connect:

- Orders
- Products and variants
- Recipes and ingredients
- Inventory and purchasing
- Kitchen operations
- Customers
- Payments and discounts
- Expenses and financial reporting
- Analytics
- Artificial intelligence
- Business recommendations

into one operational platform.

## Core Features

### Business and Multi-Tenancy

- Multi-tenant architecture
- Multi-branch support
- Tenant data isolation
- PostgreSQL Row-Level Security (RLS)
- Role-based access control
- Fine-grained permissions
- Feature Flags / Tenant Features
- Branch-specific settings and operations

### Products and Menu

- Categories
- Products
- Product variants
- Multiple product sizes
- Product availability
- Product options and add-ons
- Configurable optional/removable ingredients

### Recipe and Unit Management

- Recipes connected to `ProductVariant`
- Recipe items and ingredient quantities
- Standard unit system
- Unit conversion such as kg/g, L/ml, and piece
- Recipe-driven ingredient consumption

### Orders and Kitchen

- `DINE_IN`
- `TAKEAWAY`
- `DELIVERY`
- Order items
- Add-ons per order item
- Order status history
- Kitchen Order View
- `PREPARING` workflow
- Kitchen workload and capacity tracking
- Dynamic preparation-time estimation
- Dynamic delivery-time estimation

### Customers

- Customer profiles
- Multiple customer addresses
- Order history
- Order address snapshot
- Personalized recommendations
- Frequently Bought Together recommendations
- Loyalty and rewards

### Inventory

- Current stock
- Inventory transactions
- Inventory batches / lots
- Expiry-date management
- FEFO support
- Waste tracking
- Stock adjustments
- Inter-branch transfers
- Low-stock monitoring
- Smart inventory planning
- Smart restocking recommendations

### Purchasing and Suppliers

- Supplier management
- Purchases
- Purchase items
- Ingredient purchase costs
- Supplier performance analysis
- Supplier price comparison
- Purchase trends

### Payments, Discounts and Finance

- Cash, card and online payment support
- Payment status tracking
- Transaction references
- Discount codes
- Discount usage limits
- Operating expenses
- Purchase costs as ingredient costs
- Financial summaries
- Financial reports

### Analytics and Business Intelligence

- Sales analytics
- Consumption trend analysis
- Supplier analysis
- Waste analysis
- Daily business summary
- Business dashboard
- Busy-hours prediction
- Product performance analysis
- Estimated profitability
- Anomaly detection

## Artificial Intelligence

AI is a core product capability rather than a decorative add-on.

Planned AI capabilities include:

- AI Demand Forecasting
- AI Smart Inventory & Purchase Planning
- AI Waste Prediction
- AI Menu Intelligence
- AI Kitchen Load & Capacity Prediction
- Dynamic Preparation / Delivery Prediction
- AI Customer Recommendations
- AI Supplier Intelligence
- AI Anomaly Detection
- AI Business Assistant

The architecture will distinguish between predictive/analytical models and generative AI capabilities.

AI features will be introduced progressively after reliable business data is available.

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn

### Database

- PostgreSQL
- SQLAlchemy
- Psycopg 3
- Alembic

### Validation and Configuration

- Pydantic
- Pydantic Settings
- Environment variables

### API

- REST API
- OpenAPI
- Swagger UI: `/docs`
- ReDoc: `/redoc`

### Quality and Operations

- Pytest
- Structured logging
- Error handling
- Database transactions
- Audit logging
- Docker-ready architecture

## Backend Architecture

The backend follows a layered architecture:

```text
Client / Frontend
        |
        v
FastAPI Routes
        |
        v
Pydantic Schemas
        |
        v
Service Layer
        |
        v
Repository / Data Access
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

The frontend will live in a separate GitHub repository.

## Project Structure

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
│   │   └── ...
│   └── project-structure.md
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── core/
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── base.py
│   │   └── models/
│   │
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── api/
│   ├── reports/
│   └── utils/
│
├── database/
│
├── migrations/
│
└── tests/
```

See [`docs/project-structure.md`](docs/project-structure.md) for the detailed explanation of each directory.

## Database Approach

The primary database implementation uses **PostgreSQL + SQLAlchemy + Alembic**.

The main application tables will be represented by SQLAlchemy models and managed through Alembic migrations.

The root-level `database/` directory is reserved for PostgreSQL-specific assets that may be better represented as SQL, such as:

- RLS policies
- PostgreSQL functions
- Triggers
- Seed data
- Other database-specific scripts

This avoids maintaining the same table structure in both raw SQL and ORM models.

## Security

Security is a first-class concern.

Planned protections include:

- Tenant isolation
- PostgreSQL RLS
- Authentication
- Authorization
- Role-based access control
- Fine-grained permissions
- Password hashing
- Secure environment configuration
- Audit logs
- Database constraints and transactions

## Documentation Standards

The project will maintain:

- Meaningful docstrings for public classes and functions
- Clear API route descriptions
- Pydantic request and response schemas
- OpenAPI documentation
- Swagger UI at `/docs`
- ReDoc at `/redoc`
- API documentation
- Database documentation
- Architecture documentation

## SaaS-Ready Architecture

The platform is designed to support future commercialization.

The initial implementation will **not** include subscription billing logic, but the architecture will remain ready for:

- Subscription plans
- Tenant plans
- Billing
- Invoices
- Subscription payments
- Plan-based feature access

Feature Flags / Tenant Features will also allow capabilities to be enabled or disabled per tenant.

## Development Roadmap

1. Finalize database architecture
2. Finalize multi-tenant and multi-branch rules
3. Set up PostgreSQL
4. Configure SQLAlchemy
5. Configure Alembic
6. Implement core database models
7. Design REST API routes
8. Implement authentication and authorization
9. Implement tenant isolation and RLS
10. Implement products, recipes and units
11. Implement orders and kitchen workflows
12. Implement inventory and purchasing
13. Implement payments, discounts and expenses
14. Implement analytics and reports
15. Implement AI capabilities
16. Add testing, logging and production hardening
17. Develop the separate frontend repository
18. Prepare the platform for real-world deployment

## Development Status

**Status: Active Development**

The project is currently in the environment and architecture setup phase.

Completed so far:

- Project repository initialized
- Repository structure established
- Python virtual environment configured
- Backend dependencies installed
- PostgreSQL 18.6 installed and running
- Application PostgreSQL role and database created
- Environment configuration added
- SQLAlchemy database connection established successfully
- SQLAlchemy Declarative Base created

## Repositories

Backend + Database:

```text
smart-pizza-shop-backend
```

Frontend:

```text
smart-pizza-shop-frontend
```

The frontend repository will be developed separately after the backend API is established.
