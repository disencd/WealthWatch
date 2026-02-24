package handlers

import (
	"encoding/csv"
	"errors"
	"io"
	"mime/multipart"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"wealthwatch/middleware"
	"wealthwatch/models"

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

func (h *BudgetTrackerHandler) ImportCategoriesCSV(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	file, _, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file is required"})
		return
	}
	defer file.Close()

	r := csv.NewReader(file)
	r.FieldsPerRecord = -1

	type section string
	const (
		sectionNone    section = "none"
		sectionIncome  section = "income"
		sectionExpense section = "expense"
		sectionSavings section = "savings"
	)

	currentSection := sectionNone
	lastExpenseCategoryName := ""

	createdCategories := 0
	createdSubCategories := 0
	skipped := 0

	get := func(row []string, idx int) string {
		if idx < 0 || idx >= len(row) {
			return ""
		}
		return strings.TrimSpace(row[idx])
	}

	upsertCategory := func(catType models.CategoryType, name string) (*models.Category, bool, error) {
		name = strings.TrimSpace(name)
		if name == "" {
			return nil, false, nil
		}

		var existing models.Category
		err := h.db.Where("family_id = ? AND type = ? AND name = ?", familyID, catType, name).First(&existing).Error
		if err == nil {
			return &existing, false, nil
		}
		if err != gorm.ErrRecordNotFound {
			return nil, false, err
		}

		cat := models.Category{FamilyID: familyID, Type: catType, Name: name, IsActive: true}
		if err := h.db.Create(&cat).Error; err != nil {
			return nil, false, err
		}
		return &cat, true, nil
	}

	upsertSubCategory := func(categoryID uint, name string) (bool, error) {
		name = strings.TrimSpace(name)
		if name == "" {
			return false, nil
		}
		var existing models.SubCategory
		err := h.db.Where("family_id = ? AND category_id = ? AND name = ?", familyID, categoryID, name).First(&existing).Error
		if err == nil {
			return false, nil
		}
		if err != gorm.ErrRecordNotFound {
			return false, err
		}

		sub := models.SubCategory{FamilyID: familyID, CategoryID: categoryID, Name: name, IsActive: true}
		if err := h.db.Create(&sub).Error; err != nil {
			return false, err
		}
		return true, nil
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to parse CSV"})
			return
		}

		col0 := get(row, 0)
		col2 := get(row, 2)

		// Section headers
		if strings.EqualFold(col0, "Income Categories") {
			currentSection = sectionIncome
			lastExpenseCategoryName = ""
			continue
		}
		if strings.HasPrefix(strings.ToLower(col0), "expense categories") {
			currentSection = sectionExpense
			lastExpenseCategoryName = ""
			continue
		}
		if strings.EqualFold(col0, "Savings Categories") {
			currentSection = sectionSavings
			lastExpenseCategoryName = ""
			continue
		}
		if strings.EqualFold(col0, "Yearly Saving Goal") {
			currentSection = sectionNone
			lastExpenseCategoryName = ""
			continue
		}

		// Skip obvious instruction lines / empty separator lines
		if col0 == "" && col2 == "" {
			continue
		}
		if strings.HasPrefix(col0, "READ THIS FIRST") || strings.HasPrefix(col0, "I WILL NO LONGER") {
			continue
		}
		if strings.HasPrefix(col0, "-") {
			continue
		}

		switch currentSection {
		case sectionIncome:
			cat, created, err := upsertCategory(models.CategoryTypeSavings, col0)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to import categories"})
				return
			}
			if cat == nil {
				skipped++
				continue
			}
			if created {
				createdCategories++
			}
		case sectionSavings:
			cat, created, err := upsertCategory(models.CategoryTypeSavings, col0)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to import categories"})
				return
			}
			if cat == nil {
				skipped++
				continue
			}
			if created {
				createdCategories++
			}
		case sectionExpense:
			if col0 != "" {
				lastExpenseCategoryName = col0
				cat, created, err := upsertCategory(models.CategoryTypeExpense, col0)
				if err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to import categories"})
					return
				}
				if cat != nil && created {
					createdCategories++
				}
			}

			if col2 != "" {
				if lastExpenseCategoryName == "" {
					skipped++
					continue
				}
				cat, _, err := upsertCategory(models.CategoryTypeExpense, lastExpenseCategoryName)
				if err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to import categories"})
					return
				}
				if cat == nil {
					skipped++
					continue
				}
				subCreated, err := upsertSubCategory(cat.ID, col2)
				if err != nil {
					c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to import subcategories"})
					return
				}
				if subCreated {
					createdSubCategories++
				}
			}
		default:
			skipped++
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"created_categories":     createdCategories,
		"created_sub_categories": createdSubCategories,
		"skipped":                skipped,
	})
}

