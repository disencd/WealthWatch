package handlers

import (
	"net/http"
	"strconv"
	"time"

	"splitwise/middleware"
	"splitwise/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type BudgetTrackerHandler struct {
	db *gorm.DB
}

func NewBudgetTrackerHandler(db *gorm.DB) *BudgetTrackerHandler {
	return &BudgetTrackerHandler{db: db}
}

type CreateCategoryRequest struct {
	Type        models.CategoryType `json:"type" binding:"required"`
	Name        string              `json:"name" binding:"required"`
	Description string              `json:"description"`
}

func (h *BudgetTrackerHandler) ListCategories(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var categories []models.Category
	q := h.db.Where("family_id = ?", familyID).Order("type ASC, name ASC")
	if t := c.Query("type"); t != "" {
		q = q.Where("type = ?", t)
	}

	if err := q.Find(&categories).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch categories"})
		return
	}

	c.JSON(http.StatusOK, categories)
}

func (h *BudgetTrackerHandler) CreateCategory(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var req CreateCategoryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Type != models.CategoryTypeExpense && req.Type != models.CategoryTypeSavings {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid category type"})
		return
	}

	cat := models.Category{FamilyID: familyID, Type: req.Type, Name: req.Name, Description: req.Description, IsActive: true}
	if err := h.db.Create(&cat).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create category"})
		return
	}

	c.JSON(http.StatusCreated, cat)
}

type CreateSubCategoryRequest struct {
	CategoryID  uint   `json:"category_id" binding:"required"`
	Name        string `json:"name" binding:"required"`
	Description string `json:"description"`
}

func (h *BudgetTrackerHandler) ListSubCategories(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var subs []models.SubCategory
	q := h.db.Preload("Category").Where("sub_categories.family_id = ?", familyID).Order("name ASC")
	if categoryID := c.Query("category_id"); categoryID != "" {
		q = q.Where("category_id = ?", categoryID)
	}

	if err := q.Find(&subs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch subcategories"})
		return
	}

	c.JSON(http.StatusOK, subs)
}

func (h *BudgetTrackerHandler) CreateSubCategory(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var req CreateSubCategoryRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Ensure category belongs to family
	var cat models.Category
	if err := h.db.Where("id = ? AND family_id = ?", req.CategoryID, familyID).First(&cat).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid category"})
		return
	}

	sub := models.SubCategory{FamilyID: familyID, CategoryID: req.CategoryID, Name: req.Name, Description: req.Description, IsActive: true}
	if err := h.db.Create(&sub).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create subcategory"})
		return
	}

	h.db.Preload("Category").First(&sub, sub.ID)
	c.JSON(http.StatusCreated, sub)
}

type CreateBudgetRequest struct {
	CategoryID    *uint              `json:"category_id"`
	SubCategoryID *uint              `json:"sub_category_id"`
	Period        models.BudgetPeriod `json:"period" binding:"required"`
	Year          int                `json:"year" binding:"required"`
	Month         *int               `json:"month"`
	Amount        float64            `json:"amount" binding:"required,gt=0"`
}

func (h *BudgetTrackerHandler) ListBudgets(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var budgets []models.Budget
	q := h.db.Preload("Category").Preload("SubCategory").Where("family_id = ?", familyID).Order("year DESC, month DESC")
	if year := c.Query("year"); year != "" {
		q = q.Where("year = ?", year)
	}
	if month := c.Query("month"); month != "" {
		q = q.Where("month = ?", month)
	}

	if err := q.Find(&budgets).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch budgets"})
		return
	}

	c.JSON(http.StatusOK, budgets)
}

func (h *BudgetTrackerHandler) CreateBudget(c *gin.Context) {
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

	var req CreateBudgetRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Period != models.BudgetPeriodMonthly && req.Period != models.BudgetPeriodYearly {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid period"})
		return
	}
	if req.Period == models.BudgetPeriodMonthly {
		if req.Month == nil || *req.Month < 1 || *req.Month > 12 {
			c.JSON(http.StatusBadRequest, gin.H{"error": "month is required for monthly budgets"})
			return
		}
	}

	if req.CategoryID == nil && req.SubCategoryID == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "category_id or sub_category_id is required"})
		return
	}

	if req.CategoryID != nil {
		var cat models.Category
		if err := h.db.Where("id = ? AND family_id = ?", *req.CategoryID, familyID).First(&cat).Error; err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid category"})
			return
		}
	}
	if req.SubCategoryID != nil {
		var sub models.SubCategory
		if err := h.db.Where("id = ? AND family_id = ?", *req.SubCategoryID, familyID).First(&sub).Error; err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid subcategory"})
			return
		}
	}

	budget := models.Budget{
		FamilyID: familyID,
		CreatedByUserID: userID,
		CategoryID: req.CategoryID,
		SubCategoryID: req.SubCategoryID,
		Period: req.Period,
		Year: req.Year,
		Month: req.Month,
		Amount: req.Amount,
		IsActive: true,
	}

	if err := h.db.Create(&budget).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create budget"})
		return
	}

	h.db.Preload("Category").Preload("SubCategory").First(&budget, budget.ID)
	c.JSON(http.StatusCreated, budget)
}

