package models

import (
	"time"

	"gorm.io/gorm"
)

type AccountType string

const (
	AccountTypeChecking   AccountType = "checking"
	AccountTypeSavings    AccountType = "savings"
	AccountTypeCreditCard AccountType = "credit_card"
	AccountTypeInvestment AccountType = "investment"
	AccountTypeLoan       AccountType = "loan"
	AccountTypeMortgage   AccountType = "mortgage"
	AccountTypeRealEstate AccountType = "real_estate"
	AccountTypeOther      AccountType = "other"
)

type AccountOwnership string

const (
	OwnershipYours AccountOwnership = "yours"
	OwnershipMine  AccountOwnership = "mine"
	OwnershipOurs  AccountOwnership = "ours"
)

type Account struct {
	ID              uint             `gorm:"primaryKey" json:"id"`
	FamilyID        uint             `gorm:"not null;index" json:"family_id"`
	CreatedByUserID uint             `gorm:"not null" json:"created_by_user_id"`
	InstitutionName string           `gorm:"not null" json:"institution_name"`
	AccountName     string           `gorm:"not null" json:"account_name"`
	AccountType     AccountType      `gorm:"type:varchar(32);not null" json:"account_type"`
	Ownership       AccountOwnership `gorm:"type:varchar(16);not null;default:'ours'" json:"ownership"`
	Balance         float64          `gorm:"not null;default:0" json:"balance"`
	Currency        string           `gorm:"not null;default:'USD'" json:"currency"`
	IsAsset         bool             `gorm:"not null;default:true" json:"is_asset"`
	IsActive        bool             `gorm:"not null;default:true" json:"is_active"`
	LastSyncedAt    *time.Time       `json:"last_synced_at"`
	PlaidItemID     string           `json:"plaid_item_id,omitempty"`
	PlaidAccountID  string           `json:"plaid_account_id,omitempty"`
	CreatedAt       time.Time        `json:"created_at"`
	UpdatedAt       time.Time        `json:"updated_at"`
	DeletedAt       gorm.DeletedAt   `gorm:"index" json:"-"`

	Family        Family `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	CreatedByUser User   `gorm:"foreignKey:CreatedByUserID" json:"created_by_user,omitempty"`
}

func (Account) TableName() string { return "accounts" }
