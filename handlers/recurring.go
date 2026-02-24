package handlers

import (
	"net/http"
	"strconv"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type RecurringHandler struct {
	db *gorm.DB
}

func NewRecurringHandler(db *gorm.DB) *RecurringHandler {
	return &RecurringHandler{db: db}
}

type CreateRecurringRequest struct {
	Merchant      string                    `json:"merchant" binding:"required"`
	Amount        float64                   `json:"amount" binding:"required,gt=0"`
	Currency      string                    `json:"currency"`
	Frequency     models.RecurringFrequency `json:"frequency" binding:"required"`
	CategoryID    *uint                     `json:"category_id"`
	SubCategoryID *uint                     `json:"sub_category_id"`
	NextDueDate   string                    `json:"next_due_date" binding:"required"`
	Notes         string                    `json:"notes"`
}

func (h *RecurringHandler) CreateRecurring(c *gin.Context) {
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

	var req CreateRecurringRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	nextDue, err := parseDate(req.NextDueDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid next_due_date format"})
		return
	}

	currency := req.Currency
	if currency == "" {
		currency = "USD"
	}

	rec := models.RecurringTransaction{
		FamilyID:        familyID,
		CreatedByUserID: userID,
		Merchant:        req.Merchant,
		Amount:          req.Amount,
		Currency:        currency,
		Frequency:       req.Frequency,
		CategoryID:      req.CategoryID,
		SubCategoryID:   req.SubCategoryID,
		NextDueDate:     nextDue,
		IsActive:        true,
		AutoDetected:    false,
		Notes:           req.Notes,
	}

	if err := h.db.Create(&rec).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create recurring transaction"})
		return
	}

	h.db.Preload("Category").Preload("SubCategory").First(&rec, rec.ID)
	c.JSON(http.StatusCreated, rec)
}

func (h *RecurringHandler) ListRecurring(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var items []models.RecurringTransaction
	q := h.db.Preload("Category").Preload("SubCategory").Where("family_id = ?", familyID).Order("next_due_date ASC")

	if active := c.Query("active"); active != "" {
		q = q.Where("is_active = ?", active == "true")
	}

	if err := q.Find(&items).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch recurring transactions"})
		return
	}

	c.JSON(http.StatusOK, items)
}

func (h *RecurringHandler) UpdateRecurring(c *gin.Context) {
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

	var rec models.RecurringTransaction
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&rec).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Recurring transaction not found"})
		return
	}

	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.db.Model(&rec).Updates(body).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update"})
		return
	}

	h.db.Preload("Category").Preload("SubCategory").First(&rec, rec.ID)
	c.JSON(http.StatusOK, rec)
}

func (h *RecurringHandler) DeleteRecurring(c *gin.Context) {
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

	var rec models.RecurringTransaction
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&rec).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Not found"})
		return
	}

	if err := h.db.Delete(&rec).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete"})
		return
	}

	c.Status(http.StatusNoContent)
}

func (h *RecurringHandler) GetUpcoming(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var items []models.RecurringTransaction
	if err := h.db.Preload("Category").Preload("SubCategory").
		Where("family_id = ? AND is_active = ? AND next_due_date <= NOW() + INTERVAL '30 days'", familyID, true).
		Order("next_due_date ASC").
		Find(&items).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch upcoming"})
		return
	}

	c.JSON(http.StatusOK, items)
}
