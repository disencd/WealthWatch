package models

import (
	"time"

	"gorm.io/gorm"
)

type InvestmentType string

const (
	InvestmentTypeStock  InvestmentType = "stock"
	InvestmentTypeBond   InvestmentType = "bond"
	InvestmentTypeETF    InvestmentType = "etf"
	InvestmentTypeMutual InvestmentType = "mutual_fund"
	InvestmentTypeCrypto InvestmentType = "crypto"
	InvestmentTypeCash   InvestmentType = "cash"
	InvestmentTypeOther  InvestmentType = "other"
)

type InvestmentHolding struct {
	ID             uint           `gorm:"primaryKey" json:"id"`
	AccountID      uint           `gorm:"not null;index" json:"account_id"`
	FamilyID       uint           `gorm:"not null;index" json:"family_id"`
	Symbol         string         `gorm:"not null" json:"symbol"`
	Name           string         `gorm:"not null" json:"name"`
	InvestmentType InvestmentType `gorm:"type:varchar(32);not null" json:"investment_type"`
	Quantity       float64        `gorm:"not null;default:0" json:"quantity"`
	CostBasis      float64        `gorm:"not null;default:0" json:"cost_basis"`
	CurrentPrice   float64        `gorm:"not null;default:0" json:"current_price"`
	CurrentValue   float64        `gorm:"not null;default:0" json:"current_value"`
	GainLoss       float64        `gorm:"not null;default:0" json:"gain_loss"`
	GainLossPercent float64       `gorm:"not null;default:0" json:"gain_loss_percent"`
	LastUpdatedAt  time.Time      `json:"last_updated_at"`
	CreatedAt      time.Time      `json:"created_at"`
	UpdatedAt      time.Time      `json:"updated_at"`
	DeletedAt      gorm.DeletedAt `gorm:"index" json:"-"`

	Account Account `gorm:"foreignKey:AccountID" json:"account,omitempty"`
	Family  Family  `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
}

func (InvestmentHolding) TableName() string { return "investment_holdings" }
