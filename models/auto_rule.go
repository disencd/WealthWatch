package models

import (
	"time"

	"gorm.io/gorm"
)

type AutoCategoryRule struct {
	ID              uint           `gorm:"primaryKey" json:"id"`
	FamilyID        uint           `gorm:"not null;index" json:"family_id"`
	CreatedByUserID uint           `gorm:"not null" json:"created_by_user_id"`
	MerchantPattern string         `gorm:"not null" json:"merchant_pattern"`
	MinAmount       *float64       `json:"min_amount"`
	MaxAmount       *float64       `json:"max_amount"`
	CategoryID      uint           `gorm:"not null;index" json:"category_id"`
	SubCategoryID   *uint          `gorm:"index" json:"sub_category_id"`
	IsActive        bool           `gorm:"not null;default:true" json:"is_active"`
	Priority        int            `gorm:"not null;default:0" json:"priority"`
	CreatedAt       time.Time      `json:"created_at"`
	UpdatedAt       time.Time      `json:"updated_at"`
	DeletedAt       gorm.DeletedAt `gorm:"index" json:"-"`

	Family        Family       `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	CreatedByUser User         `gorm:"foreignKey:CreatedByUserID" json:"created_by_user,omitempty"`
	Category      Category     `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	SubCategory   *SubCategory `gorm:"foreignKey:SubCategoryID" json:"sub_category,omitempty"`
}

func (AutoCategoryRule) TableName() string { return "auto_category_rules" }
