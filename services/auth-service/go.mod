module wealthwatch/services/auth-service

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/golang-jwt/jwt/v5 v5.0.0
	github.com/joho/godotenv v1.5.1
	golang.org/x/crypto v0.13.0
	gorm.io/driver/postgres v1.5.2
	gorm.io/gorm v1.25.4
	wealthwatch/pkg v0.0.0
)

replace wealthwatch/pkg => ../../pkg
