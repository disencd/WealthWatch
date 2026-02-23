package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCreateExpense(t *testing.T) {
	router := setupTestRouter()
	
	// First register and login to get token
	userData := map[string]interface{}{
		"first_name": "John",
		"last_name":  "Doe",
		"email":      "john.expense@example.com",
		"password":   "password123",
	}
	
	jsonData, _ := json.Marshal(userData)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	var registerResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &registerResponse)
	token := registerResponse["token"].(string)
	user := registerResponse["user"].(map[string]interface{})
	userID := uint(user["id"].(float64))
	
	// Create an expense
	expenseData := map[string]interface{}{
		"title":       "Dinner",
		"description": "Team dinner at restaurant",
		"amount":      120.00,
		"currency":    "USD",
		"date":        "2024-01-15T19:00:00Z",
		"splits": []map[string]interface{}{
			{"user_id": userID, "amount": 60.00},
			{"user_id": userID, "amount": 60.00},
		},
	}
	
	expenseJsonData, _ := json.Marshal(expenseData)
	
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("POST", "/api/v1/expenses", bytes.NewBuffer(expenseJsonData))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, "Dinner", response["title"])
	assert.Equal(t, 120.00, response["amount"])
}

func TestGetExpenses(t *testing.T) {
	router := setupTestRouter()
	
	// Register and login
	userData := map[string]interface{}{
		"first_name": "Jane",
		"last_name":  "Smith",
		"email":      "jane.expense@example.com",
		"password":   "password123",
	}
	
	jsonData, _ := json.Marshal(userData)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	var registerResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &registerResponse)
	token := registerResponse["token"].(string)
	
	// Get expenses (should be empty initially)
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("GET", "/api/v1/expenses", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response []interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, 0, len(response)) // No expenses yet
}

func TestCreateExpenseInvalidData(t *testing.T) {
	router := setupTestRouter()
	
	// Register and login
	userData := map[string]interface{}{
		"first_name": "Bob",
		"last_name":  "Wilson",
		"email":      "bob.invalid@example.com",
		"password":   "password123",
	}
	
	jsonData, _ := json.Marshal(userData)
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, req)
	
	var registerResponse map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &registerResponse)
	token := registerResponse["token"].(string)
	
	// Try to create expense with invalid data (missing required fields)
	invalidExpenseData := map[string]interface{}{
		"title": "", // Empty title should fail validation
		"amount": -10.00, // Negative amount should fail
	}
	
	invalidJsonData, _ := json.Marshal(invalidExpenseData)
	
	w = httptest.NewRecorder()
	req, _ = http.NewRequest("POST", "/api/v1/expenses", bytes.NewBuffer(invalidJsonData))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
}
