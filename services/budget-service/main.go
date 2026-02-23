package main

import (
	"fmt"
	"log"
	"os"

	"wealthwatch/internal/budget"
	"wealthwatch/internal/expense"
	"wealthwatch/internal/savings"
	"wealthwatch/pkg/config"
	"wealthwatch/pkg/database"
	"wealthwatch/pkg/middleware"
	"wealthwatch/pkg/routes"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func main() {
	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal("Failed to load configuration:", err)
	}

	// Initialize database
	db, err := database.InitDB(cfg.Database)
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// Run migrations
	if err := database.RunBudgetMigrations(db); err != nil {
		log.Fatal("Failed to run migrations:", err)
	}

	// Seed default categories
	if err := seedCategories(db); err != nil {
		log.Fatal("Failed to seed categories:", err)
	}

	// Set Gin mode
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Initialize router
	r := gin.New()

	// Middleware
	r.Use(gin.Logger())
	r.Use(gin.Recovery())
	r.Use(middleware.CORS())
	r.Use(middleware.RequestID())
	r.Use(middleware.AuthMiddleware(cfg.JWT))

	// Health check
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"service": "budget-service",
			"status":  "healthy",
		})
	})

	// Initialize handlers
	budgetHandler := budget.NewHandler(db)
	expenseHandler := expense.NewHandler(db)
	savingsHandler := savings.NewHandler(db)

	// Setup routes
	routes.SetupBudgetRoutes(r, budgetHandler)
	routes.SetupExpenseRoutes(r, expenseHandler)
	routes.SetupSavingsRoutes(r, savingsHandler)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = cfg.BudgetService.Port
	}

	log.Printf("Budget service starting on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}

// seedCategories creates default categories and sub-categories
func seedCategories(db *gorm.DB) error {
	// Check if categories already exist
	var count int64
	db.Model(&models.Category{}).Count(&count)
	if count > 0 {
		return nil // Categories already seeded
	}

	// Create main categories
	categories := []models.Category{
		{
			Name:        string(models.Housing),
			Type:        "expense",
			Description: "Housing related expenses",
			Color:       "#FF6B6B",
			Icon:        "home",
		},
		{
			Name:        string(models.Utilities),
			Type:        "expense",
			Description: "Utility bills and services",
			Color:       "#4ECDC4",
			Icon:        "zap",
		},
		{
			Name:        string(models.Food),
			Type:        "expense",
			Description: "Food and groceries",
			Color:       "#45B7D1",
			Icon:        "utensils",
		},
		{
			Name:        string(models.Transportation),
			Type:        "expense",
			Description: "Transportation expenses",
			Color:       "#96CEB4",
			Icon:        "car",
		},
		{
			Name:        string(models.MedicalHealthcare),
			Type:        "expense",
			Description: "Medical and healthcare expenses",
			Color:       "#FFEAA7",
			Icon:        "heart",
		},
		{
			Name:        string(models.DayCare),
			Type:        "expense",
			Description: "DayCare expenses",
			Color:       "#DDA0DD",
			Icon:        "child",
		},
		{
			Name:        string(models.Church),
			Type:        "expense",
			Description: "Church related expenses",
			Color:       "#F4A460",
			Icon:        "church",
		},
	}

	// Create savings categories
	savingsCategories := []models.Category{
		{
			Name:        string(models.Savings1),
			Type:        "savings",
			Description: "Primary savings account",
			Color:       "#2ECC71",
			Icon:        "piggy-bank",
		},
		{
			Name:        string(models.Savings2),
			Type:        "savings",
			Description: "Secondary savings account",
			Color:       "#3498DB",
			Icon:        "wallet",
		},
		{
			Name:        string(models.Savings3),
			Type:        "savings",
			Description: "Emergency savings",
			Color:       "#9B59B6",
			Icon:        "shield",
		},
	}

	allCategories := append(categories, savingsCategories...)

	for _, category := range allCategories {
		if err := db.Create(&category).Error; err != nil {
			return fmt.Errorf("failed to create category %s: %w", category.Name, err)
		}
	}

	// Create sub-categories
	subCategories := []models.SubCategory{
		// Housing sub-categories
		{CategoryID: 1, Name: string(models.ADU), Description: "Accessory Dwelling Unit expenses", Color: "#FF8C8C"},
		{CategoryID: 1, Name: string(models.HomeImprovement), Description: "Home improvement and repairs", Color: "#FFB6B6"},

		// Utilities sub-categories
		{CategoryID: 2, Name: string(models.PGNE), Description: "PG&E utility bills", Color: "#6EDDD6"},
		{CategoryID: 2, Name: string(models.WaterDept), Description: "Water department bills", Color: "#7EDDD6"},
		{CategoryID: 2, Name: string(models.InternetPhone), Description: "Internet and phone services", Color: "#5EDDD6"},

		// Food sub-categories
		{CategoryID: 3, Name: string(models.Grocery), Description: "Regular grocery shopping", Color: "#67C7E1"},
		{CategoryID: 3, Name: string(models.IndianGrocery), Description: "Indian specialty groceries", Color: "#77D7F1"},
		{CategoryID: 3, Name: string(models.Restaurant), Description: "Restaurant and dining out", Color: "#57B7D1"},

		// Transportation sub-categories
		{CategoryID: 4, Name: string(models.Gas), Description: "Gasoline and fuel", Color: "#A6DEC4"},

		// Medical & Healthcare sub-categories
		{CategoryID: 5, Name: string(models.MedicalExpense), Description: "Medical expenses and healthcare", Color: "#FFEFB7"},

		// DayCare sub-categories
		{CategoryID: 6, Name: string(models.DayCareExpense), Description: "DayCare fees and expenses", Color: "#EDC0ED"},

		// Church sub-categories
		{CategoryID: 7, Name: string(models.ChurchExpense), Description: "Church donations and expenses", Color: "#F5B470"},

		// Personal sub-categories (add to Housing for now, or create Personal category)
		{CategoryID: 1, Name: string(models.Movie), Description: "Movie and entertainment", Color: "#FF9C9C"},
		{CategoryID: 1, Name: string(models.Camping), Description: "Camping and outdoor activities", Color: "#FFACAC"},
		{CategoryID: 1, Name: string(models.Hair), Description: "Hair care and grooming", Color: "#FFBCBC"},
	}

	for _, subCategory := range subCategories {
		if err := db.Create(&subCategory).Error; err != nil {
			return fmt.Errorf("failed to create sub-category %s: %w", subCategory.Name, err)
		}
	}

	log.Println("Default categories and sub-categories seeded successfully")
	return nil
}
