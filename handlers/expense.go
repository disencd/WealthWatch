package handlers

import (
	"errors"
	"net/http"
	"strconv"
	"time"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type ExpenseHandler struct {
	db *gorm.DB
}

func NewExpenseHandler(db *gorm.DB) *ExpenseHandler {
	return &ExpenseHandler{db: db}
}

type CreateExpenseRequest struct {
	Title       string               `json:"title" binding:"required"`
	Description string               `json:"description"`
	Amount      float64              `json:"amount" binding:"required,gt=0"`
	Currency    string               `json:"currency"`
	Date        string               `json:"date" binding:"required"`
	GroupID     *uint                `json:"group_id"`
	Category    string               `json:"category"`
	Splits      []CreateSplitRequest `json:"splits" binding:"required,min=1"`
}

type CreateSplitRequest struct {
	UserID     uint    `json:"user_id" binding:"required"`
	Amount     float64 `json:"amount" binding:"required,gt=0"`
	Percentage float64 `json:"percentage"`
}

// CreateExpense handles creating a new expense
func (h *ExpenseHandler) CreateExpense(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	var req CreateExpenseRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Parse date
	date, err := parseDate(req.Date)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid date format"})
		return
	}

	// Validate split amounts sum equals expense amount
	totalSplitAmount := 0.0
	for _, split := range req.Splits {
		totalSplitAmount += split.Amount
	}

	if totalSplitAmount != req.Amount {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Split amounts must equal expense amount"})
		return
	}

	// Create expense
	expense := models.Expense{
		Title:       req.Title,
		Description: req.Description,
		Amount:      req.Amount,
		Currency:    req.Currency,
		Date:        date,
		PayerID:     userID,
		GroupID:     req.GroupID,
		Category:    req.Category,
	}

	// Start transaction
	tx := h.db.Begin()

	if err := tx.Create(&expense).Error; err != nil {
		tx.Rollback()
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create expense"})
		return
	}

	// Create splits
	for _, splitReq := range req.Splits {
		split := models.Split{
			ExpenseID:  expense.ID,
			UserID:     splitReq.UserID,
			Amount:     splitReq.Amount,
			Percentage: splitReq.Percentage,
		}

		if err := tx.Create(&split).Error; err != nil {
			tx.Rollback()
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create splits"})
			return
		}
	}

	tx.Commit()

	// Load expense with relationships
	h.db.Preload("Payer").Preload("Splits.User").Preload("Group").First(&expense, expense.ID)

	c.JSON(http.StatusCreated, expense)
}

// GetExpenses handles getting user's expenses
func (h *ExpenseHandler) GetExpenses(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	// Parse query parameters
	groupIDStr := c.Query("group_id")
	pageStr := c.DefaultQuery("page", "1")
	limitStr := c.DefaultQuery("limit", "10")

	page, _ := strconv.Atoi(pageStr)
	limit, _ := strconv.Atoi(limitStr)
	offset := (page - 1) * limit

	var expenses []models.Expense
	query := h.db.Model(&models.Expense{}).Preload("Payer").Preload("Splits.User").Preload("Group")

	// Filter by group if specified
	if groupIDStr != "" {
		groupID, err := strconv.ParseUint(groupIDStr, 10, 32)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid group ID"})
			return
		}
		query = query.Where("group_id = ?", uint(groupID))
	}

	// Get expenses where user is either payer or has a split
	query = query.Where("payer_id = ? OR id IN (SELECT expense_id FROM splits WHERE user_id = ?)", userID, userID)

	if err := query.Order("date DESC, created_at DESC").Limit(limit).Offset(offset).Find(&expenses).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch expenses"})
		return
	}

	c.JSON(http.StatusOK, expenses)
}

// GetExpense handles getting a specific expense
func (h *ExpenseHandler) GetExpense(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	expenseIDStr := c.Param("id")
	expenseID, err := strconv.ParseUint(expenseIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid expense ID"})
		return
	}

	var expense models.Expense
	if err := h.db.Preload("Payer").Preload("Splits.User").Preload("Group").First(&expense, expenseID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Expense not found"})
		return
	}

	// Check if user has access to this expense
	hasAccess := expense.PayerID == userID
	for _, split := range expense.Splits {
		if split.UserID == userID {
			hasAccess = true
			break
		}
	}

	if !hasAccess {
		c.JSON(http.StatusForbidden, gin.H{"error": "Access denied"})
		return
	}

	c.JSON(http.StatusOK, expense)
}

// Helper function to parse date string
func parseDate(dateStr string) (time.Time, error) {
	// Try to parse as RFC3339 format first
	if t, err := time.Parse(time.RFC3339, dateStr); err == nil {
		return t, nil
	}

	// Try other common formats
	formats := []string{
		"2006-01-02",
		"2006-01-02T15:04:05Z",
		"2006-01-02 15:04:05",
	}

	for _, format := range formats {
		if t, err := time.Parse(format, dateStr); err == nil {
			return t, nil
		}
	}

	return time.Time{}, errors.New("invalid date format")
}

// parseToday returns today's date at midnight UTC
func parseToday() time.Time {
	now := time.Now().UTC()
	return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC)
}
