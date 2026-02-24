package routes

import (
	"wealthwatch/handlers"
	"wealthwatch/middleware"
	"wealthwatch/models"

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
	accountHandler := handlers.NewAccountHandler(db)
	investmentHandler := handlers.NewInvestmentHandler(db)
	recurringHandler := handlers.NewRecurringHandler(db)
	autoRuleHandler := handlers.NewAutoRuleHandler(db)
	receiptHandler := handlers.NewReceiptHandler(db)
	reportHandler := handlers.NewReportHandler(db)

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
				budget.POST("/import/categories-csv", middleware.RequireRole(string(models.FamilyRoleSuperAdmin), string(models.FamilyRoleAdmin)), budgetTrackerHandler.ImportCategoriesCSV)
				budget.POST("/import/monthly-csv", middleware.RequireRole(string(models.FamilyRoleSuperAdmin), string(models.FamilyRoleAdmin)), budgetTrackerHandler.ImportMonthlyCSV)
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

			// Account routes (Financial Dashboard)
			accounts := protected.Group("/accounts")
			{
				accounts.GET("", accountHandler.ListAccounts)
				accounts.POST("", accountHandler.CreateAccount)
				accounts.GET("/:id", accountHandler.GetAccount)
				accounts.PUT("/:id", accountHandler.UpdateAccount)
				accounts.DELETE("/:id", accountHandler.DeleteAccount)
			}

			// Net Worth routes
			networth := protected.Group("/networth")
			{
				networth.GET("/summary", accountHandler.GetNetWorthSummary)
				networth.GET("/history", accountHandler.GetNetWorthHistory)
				networth.POST("/snapshot", accountHandler.SnapshotNetWorth)
			}

			// Investment routes
			investments := protected.Group("/investments")
			{
				investments.GET("", investmentHandler.ListHoldings)
				investments.POST("", investmentHandler.CreateHolding)
				investments.GET("/portfolio", investmentHandler.GetPortfolioSummary)
				investments.PUT("/:id", investmentHandler.UpdateHolding)
				investments.DELETE("/:id", investmentHandler.DeleteHolding)
			}

			// Recurring transaction routes
			recurring := protected.Group("/recurring")
			{
				recurring.GET("", recurringHandler.ListRecurring)
				recurring.POST("", recurringHandler.CreateRecurring)
				recurring.GET("/upcoming", recurringHandler.GetUpcoming)
				recurring.PUT("/:id", recurringHandler.UpdateRecurring)
				recurring.DELETE("/:id", recurringHandler.DeleteRecurring)
			}

			// Auto-categorization rules
			rules := protected.Group("/rules")
			{
				rules.GET("", autoRuleHandler.ListRules)
				rules.POST("", autoRuleHandler.CreateRule)
				rules.PUT("/:id", autoRuleHandler.UpdateRule)
				rules.DELETE("/:id", autoRuleHandler.DeleteRule)
			}

			// Receipt routes
			receipts := protected.Group("/receipts")
			{
				receipts.GET("", receiptHandler.ListReceipts)
				receipts.POST("", receiptHandler.UploadReceipt)
				receipts.GET("/:id", receiptHandler.GetReceipt)
				receipts.DELETE("/:id", receiptHandler.DeleteReceipt)
			}

			// Reports routes
			reports := protected.Group("/reports")
			{
				reports.GET("/spending-trends", reportHandler.SpendingTrends)
				reports.GET("/spending-by-merchant", reportHandler.SpendingByMerchant)
				reports.GET("/cashflow-sankey", reportHandler.CashFlowSankey)
				reports.GET("/savings-rate", reportHandler.SavingsRate)
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
