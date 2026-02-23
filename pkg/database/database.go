package database

import (
	"fmt"
	"log"
	"time"

	"wealthwatch/pkg/config"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// InitDB initializes the database connection
func InitDB(cfg config.DatabaseConfig) (*gorm.DB, error) {
	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=%s TimeZone=UTC",
		cfg.Host,
		cfg.User,
		cfg.Password,
		cfg.DBName,
		cfg.Port,
		cfg.SSLMode,
	)

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	// Configure connection pool
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get underlying sql.DB: %w", err)
	}

	sqlDB.SetMaxOpenConns(cfg.MaxOpenConns)
	sqlDB.SetMaxIdleConns(cfg.MaxIdleConns)
	sqlDB.SetConnMaxLifetime(cfg.ConnMaxLifetime)

	// Test connection
	if err := sqlDB.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	log.Println("Database connection established successfully")
	return db, nil
}

// RunMigrations runs migrations for a specific service
func RunMigrations(db *gorm.DB, service string) error {
	log.Printf("Running migrations for service: %s", service)

	switch service {
	case "auth":
		return runAuthMigrations(db)
	case "user":
		return runUserMigrations(db)
	case "expense":
		return runExpenseMigrations(db)
	case "balance":
		return runBalanceMigrations(db)
	case "settlement":
		return runSettlementMigrations(db)
	case "notification":
		return runNotificationMigrations(db)
	default:
		return fmt.Errorf("unknown service: %s", service)
	}
}

func runAuthMigrations(db *gorm.DB) error {
	// Users table
	type User struct {
		ID        uint           `gorm:"primaryKey" json:"id"`
		FirstName string         `gorm:"not null" json:"first_name"`
		LastName  string         `gorm:"not null" json:"last_name"`
		Email     string         `gorm:"uniqueIndex;not null" json:"email"`
		Password  string         `gorm:"not null" json:"-"`
		Phone     string         `json:"phone"`
		Avatar    string         `json:"avatar"`
		IsActive  bool           `gorm:"default:true" json:"is_active"`
		CreatedAt time.Time      `json:"created_at"`
		UpdatedAt time.Time      `json:"updated_at"`
		DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
	}

	// Sessions table
	type Session struct {
		ID        string    `gorm:"primaryKey" json:"id"`
		UserID    uint      `gorm:"not null" json:"user_id"`
		TokenHash string    `gorm:"not null;index" json:"-"`
		ExpiresAt time.Time `gorm:"not null" json:"expires_at"`
		CreatedAt time.Time `json:"created_at"`
		UpdatedAt time.Time `json:"updated_at"`
		User      User      `gorm:"foreignKey:UserID" json:"user,omitempty"`
	}

	return db.AutoMigrate(&User{}, &Session{})
}

func runUserMigrations(db *gorm.DB) error {
	// User profiles table
	type UserProfile struct {
		ID          uint      `gorm:"primaryKey" json:"id"`
		UserID      uint      `gorm:"uniqueIndex;not null" json:"user_id"`
		Bio         string    `json:"bio"`
		Avatar      string    `json:"avatar"`
		Preferences string    `gorm:"type:jsonb" json:"preferences"`
		CreatedAt   time.Time `json:"created_at"`
		UpdatedAt   time.Time `json:"updated_at"`
	}

	return db.AutoMigrate(&UserProfile{})
}

func runExpenseMigrations(db *gorm.DB) error {
	// Categories table
	type Category struct {
		ID          uint      `gorm:"primaryKey" json:"id"`
		Name        string    `gorm:"uniqueIndex;not null" json:"name"`
		Description string    `json:"description"`
		Icon        string    `json:"icon"`
		Color       string    `json:"color"`
		CreatedAt   time.Time `json:"created_at"`
		UpdatedAt   time.Time `json:"updated_at"`
	}

	// Expenses table
	type Expense struct {
		ID          uint           `gorm:"primaryKey" json:"id"`
		Title       string         `gorm:"not null" json:"title"`
		Description string         `json:"description"`
		Amount      float64        `gorm:"not null" json:"amount"`
		Currency    string         `gorm:"default:'USD'" json:"currency"`
		Date        time.Time      `gorm:"not null" json:"date"`
		PayerID     uint           `gorm:"not null" json:"payer_id"`
		CategoryID  *uint          `json:"category_id"`
		Receipt     string         `json:"receipt"`
		Status      string         `gorm:"default:'active'" json:"status"`
		CreatedAt   time.Time      `json:"created_at"`
		UpdatedAt   time.Time      `json:"updated_at"`
		DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`
		Category    *Category      `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	}

	// Expense splits table
	type ExpenseSplit struct {
		ID         uint      `gorm:"primaryKey" json:"id"`
		ExpenseID  uint      `gorm:"not null" json:"expense_id"`
		UserID     uint      `gorm:"not null" json:"user_id"`
		Amount     float64   `gorm:"not null" json:"amount"`
		Percentage float64   `json:"percentage"`
		Status     string    `gorm:"default:'pending'" json:"status"`
		CreatedAt  time.Time `gorm:"autoCreateTime" json:"created_at"`
		UpdatedAt  time.Time `gorm:"autoUpdateTime" json:"updated_at"`
		Expense    Expense   `gorm:"foreignKey:ExpenseID" json:"expense,omitempty"`
	}

	return db.AutoMigrate(&Category{}, &Expense{}, &ExpenseSplit{})
}

