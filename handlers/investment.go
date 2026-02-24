package handlers

import (
	"net/http"
	"strconv"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type InvestmentHandler struct {
	db *gorm.DB
}

func NewInvestmentHandler(db *gorm.DB) *InvestmentHandler {
	return &InvestmentHandler{db: db}
}

type CreateHoldingRequest struct {
	AccountID      uint                 `json:"account_id" binding:"required"`
	Symbol         string               `json:"symbol" binding:"required"`
	Name           string               `json:"name" binding:"required"`
	InvestmentType models.InvestmentType `json:"investment_type" binding:"required"`
	Quantity       float64              `json:"quantity" binding:"required"`
	CostBasis      float64              `json:"cost_basis" binding:"required"`
	CurrentPrice   float64              `json:"current_price" binding:"required"`
}

func (h *InvestmentHandler) CreateHolding(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var req CreateHoldingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var account models.Account
	if err := h.db.Where("id = ? AND family_id = ?", req.AccountID, familyID).First(&account).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid account"})
		return
	}

	currentValue := req.Quantity * req.CurrentPrice
	gainLoss := currentValue - req.CostBasis
	var gainLossPercent float64
	if req.CostBasis > 0 {
		gainLossPercent = (gainLoss / req.CostBasis) * 100
	}

	holding := models.InvestmentHolding{
		AccountID:       req.AccountID,
		FamilyID:        familyID,
		Symbol:          req.Symbol,
		Name:            req.Name,
		InvestmentType:  req.InvestmentType,
		Quantity:        req.Quantity,
		CostBasis:       req.CostBasis,
		CurrentPrice:    req.CurrentPrice,
		CurrentValue:    currentValue,
		GainLoss:        gainLoss,
		GainLossPercent: gainLossPercent,
		LastUpdatedAt:   parseToday(),
	}

	if err := h.db.Create(&holding).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create holding"})
		return
	}

	c.JSON(http.StatusCreated, holding)
}

func (h *InvestmentHandler) ListHoldings(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var holdings []models.InvestmentHolding
	q := h.db.Preload("Account").Where("family_id = ?", familyID).Order("current_value DESC")

	if accountID := c.Query("account_id"); accountID != "" {
		q = q.Where("account_id = ?", accountID)
	}
	if investmentType := c.Query("type"); investmentType != "" {
		q = q.Where("investment_type = ?", investmentType)
	}

	if err := q.Find(&holdings).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch holdings"})
		return
	}

	c.JSON(http.StatusOK, holdings)
}

func (h *InvestmentHandler) GetPortfolioSummary(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var holdings []models.InvestmentHolding
	if err := h.db.Where("family_id = ?", familyID).Find(&holdings).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch holdings"})
		return
	}

	var totalValue, totalCostBasis, totalGainLoss float64
	allocationByType := map[string]float64{}

	for _, h := range holdings {
		totalValue += h.CurrentValue
		totalCostBasis += h.CostBasis
		totalGainLoss += h.GainLoss
		allocationByType[string(h.InvestmentType)] += h.CurrentValue
	}

	var totalGainLossPercent float64
	if totalCostBasis > 0 {
		totalGainLossPercent = (totalGainLoss / totalCostBasis) * 100
	}

	allocationPercent := map[string]float64{}
	if totalValue > 0 {
		for k, v := range allocationByType {
			allocationPercent[k] = (v / totalValue) * 100
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"total_value":          totalValue,
		"total_cost_basis":     totalCostBasis,
		"total_gain_loss":      totalGainLoss,
		"total_gain_loss_pct":  totalGainLossPercent,
		"allocation_by_type":   allocationByType,
		"allocation_percent":   allocationPercent,
		"holding_count":        len(holdings),
	})
}

type UpdateHoldingRequest struct {
	CurrentPrice *float64 `json:"current_price"`
	Quantity     *float64 `json:"quantity"`
}

func (h *InvestmentHandler) UpdateHolding(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid holding ID"})
		return
	}

	var holding models.InvestmentHolding
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&holding).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Holding not found"})
		return
	}

	var req UpdateHoldingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.CurrentPrice != nil {
		holding.CurrentPrice = *req.CurrentPrice
	}
	if req.Quantity != nil {
		holding.Quantity = *req.Quantity
	}

	holding.CurrentValue = holding.Quantity * holding.CurrentPrice
	holding.GainLoss = holding.CurrentValue - holding.CostBasis
	if holding.CostBasis > 0 {
		holding.GainLossPercent = (holding.GainLoss / holding.CostBasis) * 100
	}
	holding.LastUpdatedAt = parseToday()

	if err := h.db.Save(&holding).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update holding"})
		return
	}

	c.JSON(http.StatusOK, holding)
}

func (h *InvestmentHandler) DeleteHolding(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid holding ID"})
		return
	}

	var holding models.InvestmentHolding
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&holding).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Holding not found"})
		return
	}

	if err := h.db.Delete(&holding).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete holding"})
		return
	}

	c.Status(http.StatusNoContent)
}
