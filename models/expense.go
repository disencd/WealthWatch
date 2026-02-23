package models

import (
	"time"

	"gorm.io/gorm"
)

// Expense represents an expense shared among users
type Expense struct {
	ID          uint           `gorm:"primaryKey" json:"id"`
	Title       string         `gorm:"not null" json:"title"`
	Description string         `json:"description"`
	Amount      float64        `gorm:"not null" json:"amount"`
	Currency    string         `gorm:"default:'USD'" json:"currency"`
	Date        time.Time      `gorm:"not null" json:"date"`
	PayerID     uint           `gorm:"not null" json:"payer_id"`
	GroupID     *uint          `json:"group_id"`
	Category    string         `json:"category"`
	Receipt     string         `json:"receipt"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	Payer  User    `gorm:"foreignKey:PayerID" json:"payer,omitempty"`
	Group  *Group  `gorm:"foreignKey:GroupID" json:"group,omitempty"`
	Splits []Split `gorm:"foreignKey:ExpenseID" json:"splits,omitempty"`
}

// Split represents how an expense is split among users
type Split struct {
	ID        uint           `gorm:"primaryKey" json:"id"`
	ExpenseID uint           `gorm:"not null" json:"expense_id"`
	UserID    uint           `gorm:"not null" json:"user_id"`
	Amount    float64        `gorm:"not null" json:"amount"`
	Percentage float64       `json:"percentage"`
	CreatedAt time.Time      `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time      `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	Expense Expense `gorm:"foreignKey:ExpenseID" json:"expense,omitempty"`
	User    User    `gorm:"foreignKey:UserID" json:"user,omitempty"`
}

// Settlement represents a payment settlement between users
type Settlement struct {
	ID            uint           `gorm:"primaryKey" json:"id"`
	FromUserID    uint           `gorm:"not null" json:"from_user_id"`
	ToUserID      uint           `gorm:"not null" json:"to_user_id"`
	Amount        float64        `gorm:"not null" json:"amount"`
	Currency      string         `gorm:"default:'USD'" json:"currency"`
	Status        string         `gorm:"default:'pending'" json:"status"` // pending, completed, cancelled
	PaymentMethod string         `json:"payment_method"`
	Notes         string         `json:"notes"`
	CreatedAt     time.Time      `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt     time.Time      `gorm:"autoUpdateTime" json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	FromUser User `gorm:"foreignKey:FromUserID" json:"from_user,omitempty"`
	ToUser   User `gorm:"foreignKey:ToUserID" json:"to_user,omitempty"`
}

// TableName returns the table name for Expense model
func (Expense) TableName() string {
	return "expenses"
}

// TableName returns the table name for Split model
func (Split) TableName() string {
	return "splits"
}

// TableName returns the table name for Settlement model
func (Settlement) TableName() string {
	return "settlements"
}
