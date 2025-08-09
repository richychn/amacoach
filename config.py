"""
Configuration settings for AmaCoach MCP server.

This module handles all configuration management including environment variables,
database settings, and security parameters.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for AmaCoach MCP server."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Database configuration
        self.database_path = os.getenv('DATABASE_PATH', 'amacoach.db')
        self.database_backup_enabled = os.getenv('DATABASE_BACKUP_ENABLED', 'true').lower() == 'true'
        self.database_backup_interval = int(os.getenv('DATABASE_BACKUP_INTERVAL', '3600'))  # seconds
        
        # Server configuration
        self.server_host = os.getenv('SERVER_HOST', '0.0.0.0')
        self.server_port = int(os.getenv('PORT', os.getenv('SERVER_PORT', '8080')))
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        # Security configuration
        self.oauth_client_id = os.getenv('OAUTH_CLIENT_ID')
        self.oauth_client_secret = os.getenv('OAUTH_CLIENT_SECRET')
        self.oauth_redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        self.jwt_secret_key = os.getenv('JWT_SECRET_KEY')
        self.token_expiry_hours = int(os.getenv('TOKEN_EXPIRY_HOURS', '24'))
        
        # Rate limiting configuration
        self.rate_limit_enabled = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        self.rate_limit_requests_per_minute = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))
        self.rate_limit_burst_size = int(os.getenv('RATE_LIMIT_BURST_SIZE', '10'))
        
        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_file = os.getenv('LOG_FILE', 'amacoach.log')
        self.audit_log_enabled = os.getenv('AUDIT_LOG_ENABLED', 'true').lower() == 'true'
        
        # Workout plan configuration
        self.default_rotation_weeks = int(os.getenv('DEFAULT_ROTATION_WEEKS', '6'))
        self.max_active_plans = int(os.getenv('MAX_ACTIVE_PLANS', '3'))
        self.max_exercises_per_plan = int(os.getenv('MAX_EXERCISES_PER_PLAN', '20'))
        
        # Exercise configuration
        self.max_difficulty_level = int(os.getenv('MAX_DIFFICULTY_LEVEL', '5'))
        self.min_difficulty_level = int(os.getenv('MIN_DIFFICULTY_LEVEL', '1'))
        
        # Performance configuration
        self.database_connection_pool_size = int(os.getenv('DATABASE_CONNECTION_POOL_SIZE', '10'))
        self.query_timeout_seconds = int(os.getenv('QUERY_TIMEOUT_SECONDS', '30'))
        
        # Railway-specific configuration
        self.railway_environment = os.getenv('RAILWAY_ENVIRONMENT')
        self.railway_project_id = os.getenv('RAILWAY_PROJECT_ID')
        self.railway_service_id = os.getenv('RAILWAY_SERVICE_ID')
        
        # Health check configuration
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))  # seconds
        self.health_check_timeout = int(os.getenv('HEALTH_CHECK_TIMEOUT', '5'))    # seconds

    def validate_config(self) -> bool:
        """Validate configuration and return True if valid."""
        errors = []
        
        # Check required OAuth configuration in production
        # More lenient for Railway deployment health checks
        if not self.debug_mode and not os.getenv('RAILWAY_ENVIRONMENT'):
            if not self.oauth_client_id or self.oauth_client_id == 'your_oauth_client_id':
                errors.append("OAUTH_CLIENT_ID is required in production")
            if not self.oauth_client_secret or self.oauth_client_secret == 'your_oauth_client_secret':
                errors.append("OAUTH_CLIENT_SECRET is required in production")
            if not self.jwt_secret_key or self.jwt_secret_key == 'your_jwt_secret_key_here':
                errors.append("JWT_SECRET_KEY is required in production")
        
        # Note: MAX_ACTIVE_PLANS is now informational only - no hard limits enforced
        # Validate numerical ranges for other settings
        
        if self.default_rotation_weeks < 1 or self.default_rotation_weeks > 52:
            errors.append("DEFAULT_ROTATION_WEEKS must be between 1 and 52")
        
        if self.max_difficulty_level < self.min_difficulty_level:
            errors.append("MAX_DIFFICULTY_LEVEL must be >= MIN_DIFFICULTY_LEVEL")
        
        if self.rate_limit_requests_per_minute < 1:
            errors.append("RATE_LIMIT_REQUESTS_PER_MINUTE must be >= 1")
        
        # Validate database path is writable
        db_dir = Path(self.database_path).parent
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                errors.append(f"Cannot create database directory: {db_dir}")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True

    def get_database_url(self) -> str:
        """Get SQLite database URL."""
        return f"sqlite:///{self.database_path}"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.railway_environment == 'production' or not self.debug_mode

    def get_log_config(self) -> dict:
        """Get logging configuration dictionary."""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': self.log_level,
                    'formatter': 'standard' if self.is_production() else 'detailed'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': self.log_file,
                    'level': self.log_level,
                    'formatter': 'detailed'
                }
            },
            'loggers': {
                '': {  # root logger
                    'handlers': ['console', 'file'] if self.log_file else ['console'],
                    'level': self.log_level,
                    'propagate': False
                }
            }
        }

    def __repr__(self) -> str:
        """String representation of configuration (without sensitive data)."""
        safe_config = {
            'database_path': self.database_path,
            'server_host': self.server_host,
            'server_port': self.server_port,
            'debug_mode': self.debug_mode,
            'rate_limit_enabled': self.rate_limit_enabled,
            'max_active_plans': self.max_active_plans,
            'default_rotation_weeks': self.default_rotation_weeks,
            'log_level': self.log_level,
            'is_production': self.is_production()
        }
        return f"Config({safe_config})"


# Global configuration instance
config = Config()


# Configuration validation constants
VALID_RECORD_TYPES = {'weight', 'reps', 'time', 'distance'}
VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
SUPPORTED_MUSCLE_GROUPS = {
    'chest', 'back', 'shoulders', 'biceps', 'triceps', 'forearms',
    'abs', 'obliques', 'lower_back', 'quadriceps', 'hamstrings', 
    'calves', 'glutes', 'cardio', 'full_body'
}
SUPPORTED_EQUIPMENT = {
    'bodyweight', 'dumbbells', 'barbell', 'resistance_bands', 
    'pull_up_bar', 'kettlebells', 'cable_machine', 'smith_machine',
    'bench', 'stability_ball', 'medicine_ball', 'foam_roller',
    'cardio_machine', 'yoga_mat'
}


def get_environment_template() -> str:
    """Get environment variable template for .env file."""
    return """# AmaCoach MCP Server Configuration Template

# Database Configuration
DATABASE_PATH=amacoach.db
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_INTERVAL=3600

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
DEBUG_MODE=false

# OAuth 2.1 Authentication (Required in production)
OAUTH_CLIENT_ID=your_oauth_client_id
OAUTH_CLIENT_SECRET=your_oauth_client_secret
OAUTH_REDIRECT_URI=https://your-domain.com/auth/callback
JWT_SECRET_KEY=your_jwt_secret_key_here
TOKEN_EXPIRY_HOURS=24

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=amacoach.log
AUDIT_LOG_ENABLED=true

# Workout Configuration
DEFAULT_ROTATION_WEEKS=6
MAX_ACTIVE_PLANS=unlimited
MAX_EXERCISES_PER_PLAN=20

# Exercise Configuration
MAX_DIFFICULTY_LEVEL=5
MIN_DIFFICULTY_LEVEL=1

# Performance
DATABASE_CONNECTION_POOL_SIZE=10
QUERY_TIMEOUT_SECONDS=30

# Health Checks
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=5

# Railway Configuration (Auto-populated by Railway)
# RAILWAY_ENVIRONMENT=
# RAILWAY_PROJECT_ID=
# RAILWAY_SERVICE_ID=
"""