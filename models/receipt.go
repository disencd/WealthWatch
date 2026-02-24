package models

import (
	"time"

	"gorm.io/gorm"
)

type Receipt struct {
	ID              uint           `gorm:"primaryKey" json:"id"`
	FamilyID        uint           `gorm:"not null;index" json:"family_id"`
	CreatedByUserID uint           `gorm:"not null" json:"created_by_user_id"`
	BudgetExpenseID *uint          `gorm:"index" json:"budget_expense_id"`
	FileName        string         `gorm:"not null" json:"file_name"`
	FilePath        string         `gorm:"not null" json:"file_path"`
	FileSize        int64          `json:"file_size"`
	MimeType        string         `json:"mime_type"`
	Merchant        string         `json:"merchant"`
	Amount          *float64       `json:"amount"`
	Date            *time.Time     `json:"date"`
	Notes           string         `json:"notes"`
	CreatedAt       time.Time      `json:"created_at"`
	UpdatedAt       time.Time      `json:"updated_at"`
	DeletedAt       gorm.DeletedAt `gorm:"index" json:"-"`

	Family        Family         `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	CreatedByUser User           `gorm:"foreignKey:CreatedByUserID" json:"created_by_user,omitempty"`
	BudgetExpense *BudgetExpense `gorm:"foreignKey:BudgetExpenseID" json:"budget_expense,omitempty"`
}

func (Receipt) TableName() string { return "receipts" }
