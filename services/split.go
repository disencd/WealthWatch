package services

import (
	"splitwise/models"
	"splitwise/utils"

	"gorm.io/gorm"
)

type SplitService struct {
	db *gorm.DB
}

func NewSplitService(db *gorm.DB) *SplitService {
	return &SplitService{db: db}
}

type SplitType string

const (
	EqualSplit    SplitType = "equal"
	ExactSplit    SplitType = "exact"
	PercentageSplit SplitType = "percentage"
)

type SplitRequest struct {
	Type      SplitType                `json:"type" binding:"required"`
	Amount    float64                  `json:"amount" binding:"required,gt=0"`
	UserIDs   []uint                   `json:"user_ids" binding:"required,min=1"`
	Splits    map[uint]float64         `json:"splits,omitempty"`     // For exact splits
	Percentages map[uint]float64       `json:"percentages,omitempty"` // For percentage splits
}

// CalculateSplits calculates how an expense should be split among users
func (s *SplitService) CalculateSplits(req SplitRequest) ([]models.Split, error) {
	switch req.Type {
	case EqualSplit:
		return s.calculateEqualSplit(req.Amount, req.UserIDs)
	case ExactSplit:
		return s.calculateExactSplit(req.Amount, req.UserIDs, req.Splits)
	case PercentageSplit:
		return s.calculatePercentageSplit(req.Amount, req.UserIDs, req.Percentages)
	default:
		return nil, utils.NewValidationError("Invalid split type")
	}
}

// calculateEqualSplit splits amount equally among all users
func (s *SplitService) calculateEqualSplit(amount float64, userIDs []uint) ([]models.Split, error) {
	if len(userIDs) == 0 {
		return nil, utils.NewValidationError("At least one user is required")
	}

	splitAmount := amount / float64(len(userIDs))
	var splits []models.Split

	for _, userID := range userIDs {
		splits = append(splits, models.Split{
			UserID: userID,
			Amount: splitAmount,
		})
	}

	return splits, nil
}

// calculateExactSplit uses exact amounts provided for each user
func (s *SplitService) calculateExactSplit(totalAmount float64, userIDs []uint, exactSplits map[uint]float64) ([]models.Split, error) {
	var splits []models.Split
	var totalSplitAmount float64

	// Validate that all users have split amounts
	for _, userID := range userIDs {
		amount, exists := exactSplits[userID]
		if !exists {
			return nil, utils.NewValidationError("Split amount missing for user")
		}
		if amount <= 0 {
			return nil, utils.NewValidationError("Split amount must be greater than 0")
		}
		totalSplitAmount += amount
		splits = append(splits, models.Split{
			UserID: userID,
			Amount: amount,
		})
	}

	// Validate that split amounts sum to total
	if totalSplitAmount != totalAmount {
		return nil, utils.NewValidationError("Split amounts must sum to total expense amount")
	}

	return splits, nil
}

// calculatePercentageSplit uses percentages provided for each user
func (s *SplitService) calculatePercentageSplit(totalAmount float64, userIDs []uint, percentages map[uint]float64) ([]models.Split, error) {
	var splits []models.Split
	var totalPercentage float64

	// Validate percentages
	for _, userID := range userIDs {
		percentage, exists := percentages[userID]
		if !exists {
			return nil, utils.NewValidationError("Percentage missing for user")
		}
		if percentage <= 0 {
			return nil, utils.NewValidationError("Percentage must be greater than 0")
		}
		totalPercentage += percentage
		
		amount := (percentage / 100.0) * totalAmount
		splits = append(splits, models.Split{
			UserID:     userID,
			Amount:     amount,
			Percentage: percentage,
		})
	}

	// Validate that percentages sum to 100
	if totalPercentage != 100.0 {
		return nil, utils.NewValidationError("Percentages must sum to 100")
	}

	return splits, nil
}

// GetUserBalance calculates the balance between two users
func (s *SplitService) GetUserBalance(userID1, userID2 uint) (float64, error) {
	var balance float64

	// Calculate what user1 owes user2 (user1 is debtor, user2 is creditor)
	var expenses []models.Expense
	if err := s.db.Preload("Splits").Where("payer_id = ?", userID2).Find(&expenses).Error; err != nil {
		return 0, err
	}

	for _, expense := range expenses {
		for _, split := range expense.Splits {
			if split.UserID == userID1 {
				balance += split.Amount
			}
		}
	}

	// Calculate what user2 owes user1 (user2 is debtor, user1 is creditor)
	if err := s.db.Preload("Splits").Where("payer_id = ?", userID1).Find(&expenses).Error; err != nil {
		return 0, err
	}

	for _, expense := range expenses {
		for _, split := range expense.Splits {
			if split.UserID == userID2 {
				balance -= split.Amount
			}
		}
	}

	return balance, nil
}

// GetAllUserBalances calculates balances for a user with all other users
func (s *SplitService) GetAllUserBalances(userID uint) (map[uint]float64, error) {
	balances := make(map[uint]float64)

	// Get all expenses where user is involved (as payer or in splits)
	var expenses []models.Expense
	if err := s.db.Preload("Splits").Where("payer_id = ? OR id IN (SELECT expense_id FROM splits WHERE user_id = ?)", userID, userID).Find(&expenses).Error; err != nil {
		return nil, err
	}

	// Calculate balances
	for _, expense := range expenses {
		// User is the payer (they paid, others owe them)
		if expense.PayerID == userID {
			for _, split := range expense.Splits {
				if split.UserID != userID {
					balances[split.UserID] += split.Amount
				}
			}
		} else {
			// User is in splits (they owe the payer)
			for _, split := range expense.Splits {
				if split.UserID == userID {
					balances[expense.PayerID] -= split.Amount
					break
				}
			}
		}
	}

	return balances, nil
}
