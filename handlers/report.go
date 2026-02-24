package handlers

import (
	"net/http"
	"strconv"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type ReportHandler struct {
	db *gorm.DB
}

func NewReportHandler(db *gorm.DB) *ReportHandler {
	return &ReportHandler{db: db}
}

type SpendingTrendItem struct {
	Year       int     `json:"year"`
	Month      int     `json:"month"`
	TotalSpent float64 `json:"total_spent"`
}

func (h *ReportHandler) SpendingTrends(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	months := 12
	if m := c.Query("months"); m != "" {
		if val, err := strconv.Atoi(m); err == nil && val > 0 && val <= 60 {
			months = val
		}
	}

	var trends []SpendingTrendItem
	if err := h.db.Table("budget_expenses").
		Select("EXTRACT(YEAR FROM date)::int as year, EXTRACT(MONTH FROM date)::int as month, COALESCE(SUM(amount),0) as total_spent").
		Where("family_id = ? AND date >= NOW() - INTERVAL '1 month' * ?", familyID, months).
		Group("year, month").
		Order("year ASC, month ASC").
		Scan(&trends).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compute spending trends"})
		return
	}

	c.JSON(http.StatusOK, trends)
}

type MerchantSpending struct {
	Merchant   string  `json:"merchant"`
	TotalSpent float64 `json:"total_spent"`
	Count      int     `json:"count"`
}

func (h *ReportHandler) SpendingByMerchant(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var results []MerchantSpending
	q := h.db.Table("budget_expenses").
		Select("merchant, COALESCE(SUM(amount),0) as total_spent, COUNT(*) as count").
		Where("family_id = ? AND merchant != ''", familyID).
		Group("merchant").
		Order("total_spent DESC")

	if year := c.Query("year"); year != "" {
		q = q.Where("EXTRACT(YEAR FROM date) = ?", year)
	}
	if month := c.Query("month"); month != "" {
		q = q.Where("EXTRACT(MONTH FROM date) = ?", month)
	}
	if limit := c.Query("limit"); limit != "" {
		if l, err := strconv.Atoi(limit); err == nil {
			q = q.Limit(l)
		}
	}

	if err := q.Scan(&results).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to compute merchant spending"})
		return
	}

	c.JSON(http.StatusOK, results)
}

type SankeyNode struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type SankeyLink struct {
	Source string  `json:"source"`
	Target string  `json:"target"`
	Value  float64 `json:"value"`
}

func (h *ReportHandler) CashFlowSankey(c *gin.Context) {
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

	// Get income (savings-type categories represent income sources for Sankey)
	var incomeCategories []struct {
		CategoryName string  `json:"category_name"`
		TotalAmount  float64 `json:"total_amount"`
	}
	h.db.Table("budget_expenses be").
		Select("c.name as category_name, COALESCE(SUM(be.amount),0) as total_amount").
		Joins("JOIN categories c ON c.id = be.category_id").
		Where("be.family_id = ? AND c.type = ? AND EXTRACT(YEAR FROM be.date) = ? AND EXTRACT(MONTH FROM be.date) = ?",
			familyID, models.CategoryTypeSavings, yearStr, monthStr).
		Group("c.name").
		Order("total_amount DESC").
		Scan(&incomeCategories)

	// Get expense categories
	var expenseCategories []struct {
		CategoryName string  `json:"category_name"`
		TotalAmount  float64 `json:"total_amount"`
	}
	h.db.Table("budget_expenses be").
		Select("c.name as category_name, COALESCE(SUM(be.amount),0) as total_amount").
		Joins("JOIN categories c ON c.id = be.category_id").
		Where("be.family_id = ? AND c.type = ? AND EXTRACT(YEAR FROM be.date) = ? AND EXTRACT(MONTH FROM be.date) = ?",
			familyID, models.CategoryTypeExpense, yearStr, monthStr).
		Group("c.name").
		Order("total_amount DESC").
		Scan(&expenseCategories)

	nodes := []SankeyNode{}
	links := []SankeyLink{}

	// Add income nodes and link to "Income" hub
	nodes = append(nodes, SankeyNode{ID: "income", Name: "Income"})
	for _, inc := range incomeCategories {
		nodeID := "inc_" + inc.CategoryName
		nodes = append(nodes, SankeyNode{ID: nodeID, Name: inc.CategoryName})
		links = append(links, SankeyLink{Source: nodeID, Target: "income", Value: inc.TotalAmount})
	}

	// Add expense node hub and expense category nodes
	nodes = append(nodes, SankeyNode{ID: "expenses", Name: "Expenses"})
	links = append(links, SankeyLink{Source: "income", Target: "expenses", Value: 0})

	var totalExpenses float64
	for _, exp := range expenseCategories {
		nodeID := "exp_" + exp.CategoryName
		nodes = append(nodes, SankeyNode{ID: nodeID, Name: exp.CategoryName})
		links = append(links, SankeyLink{Source: "expenses", Target: nodeID, Value: exp.TotalAmount})
		totalExpenses += exp.TotalAmount
	}

	// Update the income->expenses link value
	for i := range links {
		if links[i].Source == "income" && links[i].Target == "expenses" {
			links[i].Value = totalExpenses
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"nodes": nodes,
		"links": links,
	})
}

func (h *ReportHandler) SavingsRate(c *gin.Context) {
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

	// Total income (savings-type category expenses represent income entries)
	var totalIncome float64
	h.db.Table("budget_expenses be").
		Joins("JOIN categories c ON c.id = be.category_id").
		Where("be.family_id = ? AND c.type = ? AND EXTRACT(YEAR FROM be.date) = ? AND EXTRACT(MONTH FROM be.date) = ?",
			familyID, models.CategoryTypeSavings, yearStr, monthStr).
		Select("COALESCE(SUM(be.amount),0)").
		Scan(&totalIncome)

	// Total expenses
	var totalExpenses float64
	h.db.Table("budget_expenses be").
		Joins("JOIN categories c ON c.id = be.category_id").
		Where("be.family_id = ? AND c.type = ? AND EXTRACT(YEAR FROM be.date) = ? AND EXTRACT(MONTH FROM be.date) = ?",
			familyID, models.CategoryTypeExpense, yearStr, monthStr).
		Select("COALESCE(SUM(be.amount),0)").
		Scan(&totalExpenses)

	savings := totalIncome - totalExpenses
	var savingsRate float64
	if totalIncome > 0 {
		savingsRate = (savings / totalIncome) * 100
	}

	c.JSON(http.StatusOK, gin.H{
		"year":           yearStr,
		"month":          monthStr,
		"total_income":   totalIncome,
		"total_expenses": totalExpenses,
		"savings":        savings,
		"savings_rate":   savingsRate,
	})
}
