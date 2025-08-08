#!/usr/bin/env python3
"""
Health check endpoint for AmaCoach MCP server.

This script provides health checks for Railway deployment monitoring
and can be used to verify server and database connectivity.
"""

import sys
import json
from datetime import datetime
from database import Database
from config import config

def health_check():
    """Perform comprehensive health check."""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "checks": {},
        "details": {}
    }
    
    try:
        # Database connectivity check
        db = Database(config.database_path)
        if db.health_check():
            health_status["checks"]["database"] = "healthy"
            health_status["details"]["database"] = "SQLite database accessible"
        else:
            health_status["checks"]["database"] = "unhealthy"
            health_status["details"]["database"] = "SQLite database not accessible"
            health_status["status"] = "degraded"
        
        # Configuration validation check
        if config.validate_config():
            health_status["checks"]["configuration"] = "healthy"
            health_status["details"]["configuration"] = "All required configuration valid"
        else:
            health_status["checks"]["configuration"] = "unhealthy"
            health_status["details"]["configuration"] = "Configuration validation failed"
            health_status["status"] = "unhealthy"
        
        # Database schema check (verify tables exist)
        try:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = {'users', 'exercises', 'workout_plans', 'planned_exercises', 'personal_records'}
                missing_tables = expected_tables - set(tables)
                
                if not missing_tables:
                    health_status["checks"]["schema"] = "healthy"
                    health_status["details"]["schema"] = f"All {len(expected_tables)} tables present"
                else:
                    health_status["checks"]["schema"] = "unhealthy"
                    health_status["details"]["schema"] = f"Missing tables: {missing_tables}"
                    health_status["status"] = "unhealthy"
        
        except Exception as e:
            health_status["checks"]["schema"] = "unhealthy"
            health_status["details"]["schema"] = f"Schema check failed: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Basic functionality check (can create test user)
        try:
            test_user_id = f"health_check_{int(datetime.now().timestamp())}"
            user = db.create_user(test_user_id, "Health Check User")
            if user:
                health_status["checks"]["basic_operations"] = "healthy"
                health_status["details"]["basic_operations"] = "Can create and retrieve users"
            else:
                health_status["checks"]["basic_operations"] = "unhealthy"
                health_status["details"]["basic_operations"] = "Cannot create users"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["basic_operations"] = "unhealthy"
            health_status["details"]["basic_operations"] = f"Basic operations failed: {str(e)}"
            health_status["status"] = "degraded"
        
        # Environment check
        if config.is_production():
            health_status["checks"]["environment"] = "production"
            health_status["details"]["environment"] = "Running in production mode"
        else:
            health_status["checks"]["environment"] = "development"
            health_status["details"]["environment"] = "Running in development mode"
            
        # Add system info
        health_status["details"]["version"] = "1.0.0"
        health_status["details"]["max_active_plans"] = config.max_active_plans
        health_status["details"]["default_rotation_weeks"] = config.default_rotation_weeks
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["system"] = "unhealthy"
        health_status["details"]["system_error"] = str(e)
    
    return health_status

def main():
    """Main health check entry point."""
    result = health_check()
    
    # Print JSON result
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    if result["status"] == "healthy":
        sys.exit(0)  # Success
    elif result["status"] == "degraded":
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Critical

if __name__ == "__main__":
    main()