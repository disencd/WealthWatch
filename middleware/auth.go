package middleware

import (
	"net/http"
	"strings"

	"splitwise/utils"

	"github.com/gin-gonic/gin"
)

// AuthMiddleware protects routes that require authentication
func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authorization header required"})
			c.Abort()
			return
		}

		// Extract token from "Bearer <token>"
		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
		if tokenString == authHeader {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Bearer token required"})
			c.Abort()
			return
		}

		claims, err := utils.ValidateToken(tokenString)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid token"})
			c.Abort()
			return
		}

		// Set user context
		c.Set("user_id", claims.UserID)
		c.Set("user_email", claims.Email)
		c.Set("family_id", claims.FamilyID)
		c.Set("user_role", claims.Role)
		c.Next()
	}
}

// GetUserID gets the user ID from the context
func GetUserID(c *gin.Context) (uint, bool) {
	userID, exists := c.Get("user_id")
	if !exists {
		return 0, false
	}
	return userID.(uint), true
}

// GetUserEmail gets the user email from the context
func GetUserEmail(c *gin.Context) (string, bool) {
	email, exists := c.Get("user_email")
	if !exists {
		return "", false
	}
	return email.(string), true
}

// GetFamilyID gets the active family ID from the context
func GetFamilyID(c *gin.Context) (uint, bool) {
	familyID, exists := c.Get("family_id")
	if !exists {
		return 0, false
	}
	return familyID.(uint), true
}

// GetUserRole gets the user role from the context
func GetUserRole(c *gin.Context) (string, bool) {
	role, exists := c.Get("user_role")
	if !exists {
		return "", false
	}
	return role.(string), true
}

// RequireRole enforces that the authenticated user has at least one of the allowed roles.
func RequireRole(allowed ...string) gin.HandlerFunc {
	allowedSet := map[string]struct{}{}
	for _, r := range allowed {
		allowedSet[r] = struct{}{}
	}

	return func(c *gin.Context) {
		role, ok := GetUserRole(c)
		if !ok {
			c.JSON(http.StatusForbidden, gin.H{"error": "Role not found in token"})
			c.Abort()
			return
		}

		if _, exists := allowedSet[role]; !exists {
			c.JSON(http.StatusForbidden, gin.H{"error": "Insufficient permissions"})
			c.Abort()
			return
		}

		c.Next()
	}
}
