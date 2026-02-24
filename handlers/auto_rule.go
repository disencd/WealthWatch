package handlers

import (
	"net/http"
	"strconv"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AutoRuleHandler struct {
	db *gorm.DB
}

func NewAutoRuleHandler(db *gorm.DB) *AutoRuleHandler {
	return &AutoRuleHandler{db: db}
}

type CreateAutoRuleRequest struct {
	MerchantPattern string   `json:"merchant_pattern" binding:"required"`
	MinAmount       *float64 `json:"min_amount"`
	MaxAmount       *float64 `json:"max_amount"`
	CategoryID      uint     `json:"category_id" binding:"required"`
	SubCategoryID   *uint    `json:"sub_category_id"`
	Priority        int      `json:"priority"`
}

func (h *AutoRuleHandler) CreateRule(c *gin.Context) {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var req CreateAutoRuleRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var cat models.Category
	if err := h.db.Where("id = ? AND family_id = ?", req.CategoryID, familyID).First(&cat).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid category"})
		return
	}

	rule := models.AutoCategoryRule{
		FamilyID:        familyID,
		CreatedByUserID: userID,
		MerchantPattern: req.MerchantPattern,
		MinAmount:       req.MinAmount,
		MaxAmount:       req.MaxAmount,
		CategoryID:      req.CategoryID,
		SubCategoryID:   req.SubCategoryID,
		IsActive:        true,
		Priority:        req.Priority,
	}

	if err := h.db.Create(&rule).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create rule"})
		return
	}

	h.db.Preload("Category").Preload("SubCategory").First(&rule, rule.ID)
	c.JSON(http.StatusCreated, rule)
}

func (h *AutoRuleHandler) ListRules(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var rules []models.AutoCategoryRule
	if err := h.db.Preload("Category").Preload("SubCategory").
		Where("family_id = ?", familyID).
		Order("priority DESC, merchant_pattern ASC").
		Find(&rules).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch rules"})
		return
	}

	c.JSON(http.StatusOK, rules)
}

func (h *AutoRuleHandler) UpdateRule(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
		return
	}

	var rule models.AutoCategoryRule
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&rule).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.db.Model(&rule).Updates(body).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update rule"})
		return
	}

	h.db.Preload("Category").Preload("SubCategory").First(&rule, rule.ID)
	c.JSON(http.StatusOK, rule)
}

func (h *AutoRuleHandler) DeleteRule(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
		return
	}

	var rule models.AutoCategoryRule
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&rule).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Rule not found"})
		return
	}

	if err := h.db.Delete(&rule).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete rule"})
		return
	}

	c.Status(http.StatusNoContent)
}
