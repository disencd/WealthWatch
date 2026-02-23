package models

import (
	"time"
	"gorm.io/gorm"
)

// Expense Categories
type ExpenseCategory string

const (
	Housing            ExpenseCategory = "Housing"
	Utilities          ExpenseCategory = "Utilities"
	Food               ExpenseCategory = "Food"
	Transportation     ExpenseCategory = "Transportation"
	MedicalHealthcare  ExpenseCategory = "Medical & Healthcare"
	DayCare            ExpenseCategory = "DayCare"
	Church             ExpenseCategory = "Church"
)

// Savings Categories
type SavingsCategory string

const (
	Savings1 SavingsCategory = "Savings 1"
	Savings2 SavingsCategory = "Savings 2"
	Savings3 SavingsCategory = "Savings 3"
)

// Expense Sub-categories
type ExpenseSubCategory string

const (
	// Housing Sub-categories
	ADU               ExpenseSubCategory = "ADU"
	HomeImprovement   ExpenseSubCategory = "Home Improvement"
	
	// Utilities Sub-categories
	PGNE              ExpenseSubCategory = "PGNE"
	WaterDept         ExpenseSubCategory = "Water Dept"
	InternetPhone     ExpenseSubCategory = "Internet + Phone"
	
	// Food Sub-categories
	Grocery           ExpenseSubCategory = "Grocery"
	IndianGrocery     ExpenseSubCategory = "Indian Grocery"
	Restaurant        ExpenseSubCategory = "Restaurant"
	
	// Transportation Sub-categories
	Gas               ExpenseSubCategory = "Gas"
	
	// Medical & Healthcare Sub-categories
	MedicalExpense    ExpenseSubCategory = "Medical Expense"
	
	// DayCare Sub-categories
	DayCareExpense    ExpenseSubCategory = "DayCare"
	
	// Church Sub-categories
	ChurchExpense     ExpenseSubCategory = "Church"
	
	// Personal Sub-categories
	Movie             ExpenseSubCategory = "Movie"
	Camping           ExpenseSubCategory = "Camping"
	Hair              ExpenseSubCategory = "Hair"
)

// Category defines the main expense categories
type Category struct {
	ID          uint      `gorm:"primaryKey" json:"id"`
	Name        string    `gorm:"uniqueIndex;not null" json:"name"`
	Type        string    `gorm:"not null" json:"type"` // expense, savings
	Description string    `json:"description"`
	Color       string    `json:"color"`         // For UI display
	Icon        string    `json:"icon"`          // For UI display
	IsActive    bool      `gorm:"default:true" json:"is_active"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`
	
	// Relationships
	SubCategories []SubCategory `gorm:"foreignKey:CategoryID" json:"sub_categories,omitempty"`
	Budgets       []Budget       `gorm:"foreignKey:CategoryID" json:"budgets,omitempty"`
}

// SubCategory defines expense sub-categories
type SubCategory struct {
	ID          uint      `gorm:"primaryKey" json:"id"`
	CategoryID  uint      `gorm:"not null" json:"category_id"`
	Name        string    `gorm:"not null" json:"name"`
	Description string    `json:"description"`
	Color       string    `json:"color"`
	Icon        string    `json:"icon"`
	IsActive    bool      `gorm:"default:true" json:"is_active"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`
	
	// Relationships
	Category  Category `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	Expenses  []Expense `gorm:"foreignKey:SubCategoryID" json:"expenses,omitempty"`
	Budgets   []Budget  `gorm:"foreignKey:SubCategoryID" json:"budgets,omitempty"`
}

// Budget defines budget limits for categories/sub-categories
type Budget struct {
	ID             uint      `gorm:"primaryKey" json:"id"`
	CategoryID     *uint     `json:"category_id"`
	SubCategoryID  *uint     `json:"sub_category_id"`
	UserID         uint      `gorm:"not null" json:"user_id"`
	Amount         float64   `gorm:"not null" json:"amount"`
	Period         string    `gorm:"not null" json:"period"` // monthly, yearly, weekly
	Year           int       `gorm:"not null" json:"year"`
	Month          *int      `json:"month"` // nil for yearly budgets
	AlertThreshold float64   `gorm:"default:0.8" json:"alert_threshold"` // 0.8 = 80%
	IsActive       bool      `gorm:"default:true" json:"is_active"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
	DeletedAt      gorm.DeletedAt `gorm:"index" json:"-"`
	
	// Relationships
	User        User         `gorm:"foreignKey:UserID" json:"user,omitempty"`
	Category    *Category    `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	SubCategory *SubCategory `gorm:"foreignKey:SubCategoryID" json:"sub_category,omitempty"`
	Expenses    []Expense    `gorm:"foreignKey:BudgetID" json:"expenses,omitempty"`
}

// Expense represents individual expenses
type Expense struct {
	ID            uint      `gorm:"primaryKey" json:"id"`
	UserID        uint      `gorm:"not null" json:"user_id"`
	CategoryID    uint      `gorm:"not null" json:"category_id"`
	SubCategoryID uint      `gorm:"not null" json:"sub_category_id"`
	BudgetID      *uint     `json:"budget_id"`
	Title         string    `gorm:"not null" json:"title"`
	Description   string    `json:"description"`
	Amount        float64   `gorm:"not null" json:"amount"`
	Currency      string    `gorm:"default:'USD'" json:"currency"`
	Date          time.Time `gorm:"not null" json:"date"`
	Location      string    `json:"location"`
	Receipt       string    `json:"receipt"` // URL to receipt image
	Tags          string    `gorm:"type:text" json:"tags"` // JSON array of tags
	IsRecurring   bool      `gorm:"default:false" json:"is_recurring"`
	RecurringType string    `json:"recurring_type"` // daily, weekly, monthly, yearly
	RecurringEnd  *time.Time `json:"recurring_end"`
	Status        string    `gorm:"default:'active'" json:"status"` // active, cancelled
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`
	
	// Relationships
	User        User         `gorm:"foreignKey:UserID" json:"user,omitempty"`
	Category    Category     `gorm:"foreignKey:CategoryID" json:"category,omitempty"`
	SubCategory SubCategory  `gorm:"foreignKey:SubCategoryID" json:"sub_category,omitempty"`
	Budget      *Budget      `gorm:"foreignKey:BudgetID" json:"budget,omitempty"`
}

