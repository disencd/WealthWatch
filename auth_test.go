package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"wealthwatch/models"
	"wealthwatch/routes"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// setupTestDB creates an in-memory SQLite database for testing
func setupTestDB() *gorm.DB {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		panic("failed to connect database")
	}

	// Auto-migrate all models
	models.AutoMigrate(db)

	return db
}

// setupTestRouter creates a test router with in-memory database
func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)

	db := setupTestDB()
	router := gin.New()
	routes.SetupRoutes(router, db)

	return router
}

func TestHealthCheck(t *testing.T) {
	router := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "ok", response["status"])
}

func TestUserRegistration(t *testing.T) {
	router := setupTestRouter()

	userData := map[string]interface{}{
		"first_name": "John",
		"last_name":  "Doe",
		"email":      "john.doe@example.com",
		"password":   "password123",
		"phone":      "1234567890",
	}

	jsonData, _ := json.Marshal(userData)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Contains(t, response, "token")
	assert.Contains(t, response, "user")
}

func TestUserLogin(t *testing.T) {
	router := setupTestRouter()

	// First register a user
	userData := map[string]interface{}{
		"first_name": "Jane",
		"last_name":  "Smith",
		"email":      "jane.smith@example.com",
		"password":   "password123",
	}

	jsonData, _ := json.Marshal(userData)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	// Now login with the same user
	loginData := map[string]interface{}{
		"email":    "jane.smith@example.com",
		"password": "password123",
	}

	loginJsonData, _ := json.Marshal(loginData)

	w = httptest.NewRecorder()
	req, _ = http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer(loginJsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Contains(t, response, "token")
	assert.Contains(t, response, "user")
}

func TestInvalidLogin(t *testing.T) {
	router := setupTestRouter()

	loginData := map[string]interface{}{
		"email":    "nonexistent@example.com",
		"password": "wrongpassword",
	}

	jsonData, _ := json.Marshal(loginData)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestProtectedRouteWithoutToken(t *testing.T) {
	router := setupTestRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/v1/profile", nil)
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestProtectedRouteWithToken(t *testing.T) {
	router := setupTestRouter()

	// First register and login to get token
	userData := map[string]interface{}{
		"first_name": "Test",
		"last_name":  "User",
		"email":      "test.user@example.com",
		"password":   "password123",
	}

	jsonData, _ := json.Marshal(userData)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	var registerResponse map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &registerResponse)
	assert.NoError(t, err)

	token, ok := registerResponse["token"].(string)
	assert.True(t, ok, "Token should be a string")

	// Now access protected route with token
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/api/v1/profile", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err = json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Test", response["first_name"])
	assert.Equal(t, "User", response["last_name"])
}
