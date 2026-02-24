package handlers

import (
	"net/http"
	"strconv"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AccountHandler struct {
	db *gorm.DB
}

func NewAccountHandler(db *gorm.DB) *AccountHandler {
	return &AccountHandler{db: db}
}

type CreateAccountRequest struct {
	InstitutionName string                 `json:"institution_name" binding:"required"`
	AccountName     string                 `json:"account_name" binding:"required"`
	AccountType     models.AccountType     `json:"account_type" binding:"required"`
	Ownership       models.AccountOwnership `json:"ownership"`
	Balance         float64                `json:"balance"`
	Currency        string                 `json:"currency"`
	IsAsset         *bool                  `json:"is_asset"`
}

func (h *AccountHandler) CreateAccount(c *gin.Context) {
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

	var req CreateAccountRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ownership := req.Ownership
	if ownership == "" {
		ownership = models.OwnershipOurs
	}
	currency := req.Currency
	if currency == "" {
		currency = "USD"
	}
	isAsset := true
	if req.IsAsset != nil {
		isAsset = *req.IsAsset
	}
	if req.AccountType == models.AccountTypeCreditCard || req.AccountType == models.AccountTypeLoan || req.AccountType == models.AccountTypeMortgage {
		isAsset = false
	}

	account := models.Account{
		FamilyID:        familyID,
		CreatedByUserID: userID,
		InstitutionName: req.InstitutionName,
		AccountName:     req.AccountName,
		AccountType:     req.AccountType,
		Ownership:       ownership,
		Balance:         req.Balance,
		Currency:        currency,
		IsAsset:         isAsset,
		IsActive:        true,
	}

	if err := h.db.Create(&account).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create account"})
		return
	}

	c.JSON(http.StatusCreated, account)
}

func (h *AccountHandler) ListAccounts(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var accounts []models.Account
	q := h.db.Where("family_id = ? AND is_active = ?", familyID, true).Order("account_type ASC, account_name ASC")

	if accountType := c.Query("type"); accountType != "" {
		q = q.Where("account_type = ?", accountType)
	}
	if ownership := c.Query("ownership"); ownership != "" {
		q = q.Where("ownership = ?", ownership)
	}

	if err := q.Find(&accounts).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch accounts"})
		return
	}

	c.JSON(http.StatusOK, accounts)
}

func (h *AccountHandler) GetAccount(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid account ID"})
		return
	}

	var account models.Account
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&account).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Account not found"})
		return
	}

	c.JSON(http.StatusOK, account)
}

type UpdateAccountRequest struct {
	AccountName     string                  `json:"account_name"`
	Balance         *float64                `json:"balance"`
	Ownership       models.AccountOwnership `json:"ownership"`
	IsActive        *bool                   `json:"is_active"`
}

func (h *AccountHandler) UpdateAccount(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid account ID"})
		return
	}

	var account models.Account
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&account).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Account not found"})
		return
	}

	var req UpdateAccountRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	updates := map[string]interface{}{}
	if req.AccountName != "" {
		updates["account_name"] = req.AccountName
	}
	if req.Balance != nil {
		updates["balance"] = *req.Balance
	}
	if req.Ownership != "" {
		updates["ownership"] = req.Ownership
	}
	if req.IsActive != nil {
		updates["is_active"] = *req.IsActive
	}

	if err := h.db.Model(&account).Updates(updates).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update account"})
		return
	}

	h.db.First(&account, account.ID)
	c.JSON(http.StatusOK, account)
}

func (h *AccountHandler) DeleteAccount(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid account ID"})
		return
	}

	var account models.Account
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&account).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Account not found"})
		return
	}

	if err := h.db.Delete(&account).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete account"})
		return
	}

	c.Status(http.StatusNoContent)
}

func (h *AccountHandler) GetNetWorthSummary(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var accounts []models.Account
	if err := h.db.Where("family_id = ? AND is_active = ?", familyID, true).Find(&accounts).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch accounts"})
		return
	}

	var totalAssets, totalLiabilities float64
	assetsByType := map[string]float64{}
	liabilitiesByType := map[string]float64{}

	for _, acc := range accounts {
		if acc.IsAsset {
			totalAssets += acc.Balance
			assetsByType[string(acc.AccountType)] += acc.Balance
		} else {
			totalLiabilities += acc.Balance
			liabilitiesByType[string(acc.AccountType)] += acc.Balance
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"total_assets":        totalAssets,
		"total_liabilities":   totalLiabilities,
		"net_worth":           totalAssets - totalLiabilities,
		"assets_by_type":      assetsByType,
		"liabilities_by_type": liabilitiesByType,
		"account_count":       len(accounts),
	})
}

func (h *AccountHandler) GetNetWorthHistory(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var snapshots []models.NetWorthSnapshot
	q := h.db.Where("family_id = ?", familyID).Order("date ASC")

	if limit := c.Query("limit"); limit != "" {
		if l, err := strconv.Atoi(limit); err == nil {
			q = q.Limit(l)
		}
	}

	if err := q.Find(&snapshots).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch net worth history"})
		return
	}

	c.JSON(http.StatusOK, snapshots)
}

func (h *AccountHandler) SnapshotNetWorth(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var accounts []models.Account
	if err := h.db.Where("family_id = ? AND is_active = ?", familyID, true).Find(&accounts).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch accounts"})
		return
	}

	var totalAssets, totalLiabilities float64
	for _, acc := range accounts {
		if acc.IsAsset {
			totalAssets += acc.Balance
		} else {
			totalLiabilities += acc.Balance
		}
	}

	snapshot := models.NetWorthSnapshot{
		FamilyID:         familyID,
		Date:             parseToday(),
		TotalAssets:      totalAssets,
		TotalLiabilities: totalLiabilities,
		NetWorth:         totalAssets - totalLiabilities,
	}

	if err := h.db.Create(&snapshot).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create snapshot"})
		return
	}

	c.JSON(http.StatusCreated, snapshot)
}
