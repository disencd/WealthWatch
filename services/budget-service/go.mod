module splitwise/services/budget-service

go 1.23

require (
	github.com/gin-gonic/gin v1.10.0
	gorm.io/driver/postgres v1.5.7
	gorm.io/gorm v1.25.12
)

replace splitwise/pkg => ../../pkg
