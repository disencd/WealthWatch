package config

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	Environment   string
	Database      DatabaseConfig
	Redis         RedisConfig
	JWT           JWTConfig
	AuthService   ServiceConfig
	UserService   ServiceConfig
	ExpenseService ServiceConfig
	BalanceService ServiceConfig
	SettlementService ServiceConfig
	NotificationService ServiceConfig
	APIGateway    APIGatewayConfig
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	DBName   string
	SSLMode  string
	MaxOpenConns int
	MaxIdleConns int
	ConnMaxLifetime time.Duration
}

type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
	PoolSize int
}

type JWTConfig struct {
	Secret          string
	ExpiresIn       time.Duration
	RefreshExpiresIn time.Duration
}

type ServiceConfig struct {
	Port string
	Host string
}

type APIGatewayConfig struct {
	Port string
	Host string
}

func LoadConfig() (*Config, error) {
	// Load .env file if it exists
	if err := godotenv.Load(); err != nil {
		// .env file not found, continue with environment variables
	}

	cfg := &Config{
		Environment: getEnv("ENVIRONMENT", "development"),
		Database: DatabaseConfig{
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnv("DB_PORT", "5432"),
			User:     getEnv("DB_USER", "splitwise"),
			Password: getEnv("DB_PASSWORD", "password"),
			DBName:   getEnv("DB_NAME", "splitwise"),
			SSLMode:  getEnv("DB_SSLMODE", "disable"),
			MaxOpenConns: getEnvAsInt("DB_MAX_OPEN_CONNS", 25),
			MaxIdleConns: getEnvAsInt("DB_MAX_IDLE_CONNS", 5),
			ConnMaxLifetime: getEnvAsDuration("DB_CONN_MAX_LIFETIME", 5*time.Minute),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       getEnvAsInt("REDIS_DB", 0),
			PoolSize: getEnvAsInt("REDIS_POOL_SIZE", 10),
		},
		JWT: JWTConfig{
			Secret:          getEnv("JWT_SECRET", "your-super-secret-jwt-key"),
			ExpiresIn:       getEnvAsDuration("JWT_EXPIRES_IN", 24*time.Hour),
			RefreshExpiresIn: getEnvAsDuration("JWT_REFRESH_EXPIRES_IN", 7*24*time.Hour),
		},
		AuthService: ServiceConfig{
			Port: getEnv("AUTH_SERVICE_PORT", "8001"),
			Host: getEnv("AUTH_SERVICE_HOST", "auth-service"),
		},
		UserService: ServiceConfig{
			Port: getEnv("USER_SERVICE_PORT", "8002"),
			Host: getEnv("USER_SERVICE_HOST", "user-service"),
		},
		ExpenseService: ServiceConfig{
			Port: getEnv("EXPENSE_SERVICE_PORT", "8003"),
			Host: getEnv("EXPENSE_SERVICE_HOST", "expense-service"),
		},
		BalanceService: ServiceConfig{
			Port: getEnv("BALANCE_SERVICE_PORT", "8004"),
			Host: getEnv("BALANCE_SERVICE_HOST", "balance-service"),
		},
		SettlementService: ServiceConfig{
			Port: getEnv("SETTLEMENT_SERVICE_PORT", "8005"),
			Host: getEnv("SETTLEMENT_SERVICE_HOST", "settlement-service"),
		},
		NotificationService: ServiceConfig{
			Port: getEnv("NOTIFICATION_SERVICE_PORT", "8006"),
			Host: getEnv("NOTIFICATION_SERVICE_HOST", "notification-service"),
		},
		APIGateway: APIGatewayConfig{
			Port: getEnv("API_GATEWAY_PORT", "8080"),
			Host: getEnv("API_GATEWAY_HOST", "api-gateway"),
		},
	}

	// Validate required fields
	if cfg.JWT.Secret == "your-super-secret-jwt-key" && cfg.Environment == "production" {
		return nil, fmt.Errorf("JWT_SECRET must be set in production")
	}

	return cfg, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvAsDuration(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}

func (c *Config) GetDatabaseDSN() string {
	return fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=%s",
		c.Database.Host,
		c.Database.User,
		c.Database.Password,
		c.Database.DBName,
		c.Database.Port,
		c.Database.SSLMode,
	)
}

func (c *Config) GetRedisAddr() string {
	return fmt.Sprintf("%s:%s", c.Redis.Host, c.Redis.Port)
}

func (c *Config) IsDevelopment() bool {
	return c.Environment == "development"
}

func (c *Config) IsProduction() bool {
	return c.Environment == "production"
}
