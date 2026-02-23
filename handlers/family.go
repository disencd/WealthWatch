package handlers

import (
	"net/http"
	"strconv"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type FamilyHandler struct {
	db *gorm.DB
}

func NewFamilyHandler(db *gorm.DB) *FamilyHandler {
	return &FamilyHandler{db: db}
}

type CreateFamilyRequest struct {
	Name     string `json:"name" binding:"required"`
	Currency string `json:"currency"`
}

func (h *FamilyHandler) ListMyFamilies(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	var memberships []models.FamilyMembership
	if err := h.db.Preload("Family").Where("user_id = ? AND status = ?", userID, "active").Find(&memberships).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch families"})
		return
	}

	type familyWithRole struct {
		Family models.Family     `json:"family"`
		Role   models.FamilyRole `json:"role"`
	}

	out := make([]familyWithRole, 0, len(memberships))
	for _, m := range memberships {
		out = append(out, familyWithRole{Family: m.Family, Role: m.Role})
	}

	c.JSON(http.StatusOK, out)
}

func (h *FamilyHandler) CreateFamily(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	var req CreateFamilyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	currency := req.Currency
	if currency == "" {
		currency = "USD"
	}

	family := models.Family{Name: req.Name, Currency: currency, OwnerUserID: userID}
	if err := h.db.Create(&family).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create family"})
		return
	}

	membership := models.FamilyMembership{FamilyID: family.ID, UserID: userID, Role: models.FamilyRoleSuperAdmin, Status: "active"}
	if err := h.db.Create(&membership).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create family membership"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"family": family, "membership": membership})
}

func (h *FamilyHandler) ListMembers(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var members []models.FamilyMembership
	if err := h.db.Preload("User").Where("family_id = ? AND status = ?", familyID, "active").Find(&members).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch members"})
		return
	}

	c.JSON(http.StatusOK, members)
}

type AddFamilyMemberRequest struct {
	Email string            `json:"email" binding:"required,email"`
	Role  models.FamilyRole `json:"role"`
}

func (h *FamilyHandler) AddMember(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var req AddFamilyMemberRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	role := req.Role
	if role == "" {
		role = models.FamilyRoleMember
	}

	if role != models.FamilyRoleAdmin && role != models.FamilyRoleMember {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid role"})
		return
	}

	var user models.User
	if err := h.db.Where("email = ?", req.Email).First(&user).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	var existing models.FamilyMembership
	if err := h.db.Where("family_id = ? AND user_id = ?", familyID, user.ID).First(&existing).Error; err == nil {
		c.JSON(http.StatusConflict, gin.H{"error": "User is already in family"})
		return
	}

	membership := models.FamilyMembership{FamilyID: familyID, UserID: user.ID, Role: role, Status: "active"}
	if err := h.db.Create(&membership).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to add member"})
		return
	}

	h.db.Preload("User").First(&membership, membership.ID)
	c.JSON(http.StatusCreated, membership)
}

type UpdateMemberRoleRequest struct {
	Role models.FamilyRole `json:"role" binding:"required"`
}

func (h *FamilyHandler) UpdateMemberRole(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	memberIDStr := c.Param("memberId")
	memberID, err := strconv.ParseUint(memberIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid memberId"})
		return
	}

	var req UpdateMemberRoleRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Role != models.FamilyRoleAdmin && req.Role != models.FamilyRoleMember {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid role"})
		return
	}

	var member models.FamilyMembership
	if err := h.db.Where("id = ? AND family_id = ?", uint(memberID), familyID).First(&member).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Member not found"})
		return
	}

	if member.Role == models.FamilyRoleSuperAdmin {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Cannot change superadmin role"})
		return
	}

	if err := h.db.Model(&member).Update("role", req.Role).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update role"})
		return
	}

	h.db.Preload("User").First(&member, member.ID)
	c.JSON(http.StatusOK, member)
}

func (h *FamilyHandler) RemoveMember(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	memberIDStr := c.Param("memberId")
	memberID, err := strconv.ParseUint(memberIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid memberId"})
		return
	}

	var member models.FamilyMembership
	if err := h.db.Where("id = ? AND family_id = ?", uint(memberID), familyID).First(&member).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Member not found"})
		return
	}

	if member.Role == models.FamilyRoleSuperAdmin {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Cannot remove superadmin"})
		return
	}

	if err := h.db.Model(&member).Update("status", "removed").Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to remove member"})
		return
	}

	c.Status(http.StatusNoContent)
}
