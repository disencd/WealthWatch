# WealthWatch - Personal Finance Dashboard

A comprehensive personal finance dashboard built with Go, PostgreSQL, and a modern web UI. Track accounts, net worth, investments, budgets, recurring bills, receipts, and more — with shared access for couples.

## Features

- **Account Aggregation**: Track checking, savings, credit cards, investments, loans, mortgages, and real estate
- **Net Worth Tracking**: Automatic calculation with historical snapshots and trend charts
- **Investment Portfolio**: Holdings view with cost basis, gain/loss, and asset allocation
- **Advanced Budgeting**: Custom categories, sub-categories, and monthly budget tracking with progress bars
- **Auto-Categorization Rules**: If-then rules to categorize transactions by merchant pattern and amount range
- **Recurring Bill Tracking**: Monitor subscriptions and upcoming bills with due-date alerts
- **Receipt Management**: Upload and attach receipt images/PDFs to transactions
- **Cash Flow Visualization**: Sankey-style income-to-expense flow diagrams by month
- **Spending Reports**: Monthly trends, top merchants, and savings rate calculations
- **Expense Splitting**: Split expenses with friends/groups (equal, exact, percentage)
- **Family Collaboration**: Invite a partner with separate login but shared household view
- **"Yours, Mine, Ours"**: Label accounts by ownership to distinguish joint vs. individual finances

## Tech Stack

- **Backend**: Go with Gin framework
- **Database**: PostgreSQL with GORM ORM
- **Frontend**: Vanilla JavaScript SPA, Tailwind CSS, Chart.js
- **Authentication**: JWT tokens with bcrypt password hashing
- **Containerization**: Multi-stage Docker build

## Project Structure

```
wealthwatch/
├── main.go              # Application entry point
├── go.mod               # Go module file
├── Dockerfile           # Multi-stage Docker build
├── Makefile             # Build, run, test commands
├── .env.example         # Environment variables template
├── config/              # Configuration management
├── database/            # Database connection and setup
├── models/              # Data models (User, Account, Budget, Investment, etc.)
├── handlers/            # HTTP request handlers
├── services/            # Business logic services
├── middleware/           # Auth & role middleware
├── routes/              # Route definitions
├── web/                 # Frontend (index.html, app.js)
│   ├── index.html       # SPA with sidebar navigation
│   └── app.js           # Client-side logic, charts, modals
└── utils/               # Utility functions
```

## Getting Started

### Prerequisites

- Go 1.21 or higher
- PostgreSQL database
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd wealthwatch
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Edit `.env` file with your database and JWT configuration:
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=wealthwatch_db

# JWT Configuration
JWT_SECRET=your_super_secret_jwt_key_here
```

4. Install dependencies:
```bash
go mod download
```

5. Run the application:
```bash
go run main.go
```

The server will start on `http://localhost:8080`

## API Endpoints

All endpoints below (except Auth and Health) require a valid JWT in the `Authorization: Bearer <token>` header.

### Authentication
- `POST /api/v1/auth/register` - Register a new user (auto-creates family & default categories)
- `POST /api/v1/auth/login` - Login, returns JWT token
- `GET /api/v1/profile` - Get current user profile

### Accounts
- `GET /api/v1/accounts` - List accounts (filter: `?ownership=mine|yours|ours`)
- `POST /api/v1/accounts` - Create account
- `GET /api/v1/accounts/:id` - Get account
- `PUT /api/v1/accounts/:id` - Update account
- `DELETE /api/v1/accounts/:id` - Delete account

### Net Worth
- `GET /api/v1/networth/summary` - Current net worth with asset/liability breakdown by type
- `GET /api/v1/networth/history` - Historical net worth snapshots
- `POST /api/v1/networth/snapshot` - Take a point-in-time snapshot

### Investments
- `GET /api/v1/investments` - List holdings
- `POST /api/v1/investments` - Add holding
- `GET /api/v1/investments/:id` - Get holding
- `PUT /api/v1/investments/:id` - Update holding
- `DELETE /api/v1/investments/:id` - Delete holding
- `GET /api/v1/investments/portfolio` - Portfolio summary (total value, cost basis, gain/loss)

### Budget Categories & Expenses
- `GET /api/v1/budget/categories` - List categories
- `POST /api/v1/budget/categories` - Create category
- `GET /api/v1/budget/subcategories` - List sub-categories
- `POST /api/v1/budget/subcategories` - Create sub-category
- `GET /api/v1/budget/budgets` - List budgets (filter: `?year=&month=`)
- `POST /api/v1/budget/budgets` - Create budget
- `GET /api/v1/budget/expenses` - List transactions (filter: `?category_id=&year=&month=`)
- `POST /api/v1/budget/expenses` - Add transaction
- `GET /api/v1/budget/summary/monthly` - Monthly spending summary by category

