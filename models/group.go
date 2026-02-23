package models

import (
	"time"

	"gorm.io/gorm"
)

// Group represents a group of users who share expenses
type Group struct {
	ID          uint           `gorm:"primaryKey" json:"id"`
	Name        string         `gorm:"not null" json:"name"`
	Description string         `json:"description"`
	Avatar      string         `json:"avatar"`
	CreatedBy   uint           `gorm:"not null" json:"created_by"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	Members  []User     `gorm:"many2many:group_members;" json:"members,omitempty"`
	Expenses []Expense  `gorm:"foreignKey:GroupID" json:"expenses,omitempty"`
	Creator  User       `gorm:"foreignKey:CreatedBy" json:"creator,omitempty"`
}

// GroupMember represents the join table between users and groups
type GroupMember struct {
	ID        uint           `gorm:"primaryKey" json:"id"`
	GroupID   uint           `gorm:"not null" json:"group_id"`
	UserID    uint           `gorm:"not null" json:"user_id"`
	JoinedAt  time.Time      `gorm:"autoCreateTime" json:"joined_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`

	// Relationships
	Group Group `gorm:"foreignKey:GroupID" json:"group,omitempty"`
	User  User  `gorm:"foreignKey:UserID" json:"user,omitempty"`
}

// TableName returns the table name for Group model
func (Group) TableName() string {
	return "groups"
}

// TableName returns the table name for GroupMember model
func (GroupMember) TableName() string {
	return "group_members"
}
