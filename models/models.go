package models

import (
	"gorm.io/gorm"
)

// AutoMigrate runs database migrations for all models
func AutoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(
		&User{},
		&Family{},
		&FamilyMembership{},
		&Category{},
		&SubCategory{},
		&Budget{},
		&BudgetExpense{},
		&Group{},
		&GroupMember{},
		&Expense{},
		&Split{},
		&Settlement{},
	)
}