// ImportMonthlyCSV imports FinancialDocs monthly CSV exports (e.g. "FinancialDocs-2026 - Jan.csv")
// and creates BudgetExpense rows for the "Expenses" table section.
//
// Request: multipart/form-data with:
// - files: one or many files (preferred)
// - file: single file (supported)
func (h *BudgetTrackerHandler) ImportMonthlyCSV(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	userID, ok := middleware.GetUserID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "User not found in token"})
		return
	}

	form, err := c.MultipartForm()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "multipart form required"})
		return
	}

	files := form.File["files"]
	if len(files) == 0 {
		files = form.File["file"]
	}
	if len(files) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "files is required"})
		return
	}

	created := 0
	skipped := 0
	createdCategories := 0
	createdSubCategories := 0

	for _, fh := range files {
		cCount, sCount, crCat, crSub, err := h.importOneMonthlyCSV(familyID, userID, fh)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		created += cCount
		skipped += sCount
		createdCategories += crCat
		createdSubCategories += crSub
	}

	c.JSON(http.StatusOK, gin.H{
		"created_budget_expenses": created,
		"skipped":                 skipped,
		"created_categories":      createdCategories,
		"created_sub_categories":  createdSubCategories,
	})
}

var monthlyHeaderYearRe = regexp.MustCompile(`(?i)\b(\d{4})\b`)

