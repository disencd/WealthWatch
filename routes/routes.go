package routes

import (
	"splitwise/handlers"
	"splitwise/middleware"
	"splitwise/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func SetupRoutes(r *gin.Engine, db *gorm.DB) {
	// Auto-migrate database
	models.AutoMigrate(db)

	// Initialize handlers
	authHandler := handlers.NewAuthHandler(db)
	familyHandler := handlers.NewFamilyHandler(db)
	budgetTrackerHandler := handlers.NewBudgetTrackerHandler(db)
	expenseHandler := handlers.NewExpenseHandler(db)
	groupHandler := handlers.NewGroupHandler(db)
	balanceHandler := handlers.NewBalanceHandler(db)
	settlementHandler := handlers.NewSettlementHandler(db)

	// Health check endpoint
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// Public routes
	api := r.Group("/api/v1")
	{
		// Authentication routes
		auth := api.Group("/auth")
		{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
		}

		// Protected routes
		protected := api.Group("/")
		protected.Use(middleware.AuthMiddleware())
		{
			// User routes
			protected.GET("/profile", authHandler.GetProfile)

			// Family routes
			families := protected.Group("/families")
			{
				families.GET("", familyHandler.ListMyFamilies)
				families.POST("", familyHandler.CreateFamily)
				families.GET("/members", familyHandler.ListMembers)
				families.POST("/members", middleware.RequireRole(string(models.FamilyRoleSuperAdmin), string(models.FamilyRoleAdmin)), familyHandler.AddMember)
				families.PUT("/members/:memberId/role", middleware.RequireRole(string(models.FamilyRoleSuperAdmin)), familyHandler.UpdateMemberRole)
				families.DELETE("/members/:memberId", middleware.RequireRole(string(models.FamilyRoleSuperAdmin)), familyHandler.RemoveMember)
			}

			// Budget tracker routes
			budget := protected.Group("/budget")
			{
				// Categories
				budget.GET("/categories", budgetTrackerHandler.ListCategories)
				budget.POST("/categories", middleware.RequireRole(string(models.FamilyRoleSuperAdmin), string(models.FamilyRoleAdmin)), budgetTrackerHandler.CreateCategory)
				// Sub-categories
				budget.GET("/subcategories", budgetTrackerHandler.ListSubCategories)
				budget.POST("/subcategories", middleware.RequireRole(string(models.FamilyRoleSuperAdmin), string(models.FamilyRoleAdmin)), budgetTrackerHandler.CreateSubCategory)
				// Budgets
				budget.GET("/budgets", budgetTrackerHandler.ListBudgets)
				budget.POST("/budgets", middleware.RequireRole(string(models.FamilyRoleSuperAdmin), string(models.FamilyRoleAdmin)), budgetTrackerHandler.CreateBudget)
				// Expenses
				budget.GET("/expenses", budgetTrackerHandler.ListBudgetExpenses)
				budget.POST("/expenses", budgetTrackerHandler.CreateBudgetExpense)
				// Reporting
				budget.GET("/summary/monthly", budgetTrackerHandler.MonthlySummary)
			}

			// Balance routes
			balances := protected.Group("/balances")
			{
				balances.GET("", balanceHandler.GetBalances)
				balances.GET("/users/:userId", balanceHandler.GetBalanceWithUser)
			}

			// Settlement routes
			settlements := protected.Group("/settlements")
			{
				settlements.POST("", settlementHandler.CreateSettlement)
				settlements.GET("", settlementHandler.GetSettlements)
				settlements.GET("/:id", settlementHandler.GetSettlement)
				settlements.PUT("/:id/status", settlementHandler.UpdateSettlementStatus)
			}

			// Expense routes
			expenses := protected.Group("/expenses")
			{
				expenses.POST("", expenseHandler.CreateExpense)
				expenses.GET("", expenseHandler.GetExpenses)
				expenses.GET("/:id", expenseHandler.GetExpense)
			}

			// Group routes
			groups := protected.Group("/groups")
			{
				groups.POST("", groupHandler.CreateGroup)
				groups.GET("", groupHandler.GetGroups)
				groups.GET("/:id", groupHandler.GetGroup)
				groups.POST("/:id/members", groupHandler.AddMember)
				groups.DELETE("/:id/members/:memberId", groupHandler.RemoveMember)
			}
		}
	}
}
