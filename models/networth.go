package models

import (
	"time"

	"gorm.io/gorm"
)

type NetWorthSnapshot struct {
	ID              uint           `gorm:"primaryKey" json:"id"`
	FamilyID        uint           `gorm:"not null;index" json:"family_id"`
	Date            time.Time      `gorm:"not null;index" json:"date"`
	TotalAssets     float64        `gorm:"not null;default:0" json:"total_assets"`
	TotalLiabilities float64      `gorm:"not null;default:0" json:"total_liabilities"`
	NetWorth        float64        `gorm:"not null;default:0" json:"net_worth"`
	CreatedAt       time.Time      `json:"created_at"`
	UpdatedAt       time.Time      `json:"updated_at"`
	DeletedAt       gorm.DeletedAt `gorm:"index" json:"-"`

	Family Family `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
}

func (NetWorthSnapshot) TableName() string { return "net_worth_snapshots" }
