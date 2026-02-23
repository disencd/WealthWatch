package handlers

import (
	"net/http"
	"strconv"

	"splitwise/middleware"
	"splitwise/models"
	"splitwise/services"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type SettlementHandler struct {
	db           *gorm.DB
	splitService *services.SplitService
}

func NewSettlementHandler(db *gorm.DB) *SettlementHandler {
	return &SettlementHandler{
		db:           db,
		splitService: services.NewSplitService(db),
	}
}

type CreateSettlementRequest struct {
	ToUserID      uint    `json:"to_user_id" binding:"required"`
	Amount        float64 `json:"amount" binding:"required,gt=0"`
	Currency      string  `json:"currency"`
	PaymentMethod string  `json:"payment_method"`
	Notes         string  `json:"notes"`
}

// CreateSettlement handles creating a new settlement
func (h *SettlementHandler) CreateSettlement(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	var req CreateSettlementRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Validate that the settlement amount doesn't exceed the actual balance
	currentBalance, err := h.splitService.GetUserBalance(req.ToUserID, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to verify balance"})
		return
	}

	// currentBalance > 0 means to_user owes from_user
	// So from_user (current user) can receive up to currentBalance amount
	if currentBalance < req.Amount {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Settlement amount exceeds actual balance"})
		return
	}

	// Create settlement
	settlement := models.Settlement{
		FromUserID:    userID,
		ToUserID:      req.ToUserID,
		Amount:        req.Amount,
		Currency:      req.Currency,
		Status:        "pending",
		PaymentMethod: req.PaymentMethod,
		Notes:         req.Notes,
	}

	if err := h.db.Create(&settlement).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create settlement"})
		return
	}

	// Load settlement with relationships
	h.db.Preload("FromUser").Preload("ToUser").First(&settlement, settlement.ID)

	c.JSON(http.StatusCreated, settlement)
}

// GetSettlements handles getting user's settlements
func (h *SettlementHandler) GetSettlements(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	// Parse query parameters
	status := c.Query("status")
	pageStr := c.DefaultQuery("page", "1")
	limitStr := c.DefaultQuery("limit", "10")

	page, _ := strconv.Atoi(pageStr)
	limit, _ := strconv.Atoi(limitStr)
	offset := (page - 1) * limit

	var settlements []models.Settlement
	query := h.db.Model(&models.Settlement{}).Preload("FromUser").Preload("ToUser")

	// Filter by status if specified
	if status != "" {
		query = query.Where("status = ?", status)
	}

	// Get settlements where user is either from_user or to_user
	query = query.Where("from_user_id = ? OR to_user_id = ?", userID, userID)

	if err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&settlements).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch settlements"})
		return
	}

	c.JSON(http.StatusOK, settlements)
}

// UpdateSettlementStatus handles updating settlement status
func (h *SettlementHandler) UpdateSettlementStatus(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	settlementIDStr := c.Param("id")
	settlementID, err := strconv.ParseUint(settlementIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid settlement ID"})
		return
	}

	var req struct {
		Status string `json:"status" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Validate status
	validStatuses := map[string]bool{
		"pending":   true,
		"completed": true,
		"cancelled": true,
	}

	if !validStatuses[req.Status] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid status"})
		return
	}

	// Get settlement
	var settlement models.Settlement
	if err := h.db.First(&settlement, settlementID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Settlement not found"})
		return
	}

	// Check if user has permission to update this settlement
	// Only the to_user can mark as completed, only from_user can cancel
	if (req.Status == "completed" && settlement.ToUserID != userID) ||
		(req.Status == "cancelled" && settlement.FromUserID != userID) {
		c.JSON(http.StatusForbidden, gin.H{"error": "Permission denied"})
		return
	}

	// Update settlement
	if err := h.db.Model(&settlement).Update("status", req.Status).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update settlement"})
		return
	}

	// Load updated settlement with relationships
	h.db.Preload("FromUser").Preload("ToUser").First(&settlement, settlement.ID)

	c.JSON(http.StatusOK, settlement)
}

// GetSettlement handles getting a specific settlement
func (h *SettlementHandler) GetSettlement(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	settlementIDStr := c.Param("id")
	settlementID, err := strconv.ParseUint(settlementIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid settlement ID"})
		return
	}

	var settlement models.Settlement
	if err := h.db.Preload("FromUser").Preload("ToUser").First(&settlement, settlementID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Settlement not found"})
		return
	}

	// Check if user has access to this settlement
	if settlement.FromUserID != userID && settlement.ToUserID != userID {
		c.JSON(http.StatusForbidden, gin.H{"error": "Access denied"})
		return
	}

	c.JSON(http.StatusOK, settlement)
}
