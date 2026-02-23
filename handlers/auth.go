package handlers

import (
	"errors"
	"fmt"
	"net/http"

	"splitwise/middleware"
	"splitwise/models"
	"splitwise/utils"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type AuthHandler struct {
	db *gorm.DB
}

func NewAuthHandler(db *gorm.DB) *AuthHandler {
	return &AuthHandler{db: db}
}

type RegisterRequest struct {
	FirstName string `json:"first_name" binding:"required"`
	LastName  string `json:"last_name" binding:"required"`
	Email     string `json:"email" binding:"required,email"`
	Password  string `json:"password" binding:"required,min=6"`
	Phone     string `json:"phone"`
}

type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

type AuthResponse struct {
	Token string      `json:"token"`
	User  models.User `json:"user"`
}

// Register handles user registration
func (h *AuthHandler) Register(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Check if user already exists
	var existingUser models.User
	if err := h.db.Where("email = ?", req.Email).First(&existingUser).Error; err == nil {
		c.JSON(http.StatusConflict, gin.H{"error": "User with this email already exists"})
		return
	}

	// Hash password
	hashedPassword, err := utils.HashPassword(req.Password)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to hash password"})
		return
	}

	// Create user
	user := models.User{
		FirstName: req.FirstName,
		LastName:  req.LastName,
		Email:     req.Email,
		Password:  hashedPassword,
		Phone:     req.Phone,
	}

	if err := h.db.Create(&user).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create user"})
		return
	}

	// Create a default family and make this user the superadmin
	family := models.Family{
		Name:        fmt.Sprintf("%s %s Family", req.FirstName, req.LastName),
		Currency:    "USD",
		OwnerUserID: user.ID,
	}
	if err := h.db.Create(&family).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create family"})
		return
	}

	var existingExpenseCategoryCount int64
	if err := h.db.Model(&models.Category{}).
		Where("family_id = ? AND type = ?", family.ID, models.CategoryTypeExpense).
		Count(&existingExpenseCategoryCount).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to check existing categories"})
		return
	}

	if existingExpenseCategoryCount == 0 {
		defaultExpenseCategoryNames := []string{
			"Housing",
			"Utilities",
			"Food",
			"Transportation",
			"Medical & Healthcare",
			"DayCare",
			"Church",
		}

		categories := make([]models.Category, 0, len(defaultExpenseCategoryNames))
		for _, name := range defaultExpenseCategoryNames {
			categories = append(categories, models.Category{
				FamilyID: family.ID,
				Type:     models.CategoryTypeExpense,
				Name:     name,
				IsActive: true,
			})
		}

		if err := h.db.Create(&categories).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to seed categories"})
			return
		}
	}

	// Seed default sub-categories (idempotent)
	categoryIDsByName := map[string]uint{}
	{
		var cats []models.Category
		if err := h.db.Where("family_id = ? AND type = ?", family.ID, models.CategoryTypeExpense).Find(&cats).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to load categories"})
			return
		}
		for _, cat := range cats {
			categoryIDsByName[cat.Name] = cat.ID
		}
	}

	subCategoriesByCategoryName := map[string][]string{
		"Housing": {
			"ADU",
			"Home Improvement",
			"Movie",
			"Camping",
			"Hair",
		},
		"Utilities": {
			"PGNE",
			"Water Dept",
			"Internet + Phone",
		},
		"Food": {
			"Restaurant",
			"Grocery",
			"Indian Grocery",
		},
		"Transportation": {
			"Gas",
		},
		"Medical & Healthcare": {
			"Medical Expense",
			"Insurance",
		},
		"DayCare": {
			"DayCare",
		},
		"Church": {
			"Church",
		},
	}

	for categoryName, subNames := range subCategoriesByCategoryName {
		categoryID, ok := categoryIDsByName[categoryName]
		if !ok {
			continue
		}

		for _, subName := range subNames {
			var existing models.SubCategory
			err := h.db.Where("family_id = ? AND category_id = ? AND name = ?", family.ID, categoryID, subName).First(&existing).Error
			if err == nil {
				continue
			}
			if !errors.Is(err, gorm.ErrRecordNotFound) {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to check existing subcategories"})
				return
			}

			sub := models.SubCategory{
				FamilyID:   family.ID,
				CategoryID: categoryID,
				Name:       subName,
				IsActive:   true,
			}
			if err := h.db.Create(&sub).Error; err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to seed subcategories"})
				return
			}
		}
	}

	membership := models.FamilyMembership{
		FamilyID: family.ID,
		UserID:   user.ID,
		Role:     models.FamilyRoleSuperAdmin,
		Status:   "active",
	}
	if err := h.db.Create(&membership).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create family membership"})
		return
	}

	// Generate token
	token, err := utils.GenerateToken(user.ID, user.Email, family.ID, string(membership.Role))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate token"})
		return
	}

	c.JSON(http.StatusCreated, AuthResponse{
		Token: token,
		User:  user,
	})
}

// Login handles user login
func (h *AuthHandler) Login(c *gin.Context) {
	var req LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Find user
	var user models.User
	if err := h.db.Where("email = ?", req.Email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
		return
	}

	// Check password
	if !utils.CheckPassword(req.Password, user.Password) {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
		return
	}

	// Find an active family membership for this user
	var membership models.FamilyMembership
	if err := h.db.Where("user_id = ? AND status = ?", user.ID, "active").Order("id ASC").First(&membership).Error; err != nil {
		c.JSON(http.StatusForbidden, gin.H{"error": "User is not part of any active family"})
		return
	}

	// Generate token
	token, err := utils.GenerateToken(user.ID, user.Email, membership.FamilyID, string(membership.Role))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate token"})
		return
	}

	c.JSON(http.StatusOK, AuthResponse{
		Token: token,
		User:  user,
	})
}

// GetProfile handles getting user profile
func (h *AuthHandler) GetProfile(c *gin.Context) {
	userID, exists := middleware.GetUserID(c)
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User not authenticated"})
		return
	}

	var user models.User
	if err := h.db.First(&user, userID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
		return
	}

	c.JSON(http.StatusOK, user)
}
