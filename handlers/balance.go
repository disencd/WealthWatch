package handlers

import (
	"net/http"
	"strconv"

	"splitwise/middleware"
	"splitwise/services"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type BalanceHandler struct {
	db           *gorm.DB
	splitService *services.SplitService
}

func NewBalanceHandler(db *gorm.DB) *BalanceHandler {
	return &BalanceHandler{
		db:           db,
		splitService: services.NewSplitService(db),
	}
}

// GetBalances handles getting user's balances with all other users
func (h *BalanceHandler) GetBalances(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	balances, err := h.splitService.GetAllUserBalances(userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to calculate balances"})
		return
	}

	// Convert to response format with user details
	type BalanceResponse struct {
		UserID  uint    `json:"user_id"`
		Amount  float64 `json:"amount"`
		IsOwed  bool    `json:"is_owed"`  // true if other user owes current user
	}

	var response []BalanceResponse
	for otherUserID, amount := range balances {
		// Get user details
		var user struct {
			ID        uint   `json:"id"`
			FirstName string `json:"first_name"`
			LastName  string `json:"last_name"`
			Email     string `json:"email"`
		}
		
		if err := h.db.Table("users").Select("id, first_name, last_name, email").Where("id = ?", otherUserID).First(&user).Error; err != nil {
			continue // Skip if user not found
		}

		response = append(response, BalanceResponse{
			UserID: otherUserID,
			Amount: amount,
			IsOwed: amount > 0, // Positive balance means other user owes current user
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"balances": response,
	})
}

// GetBalanceWithUser handles getting balance with a specific user
func (h *BalanceHandler) GetBalanceWithUser(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	otherUserIDStr := c.Param("userId")
	otherUserID, err := strconv.ParseUint(otherUserIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid user ID"})
		return
	}

	balance, err := h.splitService.GetUserBalance(userID, uint(otherUserID))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to calculate balance"})
		return
	}

	// Get other user details
	var otherUser struct {
		ID        uint   `json:"id"`
		FirstName string `json:"first_name"`
		LastName  string `json:"last_name"`
		Email     string `json:"email"`
	}
	
	if err := h.db.Table("users").Select("id, first_name, last_name, email").Where("id = ?", otherUserID).First(&otherUser).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"user":    otherUser,
		"balance": balance,
		"is_owed": balance > 0, // Positive balance means other user owes current user
	})
}