type CreateBudgetExpenseRequest struct {
	CategoryID    uint    `json:"category_id" binding:"required"`
	SubCategoryID uint    `json:"sub_category_id" binding:"required"`
	Title         string  `json:"title" binding:"required"`
	Description   string  `json:"description"`
	Amount        float64 `json:"amount" binding:"required,gt=0"`
	Currency      string  `json:"currency"`
	Date          string  `json:"date" binding:"required"`
	Merchant      string  `json:"merchant"`
	Notes         string  `json:"notes"`
}

func (h *BudgetTrackerHandler) CreateBudgetExpense(c *gin.Context) {
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

	var req CreateBudgetExpenseRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	currency := req.Currency
	if currency == "" {
		currency = "USD"
	}

	date, err := parseDate(req.Date)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid date format"})
		return
	}

	// Validate category/subcategory belong to family
	var sub models.SubCategory
	if err := h.db.Preload("Category").Where("id = ? AND family_id = ?", req.SubCategoryID, familyID).First(&sub).Error; err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid subcategory"})
		return
	}
	if sub.CategoryID != req.CategoryID {
		c.JSON(http.StatusBadRequest, gin.H{"error": "subcategory does not belong to category"})
		return
	}

	exp := models.BudgetExpense{
		FamilyID: familyID,
		CreatedByUserID: userID,
		CategoryID: req.CategoryID,
		SubCategoryID: req.SubCategoryID,
		Title: req.Title,
		Description: req.Description,
		Amount: req.Amount,
		Currency: currency,
		Date: date,
		Merchant: req.Merchant,
		Notes: req.Notes,
	}

	if err := h.db.Create(&exp).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create expense"})
		return
	}

	h.db.Preload("Category").Preload("SubCategory").First(&exp, exp.ID)
	c.JSON(http.StatusCreated, exp)
}

func (h *BudgetTrackerHandler) ListBudgetExpenses(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	q := h.db.Preload("Category").Preload("SubCategory").Where("family_id = ?", familyID).Order("date DESC, created_at DESC")

	if year := c.Query("year"); year != "" {
		q = q.Where("EXTRACT(YEAR FROM date) = ?", year)
	}
	if month := c.Query("month"); month != "" {
		q = q.Where("EXTRACT(MONTH FROM date) = ?", month)
	}
	if categoryID := c.Query("category_id"); categoryID != "" {
		q = q.Where("category_id = ?", categoryID)
	}
	if subCategoryID := c.Query("sub_category_id"); subCategoryID != "" {
		q = q.Where("sub_category_id = ?", subCategoryID)
	}

	var expenses []models.BudgetExpense
	if err := q.Find(&expenses).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch expenses"})
		return
	}

	c.JSON(http.StatusOK, expenses)
}

type MonthlyCategoryTotal struct {
	CategoryID   uint    `json:"category_id"`
	CategoryName string  `json:"category_name"`
	TotalAmount  float64 `json:"total_amount"`
}

type MonthlySubCategoryTotal struct {
	CategoryID      uint    `json:"category_id"`
	SubCategoryID   uint    `json:"sub_category_id"`
	SubCategoryName string  `json:"sub_category_name"`
	TotalAmount     float64 `json:"total_amount"`
}

func (h *BudgetTrackerHandler) MonthlySummary(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	yearStr := c.Query("year")
	monthStr := c.Query("month")	
	if yearStr == "" || monthStr == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "year and month are required"})
		return
	}
	_, err := strconv.Atoi(yearStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid year"})
		return
	}
	m, err := strconv.Atoi(monthStr)
	if err != nil || m < 1 || m > 12 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid month"})
		return
	}

	// Totals by category
	var catTotals []MonthlyCategoryTotal
	if err := h.db.Table("budget_expenses be").
		Select("be.category_id as category_id, c.name as category_name, COALESCE(SUM(be.amount),0) as total_amount").
		Joins("JOIN categories c ON c.id = be.category_id").
		Where("be.family_id = ? AND EXTRACT(YEAR FROM be.date) = ? AND EXTRACT(MONTH FROM be.date) = ?", familyID, yearStr, monthStr).
		Group("be.category_id, c.name").
		Order("total_amount DESC").
		Scan(&catTotals).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compute category summary"})
		return
	}

	// Totals by subcategory
	var subTotals []MonthlySubCategoryTotal
	if err := h.db.Table("budget_expenses be").
		Select("be.category_id as category_id, be.sub_category_id as sub_category_id, sc.name as sub_category_name, COALESCE(SUM(be.amount),0) as total_amount").
		Joins("JOIN sub_categories sc ON sc.id = be.sub_category_id").
		Where("be.family_id = ? AND EXTRACT(YEAR FROM be.date) = ? AND EXTRACT(MONTH FROM be.date) = ?", familyID, yearStr, monthStr).
		Group("be.category_id, be.sub_category_id, sc.name").
		Order("total_amount DESC").
		Scan(&subTotals).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compute subcategory summary"})
		return
	}

	// Total spent
	var totalSpent float64
	if err := h.db.Model(&models.BudgetExpense{}).
		Select("COALESCE(SUM(amount),0)").
		Where("family_id = ? AND EXTRACT(YEAR FROM date) = ? AND EXTRACT(MONTH FROM date) = ?", familyID, yearStr, monthStr).
		Scan(&totalSpent).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compute total"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"year": yearStr,
		"month": monthStr,
		"total_spent": totalSpent,
		"by_category": catTotals,
		"by_subcategory": subTotals,
		"generated_at": time.Now().UTC(),
	})
}
