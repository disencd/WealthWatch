package models

import (
	"time"

	"gorm.io/gorm"
)

type FamilyRole string

const (
	FamilyRoleSuperAdmin FamilyRole = "superadmin"
	FamilyRoleAdmin      FamilyRole = "admin"
	FamilyRoleMember     FamilyRole = "member"
)

type Family struct {
	ID          uint           `gorm:"primaryKey" json:"id"`
	Name        string         `gorm:"not null" json:"name"`
	Currency    string         `gorm:"not null;default:'USD'" json:"currency"`
	OwnerUserID uint           `gorm:"not null" json:"owner_user_id"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`

	Owner   User               `gorm:"foreignKey:OwnerUserID" json:"owner,omitempty"`
	Members []FamilyMembership `gorm:"foreignKey:FamilyID" json:"members,omitempty"`
}

type FamilyMembership struct {
	ID        uint           `gorm:"primaryKey" json:"id"`
	FamilyID  uint           `gorm:"not null;index" json:"family_id"`
	UserID    uint           `gorm:"not null;index" json:"user_id"`
	Role      FamilyRole     `gorm:"type:varchar(32);not null" json:"role"`
	Status    string         `gorm:"type:varchar(32);not null;default:'active'" json:"status"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`

	Family Family `gorm:"foreignKey:FamilyID" json:"family,omitempty"`
	User   User   `gorm:"foreignKey:UserID" json:"user,omitempty"`
}