func runBalanceMigrations(db *gorm.DB) error {
	// Balances table
	type Balance struct {
		ID          uint      `gorm:"primaryKey" json:"id"`
		UserID      uint      `gorm:"not null" json:"user_id"`
		OtherUserID uint      `gorm:"not null" json:"other_user_id"`
		Amount      float64   `gorm:"not null;default:0" json:"amount"`
		Currency    string    `gorm:"default:'USD'" json:"currency"`
		LastUpdated time.Time `gorm:"autoUpdateTime" json:"last_updated"`
		CreatedAt   time.Time `gorm:"autoCreateTime" json:"created_at"`
	}

	// Balance history table
	type BalanceHistory struct {
		ID          uint      `gorm:"primaryKey" json:"id"`
		UserID      uint      `gorm:"not null" json:"user_id"`
		OtherUserID uint      `gorm:"not null" json:"other_user_id"`
		Amount      float64   `gorm:"not null" json:"amount"`
		Type        string    `gorm:"not null" json:"type"` // expense, settlement, adjustment
		ReferenceID *uint     `json:"reference_id"`
		CreatedAt   time.Time `gorm:"autoCreateTime" json:"created_at"`
	}

	return db.AutoMigrate(&Balance{}, &BalanceHistory{})
}

func runSettlementMigrations(db *gorm.DB) error {
	// Settlements table
	type Settlement struct {
		ID            uint       `gorm:"primaryKey" json:"id"`
		FromUserID    uint       `gorm:"not null" json:"from_user_id"`
		ToUserID      uint       `gorm:"not null" json:"to_user_id"`
		Amount        float64    `gorm:"not null" json:"amount"`
		Currency      string     `gorm:"default:'USD'" json:"currency"`
		Status        string     `gorm:"default:'pending'" json:"status"`
		PaymentMethod string     `json:"payment_method"`
		Notes         string     `json:"notes"`
		ProcessedAt   *time.Time `json:"processed_at"`
		CreatedAt     time.Time  `gorm:"autoCreateTime" json:"created_at"`
		UpdatedAt     time.Time  `gorm:"autoUpdateTime" json:"updated_at"`
	}

	return db.AutoMigrate(&Settlement{})
}

func runNotificationMigrations(db *gorm.DB) error {
	// Notifications table
	type Notification struct {
		ID        uint      `gorm:"primaryKey" json:"id"`
		UserID    uint      `gorm:"not null" json:"user_id"`
		Type      string    `gorm:"not null" json:"type"`
		Title     string    `gorm:"not null" json:"title"`
		Message   string    `gorm:"not null" json:"message"`
		Data      string    `gorm:"type:jsonb" json:"data"`
		Read      bool      `gorm:"default:false" json:"read"`
		CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
		UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`
	}

	// Notification templates table
	type NotificationTemplate struct {
		ID          uint      `gorm:"primaryKey" json:"id"`
		Type        string    `gorm:"uniqueIndex;not null" json:"type"`
		Subject     string    `gorm:"not null" json:"subject"`
		Body        string    `gorm:"not null" json:"body"`
		Description string    `json:"description"`
		CreatedAt   time.Time `gorm:"autoCreateTime" json:"created_at"`
		UpdatedAt   time.Time `gorm:"autoUpdateTime" json:"updated_at"`
	}

	return db.AutoMigrate(&Notification{}, &NotificationTemplate{})
}
