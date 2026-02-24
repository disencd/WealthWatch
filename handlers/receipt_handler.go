package handlers

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"wealthwatch/middleware"
	"wealthwatch/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type ReceiptHandler struct {
	db *gorm.DB
}

func NewReceiptHandler(db *gorm.DB) *ReceiptHandler {
	return &ReceiptHandler{db: db}
}

func (h *ReceiptHandler) UploadReceipt(c *gin.Context) {
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

	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "File is required"})
		return
	}

	allowedTypes := map[string]bool{
		"image/jpeg":      true,
		"image/png":       true,
		"image/webp":      true,
		"application/pdf": true,
	}
	if !allowedTypes[file.Header.Get("Content-Type")] {
		c.JSON(http.StatusBadRequest, gin.H{"error": "File type not supported. Use JPEG, PNG, WebP, or PDF."})
		return
	}

	uploadDir := fmt.Sprintf("receipts/%d", familyID)
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create upload directory"})
		return
	}

	filename := fmt.Sprintf("%d_%s", time.Now().UnixNano(), filepath.Base(file.Filename))
	filePath := filepath.Join(uploadDir, filename)

	if err := c.SaveUploadedFile(file, filePath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save file"})
		return
	}

	var budgetExpenseID *uint
	if eid := c.PostForm("budget_expense_id"); eid != "" {
		if id, err := strconv.ParseUint(eid, 10, 32); err == nil {
			uid := uint(id)
			budgetExpenseID = &uid
		}
	}

	receipt := models.Receipt{
		FamilyID:        familyID,
		CreatedByUserID: userID,
		BudgetExpenseID: budgetExpenseID,
		FileName:        file.Filename,
		FilePath:        filePath,
		FileSize:        file.Size,
		MimeType:        file.Header.Get("Content-Type"),
		Merchant:        c.PostForm("merchant"),
		Notes:           c.PostForm("notes"),
	}

	if amountStr := c.PostForm("amount"); amountStr != "" {
		if amount, err := strconv.ParseFloat(amountStr, 64); err == nil {
			receipt.Amount = &amount
		}
	}

	if dateStr := c.PostForm("date"); dateStr != "" {
		if d, err := parseDate(dateStr); err == nil {
			receipt.Date = &d
		}
	}

	if err := h.db.Create(&receipt).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save receipt"})
		return
	}

	c.JSON(http.StatusCreated, receipt)
}

func (h *ReceiptHandler) ListReceipts(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	var receipts []models.Receipt
	q := h.db.Where("family_id = ?", familyID).Order("created_at DESC")

	if expenseID := c.Query("budget_expense_id"); expenseID != "" {
		q = q.Where("budget_expense_id = ?", expenseID)
	}

	if err := q.Find(&receipts).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch receipts"})
		return
	}

	c.JSON(http.StatusOK, receipts)
}

func (h *ReceiptHandler) GetReceipt(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
		return
	}

	var receipt models.Receipt
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&receipt).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Receipt not found"})
		return
	}

	c.JSON(http.StatusOK, receipt)
}

func (h *ReceiptHandler) DeleteReceipt(c *gin.Context) {
	familyID, ok := middleware.GetFamilyID(c)
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Family not found in token"})
		return
	}

	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid ID"})
		return
	}

	var receipt models.Receipt
	if err := h.db.Where("id = ? AND family_id = ?", uint(id), familyID).First(&receipt).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Receipt not found"})
		return
	}

	os.Remove(receipt.FilePath)

	if err := h.db.Delete(&receipt).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete receipt"})
		return
	}

	c.Status(http.StatusNoContent)
}
