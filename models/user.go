package models

import (
	"time"

	"gorm.io/gorm"
)

// User represents a user in the system
type User struct {
	ID        uint           `json:"id"`
	FirstName string         `gorm:"not null" json:"first_name"`
	LastName  string         `gorm:"not null" json:"last_name"`
	Email     string         `gorm:"uniqueIndex;not null" json:"email"`
	Password  string         `gorm:"not null" json:"-"`
	Phone     string         `json:"phone"`
	Avatar    string         `json:"avatar"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	Groups          []Group      `gorm:"many2many:group_members;" json:"groups,omitempty"`
	Expenses        []Expense    `gorm:"foreignKey:PayerID" json:"expenses,omitempty"`
	Splits          []Split      `gorm:"foreignKey:UserID" json:"splits,omitempty"`
	FromSettlements []Settlement `gorm:"foreignKey:FromUserID" json:"from_settlements,omitempty"`
	ToSettlements   []Settlement `gorm:"foreignKey:ToUserID" json:"to_settlements,omitempty"`
}

// TableName returns the table name for User model
func (User) TableName() string {
	return "users"
}

// GetFullName returns the user's full name
func (u *User) GetFullName() string {
	return u.FirstName + " " + u.LastName
}
