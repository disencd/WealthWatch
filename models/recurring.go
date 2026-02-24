package models

import (
	"time"

	"gorm.io/gorm"
)

type RecurringFrequency string

const (
	FrequencyWeekly    RecurringFrequency = "weekly"
	FrequencyBiweekly  RecurringFrequency = "biweekly"
	FrequencyMonthly   RecurringFrequency = "monthly"
	FrequencyQuarterly RecurringFrequency = "quarterly"
	FrequencyYearly    RecurringFrequency = "yearly"
)

type RecurringTransaction struct {
	ID              uint               `gorm:"primaryKey" json:"id"`
	FamilyID        uint               `gorm:"not null;index" json:"family_id"`
	CreatedByUserID uint               `gorm:"not null" json:"created_by_user_id"`
	Merchant        string             `gorm:"not null" json:"merchant"`
	Amount          float64            `gorm:"not null" json:"amount"`
	Currency        string             `gorm:"not null;default:'USD'" json:"currency"`
	Frequency       RecurringFrequency `gorm:"type:varchar(16);not null" json:"frequency"`
	CategoryID      *uint              `gorm:"index" json:"category_id"`
	SubCategoryID   *uint              `gorm:"index" json:"sub_category_id"`
	NextDueDate     time.Time          `gorm:"not null" json:"next_due_date"`
	IsActive        bool               `gorm:"not null;default:true" json:"is_active"`
	AutoDetected    bool               `gorm:"not null;default:false" json:"auto_detected"`
	Notes           string             `json:"notes"`
	CreatedAt       time.Time          `json:"created_at"`
	UpdatedAt       time.Time          `json:"updated_at"`
	DeletedAt       gorm.DeletedAt     `gorm:"index" json:"-"`

	Family        Family       `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	CreatedByUser User         `gorm:"foreignKey:CreatedByUserID" json:"created_by_user,omitempty"`
	Category      *Category    `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	SubCategory   *SubCategory `gorm:"foreignKey:SubCategoryID" json:"sub_category,omitempty"`
}

func (RecurringTransaction) TableName() string { return "recurring_transactions" }