// Savings represents savings contributions
type Savings struct {
	ID            uint      `gorm:"primaryKey" json:"id"`
	UserID        uint      `gorm:"not null" json:"user_id"`
	Category      SavingsCategory `gorm:"not null" json:"category"`
	Amount        float64   `gorm:"not null" json:"amount"`
	Currency      string    `gorm:"default:'USD'" json:"currency"`
	Date          time.Time `gorm:"not null" json:"date"`
	Description   string    `json:"description"`
	TargetAmount  *float64  `json:"target_amount"`
	TargetDate    *time.Time `json:"target_date"`
	IsCompleted   bool      `gorm:"default:false" json:"is_completed"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
	DeletedAt     gorm.DeletedAt `gorm:"index" json:"-"`
	
	// Relationships
	User User `gorm:"foreignKey:UserID" json:"user,omitempty"`
}

// BudgetSummary provides budget analysis
type BudgetSummary struct {
	CategoryID     uint     `json:"category_id"`
	CategoryName   string   `json:"category_name"`
	SubCategoryID  *uint    `json:"sub_category_id"`
	SubCategoryName *string `json:"sub_category_name"`
	BudgetAmount   float64  `json:"budget_amount"`
	SpentAmount    float64  `json:"spent_amount"`
	Remaining      float64  `json:"remaining"`
	PercentageUsed float64  `json:"percentage_used"`
	IsOverBudget   bool     `json:"is_over_budget"`
	Period         string   `json:"period"`
	Year           int      `json:"year"`
	Month          *int     `json:"month"`
}

// MonthlySummary provides monthly expense breakdown
type MonthlySummary struct {
	Year          int                    `json:"year"`
	Month         int                    `json:"month"`
	TotalExpenses float64                `json:"total_expenses"`
	TotalSavings  float64                `json:"total_savings"`
	Categories    []CategorySummary      `json:"categories"`
	Savings       []SavingsSummary       `json:"savings"`
}

// CategorySummary provides category-wise breakdown
type CategorySummary struct {
	CategoryID     uint                   `json:"category_id"`
	CategoryName   string                 `json:"category_name"`
	TotalAmount    float64                `json:"total_amount"`
	SubCategories  []SubCategorySummary   `json:"sub_categories"`
}

// SubCategorySummary provides sub-category breakdown
type SubCategorySummary struct {
	SubCategoryID  uint    `json:"sub_category_id"`
	SubCategoryName string `json:"sub_category_name"`
	TotalAmount    float64 `json:"total_amount"`
	ExpenseCount   int     `json:"expense_count"`
}

// SavingsSummary provides savings breakdown
type SavingsSummary struct {
	Category    SavingsCategory `json:"category"`
	TotalAmount float64         `json:"total_amount"`
	TargetAmount *float64       `json:"target_amount"`
	Progress    float64         `json:"progress"` // percentage of target
}

// TableName returns the table name for Category
func (Category) TableName() string {
	return "categories"
}

// TableName returns the table name for SubCategory
func (SubCategory) TableName() string {
	return "sub_categories"
}

// TableName returns the table name for Budget
func (Budget) TableName() string {
	return "budgets"
}

// TableName returns the table name for Expense
func (Expense) TableName() string {
	return "expenses"
}

// TableName returns the table name for Savings
func (Savings) TableName() string {
	return "savings"
}
