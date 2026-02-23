package main

import (
	"log"
	"os"

	"splitwise/internal/balance"
	"splitwise/pkg/config"
	"splitwise/pkg/database"
	"splitwise/pkg/middleware"
	"splitwise/pkg/routes"

	"github.com/gin-gonic/gin"
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
	if err := database.RunMigrations(db, "balance"); err != nil {
		log.Fatal("Failed to run migrations:", err)
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
			"service": "balance-service",
			"status":  "healthy",
		})
	})

	// Setup routes
	balanceHandler := balance.NewHandler(db)
	routes.SetupBalanceRoutes(r, balanceHandler)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = cfg.BalanceService.Port
	}

	log.Printf("Balance service starting on port %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