### Recurring Bills
- `GET /api/v1/recurring` - List recurring transactions
- `POST /api/v1/recurring` - Create recurring bill
- `PUT /api/v1/recurring/:id` - Update recurring bill
- `DELETE /api/v1/recurring/:id` - Delete recurring bill
- `GET /api/v1/recurring/upcoming` - Upcoming bills (next 30 days)

### Auto-Categorization Rules
- `GET /api/v1/rules` - List rules
- `POST /api/v1/rules` - Create rule
- `PUT /api/v1/rules/:id` - Update rule
- `DELETE /api/v1/rules/:id` - Delete rule

### Receipts
- `GET /api/v1/receipts` - List receipts
- `POST /api/v1/receipts` - Upload receipt (multipart form: `file`, `merchant`, `amount`, `date`, `notes`)
- `GET /api/v1/receipts/:id` - Get receipt metadata
- `DELETE /api/v1/receipts/:id` - Delete receipt and file

### Reports
- `GET /api/v1/reports/spending-trends?months=N` - Monthly spending totals
- `GET /api/v1/reports/spending-by-merchant?limit=N` - Top merchants by spend
- `GET /api/v1/reports/cashflow-sankey?year=&month=` - Cash flow Sankey data (income → expense links)
- `GET /api/v1/reports/savings-rate?year=&month=` - Savings rate for a given month

### Split Expenses
- `POST /api/v1/expenses` - Create expense with splits
- `GET /api/v1/expenses` - List expenses

### Groups
- `POST /api/v1/groups` - Create group
- `GET /api/v1/groups` - List groups
- `GET /api/v1/groups/:id` - Get group
- `POST /api/v1/groups/:id/members` - Add member
- `DELETE /api/v1/groups/:id/members/:memberId` - Remove member

### Balances & Settlements
- `GET /api/v1/balances` - Get balances with all users
- `GET /api/v1/balances/users/:userId` - Balance with specific user
- `POST /api/v1/settlements` - Create settlement
- `GET /api/v1/settlements` - List settlements
- `PUT /api/v1/settlements/:id/status` - Update settlement status

### Family
- `POST /api/v1/families` - Create family
- `GET /api/v1/families` - List user's families
- `GET /api/v1/families/members` - List family members
- `POST /api/v1/families/members` - Invite member (by email)
- `PUT /api/v1/families/members/:id/role` - Update member role
- `DELETE /api/v1/families/members/:id` - Remove member

### Health Check
- `GET /health` - Health check endpoint

## Database Schema

The application uses the following entities (auto-migrated on startup):

- **User** - Authentication and profile
- **Family / FamilyMembership** - Household grouping with roles
- **Account** - Financial accounts (checking, savings, credit card, investment, loan, mortgage, real estate)
- **InvestmentHolding** - Individual securities/crypto holdings
- **NetWorthSnapshot** - Point-in-time net worth records
- **Category / SubCategory** - Budget categories per family
- **Budget** - Monthly/yearly spending limits per category
- **BudgetExpense** - Individual transactions linked to categories
- **RecurringTransaction** - Subscriptions and recurring bills
- **AutoCategoryRule** - Merchant-pattern-based auto-categorization
- **Receipt** - Uploaded receipt files with metadata
- **Group / GroupMember** - Groups for expense splitting
- **Expense / Split** - Shared expenses with splits
- **Settlement** - Payments between users

## Usage Examples

### Register and Login

```bash
# Register
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Alice","last_name":"Smith","email":"alice@example.com","password":"secret123"}'

# Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'
```

### Add an Account

```bash
curl -X POST http://localhost:8080/api/v1/accounts \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"institution_name":"Chase","account_name":"Checking","account_type":"checking","ownership":"ours","balance":5200.00}'
```

### Take a Net Worth Snapshot

```bash
curl -X POST http://localhost:8080/api/v1/networth/snapshot \
  -H "Authorization: Bearer <token>"
```

### Upload a Receipt

```bash
curl -X POST http://localhost:8080/api/v1/receipts \
  -H "Authorization: Bearer <token>" \
  -F "file=@receipt.jpg" \
  -F "merchant=Costco" \
  -F "amount=142.50" \
  -F "date=2025-01-15"
```

## Development

### Run Locally

```bash
go mod download
go run main.go        # starts on :8080
```

### Docker

```bash
docker build -t wealthwatch .
docker run --rm -p 8080:8080 --env-file .env wealthwatch
```

### Makefile Targets

```bash
make setup       # install tools
make deps        # download dependencies
make build       # compile binary
make run         # run locally
make test        # run tests
make docker-build
make docker-run
```

### Database Migrations

Auto-migrated on startup via GORM `AutoMigrate`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
