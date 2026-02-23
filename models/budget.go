package models

import (
	"time"

	"gorm.io/gorm"
)

type CategoryType string

const (
	CategoryTypeExpense CategoryType = "expense"
	CategoryTypeSavings CategoryType = "savings"
)

type Category struct {
	ID          uint           `gorm:"primaryKey" json:"id"`
	FamilyID    uint           `gorm:"not null;index" json:"family_id"`
	Type        CategoryType   `gorm:"type:varchar(32);not null;index" json:"type"`
	Name        string         `gorm:"not null" json:"name"`
	Description string         `json:"description"`
	IsActive    bool           `gorm:"default:true" json:"is_active"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`

	Family        Family        `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	SubCategories []SubCategory `gorm:"foreignKey:CategoryID" json:"sub_categories,omitempty"`
}

type SubCategory struct {
	ID          uint           `gorm:"primaryKey" json:"id"`
	FamilyID    uint           `gorm:"not null;index" json:"family_id"`
	CategoryID  uint           `gorm:"not null;index" json:"category_id"`
	Name        string         `gorm:"not null" json:"name"`
	Description string         `json:"description"`
	IsActive    bool           `gorm:"default:true" json:"is_active"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`

	Family   Family   `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	Category Category `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
}

type BudgetPeriod string

const (
	BudgetPeriodMonthly BudgetPeriod = "monthly"
	BudgetPeriodYearly  BudgetPeriod = "yearly"
)

type Budget struct {
	ID            uint           `gorm:"primaryKey" json:"id"`
	FamilyID       uint           `gorm:"not null;index" json:"family_id"`
	CreatedByUserID uint          `gorm:"not null" json:"created_by_user_id"`
	CategoryID     *uint          `gorm:"index" json:"category_id"`
	SubCategoryID  *uint          `gorm:"index" json:"sub_category_id"`
	Period         BudgetPeriod   `gorm:"type:varchar(16);not null" json:"period"`
	Year           int            `gorm:"not null;index" json:"year"`
	Month          *int           `gorm:"index" json:"month"`
	Amount         float64        `gorm:"not null" json:"amount"`
	IsActive       bool           `gorm:"default:true" json:"is_active"`
	CreatedAt      time.Time      `json:"created_at"`
	UpdatedAt      time.Time      `json:"updated_at"`
	DeletedAt      gorm.DeletedAt `gorm:"index" json:"-"`

	Family        Family        `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	CreatedByUser User          `gorm:"foreignKey:CreatedByUserID" json:"created_by_user,omitempty"`
	Category      *Category     `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	SubCategory   *SubCategory  `gorm:"foreignKey:SubCategoryID" json:"sub_category,omitempty"`
}

type BudgetExpense struct {
	ID            uint           `gorm:"primaryKey" json:"id"`
	FamilyID      uint           `gorm:"not null;index" json:"family_id"`
	CreatedByUserID uint         `gorm:"not null;index" json:"created_by_user_id"`
	CategoryID    uint           `gorm:"not null;index" json:"category_id"`
	SubCategoryID uint           `gorm:"not null;index" json:"sub_category_id"`
	Title         string         `gorm:"not null" json:"title"`
	Description   string         `json:"description"`
	Amount        float64        `gorm:"not null" json:"amount"`
	Currency      string         `gorm:"not null;default:'USD'" json:"currency"`
	Date          time.Time      `gorm:"not null;index" json:"date"`
	Merchant      string         `json:"merchant"`
	Notes         string         `json:"notes"`
	CreatedAt     time.Time      `json:"created_at"`
	UpdatedAt     time.Time      `json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`

	Family        Family       `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	CreatedByUser User         `gorm:"foreignKey:CreatedByUserID" json:"created_by_user,omitempty"`
	Category      Category     `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	SubCategory   SubCategory  `gorm:"foreignKey:SubCategoryID" json:"sub_category,omitempty"`
}

func (Category) TableName() string { return "categories" }
func (SubCategory) TableName() string { return "sub_categories" }
func (Budget) TableName() string { return "budgets" }
func (BudgetExpense) TableName() string { return "budget_expenses" }