func (h *BudgetTrackerHandler) importOneMonthlyCSV(familyID uint, userID uint, fh *multipart.FileHeader) (created int, skipped int, createdCats int, createdSubs int, outErr error) {
	f, err := fh.Open()
	if err != nil {
		return 0, 0, 0, 0, errors.New("failed to open uploaded file")
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1

	// Try to infer year from file content; fall back to current year.
	year := time.Now().Year()

	dateIdx, costIdx, categoryIdx, notesIdx := -1, -1, -1, -1
	inExpenses := false

	parseMoney := func(s string) (float64, bool) {
		s = strings.TrimSpace(s)
		if s == "" {
			return 0, false
		}
		s = strings.ReplaceAll(s, "$", "")
		s = strings.ReplaceAll(s, ",", "")
		s = strings.TrimSpace(s)
		val, err := strconv.ParseFloat(s, 64)
		if err != nil {
			return 0, false
		}
		return val, true
	}

	ensureImportedCategory := func() (*models.Category, bool, error) {
		var existing models.Category
		err := h.db.Where("family_id = ? AND type = ? AND name = ?", familyID, models.CategoryTypeExpense, "Imported").First(&existing).Error
		if err == nil {
			return &existing, false, nil
		}
		if err != gorm.ErrRecordNotFound {
			return nil, false, err
		}
		cat := models.Category{FamilyID: familyID, Type: models.CategoryTypeExpense, Name: "Imported", IsActive: true}
		if err := h.db.Create(&cat).Error; err != nil {
			return nil, false, err
		}
		return &cat, true, nil
	}

	resolveCategoryAndSub := func(name string) (catID uint, subID uint, newCat bool, newSub bool, err error) {
		name = strings.TrimSpace(name)
		if name == "" {
			return 0, 0, false, false, errors.New("missing category")
		}

		// Prefer matching existing SubCategory by name
		var sub models.SubCategory
		err = h.db.Where("family_id = ? AND name = ?", familyID, name).First(&sub).Error
		if err == nil {
			return sub.CategoryID, sub.ID, false, false, nil
		}
		if err != gorm.ErrRecordNotFound {
			return 0, 0, false, false, err
		}

		// Otherwise, create a subcategory under an "Imported" expense category
		impCat, createdCat, err := ensureImportedCategory()
		if err != nil {
			return 0, 0, false, false, err
		}

		var existingSub models.SubCategory
		err = h.db.Where("family_id = ? AND category_id = ? AND name = ?", familyID, impCat.ID, name).First(&existingSub).Error
		if err == nil {
			return existingSub.CategoryID, existingSub.ID, createdCat, false, nil
		}
		if err != gorm.ErrRecordNotFound {
			return 0, 0, false, false, err
		}

		newSubObj := models.SubCategory{FamilyID: familyID, CategoryID: impCat.ID, Name: name, IsActive: true}
		if err := h.db.Create(&newSubObj).Error; err != nil {
			return 0, 0, false, false, err
		}
		return impCat.ID, newSubObj.ID, createdCat, true, nil
	}

	parseDate := func(s string) (time.Time, bool) {
		s = strings.TrimSpace(s)
		if s == "" {
			return time.Time{}, false
		}
		parts := strings.Fields(s)
		if len(parts) < 2 {
			return time.Time{}, false
		}
		monAbbrev := strings.TrimSpace(parts[0])
		day, err := strconv.Atoi(strings.TrimSpace(parts[1]))
		if err != nil || day < 1 || day > 31 {
			return time.Time{}, false
		}
		// Parse month abbrev like Jan/Feb
		monTime, err := time.Parse("Jan", strings.Title(strings.ToLower(monAbbrev)))
		if err != nil {
			return time.Time{}, false
		}
		return time.Date(year, monTime.Month(), day, 0, 0, 0, 0, time.UTC), true
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return 0, 0, 0, 0, errors.New("failed to parse CSV")
		}

		// Best-effort year detection from any cell early in the file
		if !inExpenses {
			for _, col := range row {
				m := monthlyHeaderYearRe.FindStringSubmatch(col)
				if len(m) == 2 {
					if y, yerr := strconv.Atoi(m[1]); yerr == nil && y >= 2000 && y <= 2100 {
						year = y
						break
					}
				}
			}
		}

		// Detect expenses header row containing Date/Cost/Category/Notes
		if !inExpenses {
			for i := 0; i < len(row); i++ {
				s := strings.TrimSpace(row[i])
				if strings.EqualFold(s, "Date") {
					dateIdx = i
				}
				if strings.EqualFold(s, "Cost") {
					costIdx = i
				}
				if strings.EqualFold(s, "Category") {
					categoryIdx = i
				}
				if strings.EqualFold(s, "Notes") {
					notesIdx = i
				}
			}
			if dateIdx >= 0 && costIdx >= 0 && categoryIdx >= 0 {
				inExpenses = true
			}
			continue
		}

		if dateIdx < 0 || dateIdx >= len(row) {
			continue
		}

		dateStr := strings.TrimSpace(row[dateIdx])
		if dateStr == "" {
			continue
		}

		// Stop when we reach later sections
		if strings.EqualFold(dateStr, "Summary") || strings.EqualFold(dateStr, "Income") || strings.EqualFold(dateStr, "Savings") {
			break
		}

		dateVal, ok := parseDate(dateStr)
		if !ok {
			skipped++
			continue
		}

		amountStr := ""
		if costIdx >= 0 && costIdx < len(row) {
			amountStr = row[costIdx]
		}
		amount, ok := parseMoney(amountStr)
		if !ok || amount <= 0 {
			skipped++
			continue
		}

		catName := ""
		if categoryIdx >= 0 && categoryIdx < len(row) {
			catName = row[categoryIdx]
		}

		catID, subID, newCat, newSub, err := resolveCategoryAndSub(catName)
		if err != nil {
			skipped++
			continue
		}
		if newCat {
			createdCats++
		}
		if newSub {
			createdSubs++
		}

		merchant := ""
		if notesIdx >= 0 && notesIdx < len(row) {
			merchant = strings.TrimSpace(row[notesIdx])
		}

		title := strings.TrimSpace(catName)
		if title == "" {
			title = "Imported"
		}

		be := models.BudgetExpense{
			FamilyID:        familyID,
			CreatedByUserID: userID,
			CategoryID:      catID,
			SubCategoryID:   subID,
			Title:           title,
			Amount:          amount,
			Currency:        "USD",
			Date:            dateVal,
			Merchant:        merchant,
		}

		if err := h.db.Create(&be).Error; err != nil {
			skipped++
			continue
		}
		created++
	}

	return created, skipped, createdCats, createdSubs, nil
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
	CategoryID    *uint               `json:"category_id"`
	SubCategoryID *uint               `json:"sub_category_id"`
	Period        models.BudgetPeriod `json:"period" binding:"required"`
	Year          int                 `json:"year" binding:"required"`
	Month         *int                `json:"month"`
	Amount        float64             `json:"amount" binding:"required,gt=0"`
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
		FamilyID:        familyID,
		CreatedByUserID: userID,
		CategoryID:      req.CategoryID,
		SubCategoryID:   req.SubCategoryID,
		Period:          req.Period,
		Year:            req.Year,
		Month:           req.Month,
		Amount:          req.Amount,
		IsActive:        true,
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
		FamilyID:        familyID,
		CreatedByUserID: userID,
		CategoryID:      req.CategoryID,
		SubCategoryID:   req.SubCategoryID,
		Title:           req.Title,
		Description:     req.Description,
		Amount:          req.Amount,
		Currency:        currency,
		Date:            date,
		Merchant:        req.Merchant,
		Notes:           req.Notes,
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
		"year":           yearStr,
		"month":          monthStr,
		"total_spent":    totalSpent,
		"by_category":    catTotals,
		"by_subcategory": subTotals,
		"generated_at":   time.Now().UTC(),
	})
}
