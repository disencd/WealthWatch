# Splitwise - Expense Sharing Application

A modern expense-sharing application built with Go and PostgreSQL, inspired by Splitwise.

## Features

- **User Authentication**: Secure registration and login with JWT tokens
- **Expense Management**: Create, view, and manage expenses with detailed splitting
- **Group Management**: Create groups and manage members for shared expenses
- **Flexible Splitting**: Equal, exact, and percentage-based expense splitting
- **Balance Tracking**: Real-time balance calculation between users
- **Settlement Tracking**: Track and manage payments between users
- **RESTful API**: Well-designed API endpoints for all functionality

## Tech Stack

- **Backend**: Go with Gin framework
- **Database**: PostgreSQL with GORM ORM
- **Authentication**: JWT tokens
- **Password Hashing**: bcrypt
- **Architecture**: Clean architecture with handlers, services, and models

## Project Structure

```
splitwise/
├── main.go              # Application entry point
├── go.mod               # Go module file
├── .env.example         # Environment variables template
├── config/              # Configuration management
├── database/            # Database connection and setup
├── models/              # Data models and schemas
├── handlers/            # HTTP request handlers
├── services/            # Business logic services
├── middleware/          # HTTP middleware (auth, etc.)
├── routes/              # Route definitions
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
cd splitwise
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
DB_NAME=splitwise_db

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

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/profile` - Get user profile (protected)

### Expenses
- `POST /api/v1/expenses` - Create a new expense (protected)
- `GET /api/v1/expenses` - Get user's expenses (protected)
- `GET /api/v1/expenses/:id` - Get specific expense (protected)

### Groups
- `POST /api/v1/groups` - Create a new group (protected)
- `GET /api/v1/groups` - Get user's groups (protected)
- `GET /api/v1/groups/:id` - Get specific group (protected)
- `POST /api/v1/groups/:id/members` - Add member to group (protected)
- `DELETE /api/v1/groups/:id/members/:memberId` - Remove member from group (protected)

### Balances
- `GET /api/v1/balances` - Get user's balances with all users (protected)
- `GET /api/v1/balances/users/:userId` - Get balance with specific user (protected)

### Settlements
- `POST /api/v1/settlements` - Create a new settlement (protected)
- `GET /api/v1/settlements` - Get user's settlements (protected)
- `GET /api/v1/settlements/:id` - Get specific settlement (protected)
- `PUT /api/v1/settlements/:id/status` - Update settlement status (protected)

### Health Check
- `GET /health` - Health check endpoint

## Database Schema

The application uses the following main entities:

- **Users**: User accounts with authentication
- **Groups**: Collections of users for shared expenses
- **Expenses**: Individual expenses with splitting information
- **Splits**: How expenses are divided among users
- **Settlements**: Payment records between users
- **GroupMembers**: Join table for users and groups

## Usage Examples

### Creating an Expense

```bash
curl -X POST http://localhost:8080/api/v1/expenses \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dinner at Restaurant",
    "description": "Team dinner",
    "amount": 120.00,
    "currency": "USD",
    "date": "2024-01-15T19:00:00Z",
    "splits": [
      {"user_id": 2, "amount": 40.00},
      {"user_id": 3, "amount": 40.00},
      {"user_id": 1, "amount": 40.00}
    ]
  }'
```

### Getting User Balances

```bash
curl -X GET http://localhost:8080/api/v1/balances \
  -H "Authorization: Bearer <your-jwt-token>"
```

## Development

### Running Tests

```bash
go test ./...
```

### Database Migrations

The application automatically runs database migrations on startup using GORM AutoMigrate.

### Adding New Features

1. Add models in the `models/` directory
2. Implement business logic in `services/`
3. Create HTTP handlers in `handlers/`
4. Add routes in `routes/routes.go`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
