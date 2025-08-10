"""
AmaCoach MCP Server Implementation.

This is the main MCP server that exposes the 7 required tools to Claude.ai:
1. list_exercises
2. create_exercise  
3. save_workout_plan
4. load_workout_plan
5. save_personal_record
6. load_personal_records
7. generate_workout_guidance

The server provides secure data storage and retrieval with user isolation.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability, ResourcesCapability
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl
from mcp.server.streamable_http import StreamableHTTPServerTransport
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route
import secrets
import time
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from datetime import datetime, timedelta

from database import Database, DatabaseError, UserPermissionError
from models import User
from config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)

# Initialize database
db = Database(config.database_path)

# Create MCP server
server = Server("amacoach")

# OAuth 2.1 configuration
OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "amacoach-client")
OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", secrets.token_hex(32))
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# In-memory token store (use Redis/database in production)
oauth_tokens = {}
refresh_tokens = {}


def get_user_from_context(context) -> str:
    """
    Extract user ID from MCP context.
    In production, this would validate OAuth tokens and extract user identity.
    For development, we'll use a default user or extract from context.
    """
    # In production: validate Bearer token and extract user_id from JWT
    # For development: use default user or extract from request context
    if context and hasattr(context, 'user_id'):
        return context.user_id
    
    # Development fallback - in production this should validate OAuth tokens
    return "default_user"


def ensure_user_exists(user_id: str) -> User:
    """Ensure user exists in database, create if first time."""
    user = db.get_user(user_id)
    if not user:
        # Create user with default name (in production, get from OAuth profile)
        user = db.create_user(user_id, f"User_{user_id}")
        logger.info(f"Created new user: {user_id}")
        if not user:
            raise DatabaseError(f"Failed to create user: {user_id}")
    return user


def handle_database_error(error: Exception) -> Dict[str, Any]:
    """Handle database errors and return appropriate error response."""
    if isinstance(error, UserPermissionError):
        return {"error": "Access denied", "message": str(error), "code": 403}
    elif isinstance(error, DatabaseError):
        logger.error(f"Database error: {str(error)}")
        return {"error": "Database error", "message": "Internal database error", "code": 500}
    elif isinstance(error, ValueError):
        return {"error": "Invalid input", "message": str(error), "code": 400}
    else:
        logger.error(f"Unexpected error: {str(error)}")
        return {"error": "Internal error", "message": "An unexpected error occurred", "code": 500}


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="list_exercises",
            description="Return available exercises with optional filters for muscle group, equipment, and difficulty",
            inputSchema={
                "type": "object",
                "properties": {
                    "muscle_group": {
                        "type": "string",
                        "description": "Filter exercises by muscle group"
                    },
                    "equipment": {
                        "type": "string", 
                        "description": "Filter exercises by required equipment"
                    },
                    "difficulty": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Filter exercises by difficulty level (1-5)"
                    }
                }
            }
        ),
        Tool(
            name="create_exercise",
            description="Add new exercises to the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Exercise name (must be unique)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of the exercise"
                    },
                    "muscle_groups": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of muscle groups targeted by this exercise"
                    },
                    "equipment_needed": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "List of equipment required for this exercise"
                    },
                    "difficulty_level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Difficulty level from 1 (beginner) to 5 (expert)"
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Step-by-step exercise instructions"
                    }
                },
                "required": ["name", "description", "muscle_groups", "equipment_needed", "difficulty_level", "instructions"]
            }
        ),
        Tool(
            name="save_workout_plan",
            description="Store workout plans for users (unlimited plans allowed, with lifecycle management for Claude's 3-plan sets)",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_name": {
                        "type": "string",
                        "description": "Name of the workout plan"
                    },
                    "exercises_list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "exercise_id": {"type": "integer"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "integer"},
                                "weight": {"type": "number"},
                                "duration": {"type": "integer"},
                                "notes": {"type": "string"}
                            },
                            "required": ["exercise_id", "sets", "reps"]
                        },
                        "description": "List of exercises in the workout plan"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the workout plan"
                    },
                    "create_as_set": {
                        "type": "boolean",
                        "description": "Set to true when creating the FIRST plan of a 3-plan set. This will deactivate all existing active plans to maintain clean lifecycle."
                    }
                },
                "required": ["plan_name", "exercises_list"]
            }
        ),
        Tool(
            name="load_workout_plan",
            description="Retrieve stored workout plans for the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "integer",
                        "description": "Specific plan ID to load (optional - if omitted, returns all active plans)"
                    }
                }
            }
        ),
        Tool(
            name="save_personal_record",
            description="Store user personal bests/records",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise_name": {
                        "type": "string",
                        "description": "Name of the exercise"
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["weight", "reps", "time", "distance"],
                        "description": "Type of personal record"
                    },
                    "value": {
                        "type": "number",
                        "description": "The record value (weight in lbs/kg, reps count, time in seconds, distance in miles/km)"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit of measurement (lbs, kg, seconds, miles, km, etc.)"
                    },
                    "date": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Date the record was achieved (ISO format, optional - defaults to now)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the record"
                    }
                },
                "required": ["exercise_name", "record_type", "value", "unit"]
            }
        ),
        Tool(
            name="load_personal_records",
            description="Retrieve user personal records with optional filters",
            inputSchema={
                "type": "object", 
                "properties": {
                    "exercise_name": {
                        "type": "string",
                        "description": "Filter records by exercise name (optional)"
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["weight", "reps", "time", "distance"],
                        "description": "Filter records by type (optional)"
                    }
                }
            }
        ),
        Tool(
            name="generate_workout_guidance",
            description="**USE THIS FIRST** when users ask for workout planning help. Provides detailed guidance for creating new complementary 3-plan workout sets with available exercises and rotation recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID for generating personalized guidance"
                    },
                    "equipment_available": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of available equipment to filter exercises (optional)"
                    },
                    "muscle_focus": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "List of muscle groups to focus on (optional)"
                    }
                },
                "required": ["user_id"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any], context=None) -> List[TextContent]:
    """Handle tool calls from Claude."""
    try:
        # Get user ID from context and ensure user exists
        user_id = get_user_from_context(context)
        ensure_user_exists(user_id)
        
        if name == "list_exercises":
            return await handle_list_exercises(arguments, user_id)
        elif name == "create_exercise":
            return await handle_create_exercise(arguments, user_id)
        elif name == "save_workout_plan":
            return await handle_save_workout_plan(arguments, user_id)
        elif name == "load_workout_plan":
            return await handle_load_workout_plan(arguments, user_id)
        elif name == "save_personal_record":
            return await handle_save_personal_record(arguments, user_id)
        elif name == "load_personal_records":
            return await handle_load_personal_records(arguments, user_id)
        elif name == "generate_workout_guidance":
            return await handle_generate_workout_guidance(arguments, user_id)
        else:
            error_msg = f"Unknown tool: {name}"
            logger.error(error_msg)
            return [TextContent(type="text", text=json.dumps({"error": error_msg}))]
            
    except Exception as e:
        error_response = handle_database_error(e)
        logger.error(f"Tool call failed for {name}: {str(e)}")
        return [TextContent(type="text", text=json.dumps(error_response))]


async def handle_list_exercises(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle list_exercises tool call."""
    muscle_group = arguments.get("muscle_group")
    equipment = arguments.get("equipment")
    difficulty = arguments.get("difficulty")
    
    exercises = db.list_exercises(muscle_group, equipment, difficulty)
    
    exercise_list = [exercise.to_dict() for exercise in exercises]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "exercises": exercise_list,
            "count": len(exercise_list),
            "filters_applied": {
                "muscle_group": muscle_group,
                "equipment": equipment, 
                "difficulty": difficulty
            }
        })
    )]


async def handle_create_exercise(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle create_exercise tool call."""
    name = arguments["name"]
    description = arguments["description"]
    muscle_groups = arguments["muscle_groups"]
    equipment_needed = arguments["equipment_needed"]
    difficulty_level = arguments["difficulty_level"]
    instructions = arguments["instructions"]
    
    exercise = db.create_exercise(
        name=name,
        description=description,
        muscle_groups=muscle_groups,
        equipment_needed=equipment_needed,
        difficulty_level=difficulty_level,
        instructions=instructions,
        created_by_user_id=user_id
    )
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "message": f"Exercise '{name}' created successfully",
            "exercise": exercise.to_dict()
        })
    )]


async def handle_save_workout_plan(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle save_workout_plan tool call."""
    plan_name = arguments["plan_name"]
    exercises_list = arguments["exercises_list"]
    notes = arguments.get("notes")
    create_as_set = arguments.get("create_as_set", False)
    
    # Validate exercises exist
    for exercise_data in exercises_list:
        exercise = db.get_exercise_by_id(exercise_data["exercise_id"])
        if not exercise:
            raise ValueError(f"Exercise ID {exercise_data['exercise_id']} not found")
    
    plan = db.save_workout_plan(
        user_id=user_id,
        plan_name=plan_name,
        exercises_list=exercises_list,
        notes=notes,
        create_as_set=create_as_set
    )
    
    message = f"Workout plan '{plan_name}' saved successfully"
    if create_as_set:
        message += " (Previous active plans deactivated for new plan set)"
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "message": message,
            "plan_id": plan.plan_id,
            "plan": plan.to_dict()
        })
    )]


async def handle_load_workout_plan(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle load_workout_plan tool call."""
    plan_id = arguments.get("plan_id")
    
    result = db.load_workout_plan(user_id, plan_id)
    
    if plan_id:
        # Single plan requested
        if result is None:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "message": f"Workout plan {plan_id} not found or not accessible"
                })
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "workout_plan": result
            })
        )]
    else:
        # All active plans requested - result is a List[WorkoutPlan]
        if isinstance(result, list):
            plans_data = [plan.to_dict() for plan in result]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "active_plans": plans_data,
                    "count": len(plans_data)
                })
            )]
        else:
            # Handle unexpected return type
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "message": "Unexpected data format returned from database"
                })
            )]


async def handle_save_personal_record(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle save_personal_record tool call."""
    exercise_name = arguments["exercise_name"]
    record_type = arguments["record_type"]
    value = arguments["value"]
    unit = arguments["unit"]
    date_str = arguments.get("date")
    notes = arguments.get("notes")
    
    date = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else None
    
    record = db.save_personal_record(
        user_id=user_id,
        exercise_name=exercise_name,
        record_type=record_type,
        value=value,
        unit=unit,
        date=date,
        notes=notes
    )
    
    return [TextContent(
        type="text", 
        text=json.dumps({
            "success": True,
            "message": f"Personal record saved for {exercise_name}",
            "record": record.to_dict()
        })
    )]


async def handle_load_personal_records(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle load_personal_records tool call."""
    exercise_name = arguments.get("exercise_name")
    record_type = arguments.get("record_type")
    
    records = db.load_personal_records(user_id, exercise_name, record_type)
    records_data = [record.to_dict() for record in records]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "personal_records": records_data,
            "count": len(records_data),
            "filters_applied": {
                "exercise_name": exercise_name,
                "record_type": record_type
            }
        })
    )]


async def handle_generate_workout_guidance(arguments: Dict[str, Any], user_id: str) -> List[TextContent]:
    """Handle generate_workout_guidance tool call."""
    # Extract arguments
    request_user_id = arguments["user_id"]
    equipment_available = arguments.get("equipment_available", [])
    muscle_focus = arguments.get("muscle_focus", [])
    
    # Validate that the requesting user matches the authenticated user
    if request_user_id != user_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Access denied: Cannot generate guidance for different user",
                "message": "User can only generate guidance for their own account"
            })
        )]
    
    # Get user information for cycle data
    user = db.get_user(user_id)
    if not user:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "User not found",
                "message": f"User {user_id} not found in database"
            })
        )]
    
    # Get available exercises with filtering
    exercises = []
    
    if equipment_available:
        # Get union of exercises that work with ANY of the specified equipment
        equipment_exercise_ids = set()
        for equipment in equipment_available:
            filtered_exercises = db.list_exercises(equipment=equipment)
            equipment_exercise_ids.update(ex.exercise_id for ex in filtered_exercises)
        
        # Get all exercises that match any of the equipment
        all_exercises = db.list_exercises()
        exercises = [ex for ex in all_exercises if ex.exercise_id in equipment_exercise_ids]
    else:
        exercises = db.list_exercises()
    
    # Further filter by muscle focus if specified
    if muscle_focus and exercises:
        # Get union of exercises that target ANY of the specified muscle groups
        muscle_exercise_ids = set()
        for muscle_group in muscle_focus:
            muscle_exercises = db.list_exercises(muscle_group=muscle_group)
            muscle_exercise_ids.update(ex.exercise_id for ex in muscle_exercises)
        
        # Keep only exercises that match both equipment and muscle criteria
        equipment_exercise_ids = {ex.exercise_id for ex in exercises}
        final_exercise_ids = equipment_exercise_ids.intersection(muscle_exercise_ids)
        exercises = [ex for ex in exercises if ex.exercise_id in final_exercise_ids]
    
    # Get current active plan count
    active_plan_count = db.get_active_plan_count(user_id)
    
    # Check rotation status
    needs_rotation = False
    days_until_rotation = None
    if user.last_rotation_date:
        from datetime import timedelta
        rotation_interval = timedelta(weeks=user.rotation_weeks)
        next_rotation_date = user.last_rotation_date + rotation_interval
        days_until_rotation = (next_rotation_date - datetime.now()).days
        needs_rotation = days_until_rotation <= 0
    
    # Generate complementary plan suggestions
    plan_suggestions = [
        {
            "name": "Push Day",
            "focus": "Chest, Shoulders, Triceps",
            "description": "Focus on pushing movements - bench press, shoulder press, tricep exercises"
        },
        {
            "name": "Pull Day", 
            "focus": "Back, Biceps",
            "description": "Focus on pulling movements - rows, pulldowns, bicep exercises"
        },
        {
            "name": "Legs Day",
            "focus": "Quadriceps, Hamstrings, Glutes, Calves",
            "description": "Focus on lower body - squats, deadlifts, leg exercises"
        }
    ]
    
    # Alternative split suggestions
    alternative_splits = [
        {
            "type": "Upper/Lower/Full",
            "plans": [
                {"name": "Upper Body", "focus": "Chest, Back, Shoulders, Arms"},
                {"name": "Lower Body", "focus": "Legs, Glutes"}, 
                {"name": "Full Body", "focus": "Total body compound movements"}
            ]
        },
        {
            "type": "Strength/Hypertrophy/Conditioning",
            "plans": [
                {"name": "Strength", "focus": "Heavy compound movements, low reps"},
                {"name": "Hypertrophy", "focus": "Muscle building, moderate reps"},
                {"name": "Conditioning", "focus": "Cardio and endurance exercises"}
            ]
        }
    ]
    
    # Convert exercises to simple format for guidance
    exercise_list = [ex.to_dict() for ex in exercises]
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "guidance": {
                "instruction": "Create 3 complementary workout plans using ONLY the exercises provided below. This ensures consistency and proper progression tracking.",
                "plan_status": f"You currently have {active_plan_count} active plans. There is no maximum limit - you can create as many plans as needed.",
                "lifecycle_management": "When creating a 3-plan set, use create_as_set=true for the FIRST plan only. This will deactivate previous active plans and start a fresh rotation cycle.",
                "recommended_splits": plan_suggestions,
                "alternative_splits": alternative_splits,
                "available_exercises": {
                    "count": len(exercise_list),
                    "exercises": exercise_list,
                    "filtered_by": {
                        "equipment": equipment_available if equipment_available else None,
                        "muscle_focus": muscle_focus if muscle_focus else None
                    }
                },
                "user_cycle_info": {
                    "current_cycle": user.current_cycle_number,
                    "rotation_weeks": user.rotation_weeks,
                    "last_rotation": user.last_rotation_date.isoformat() if user.last_rotation_date else None,
                    "needs_rotation": needs_rotation,
                    "days_until_rotation": days_until_rotation
                },
                "usage_instructions": [
                    "1. Choose one of the recommended split types (Push/Pull/Legs is most popular)",
                    "2. Draft exactly 3 plans using the provided exercises",
                    "3. Ensure each plan targets different muscle groups for proper recovery",
                    "4. **IMPORTANT**: Present all 3 plans to user and get explicit approval before saving ANY plans",
                    "5. **DO NOT SAVE** until user says they're happy with all 3 plans",
                    "6. For the FIRST plan: Use save_workout_plan with create_as_set=true",
                    "7. For the 2nd and 3rd plans: Use save_workout_plan with create_as_set=false (or omit)",
                    "8. All exercises must come from the 'available_exercises' list above"
                ]
            }
        })
    )]




@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources (none for this implementation)."""
    return []


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """Read resource content (none for this implementation)."""
    raise ValueError(f"Resource not found: {uri}")


async def health_check() -> bool:
    """Perform health check on server and database."""
    try:
        # Check database connectivity
        if not db.health_check():
            logger.error("Database health check failed")
            return False
        
        # Check configuration
        if not config.validate_config():
            logger.error("Configuration validation failed") 
            return False
        
        return True
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False


async def run_http_server():
    """Run simple HTTP server for Railway health checks."""
    from aiohttp import web
    
    async def health_handler(request):
        """Handle health check requests."""
        if await health_check():
            return web.Response(text='{"status": "healthy"}', content_type='application/json')
        else:
            return web.Response(text='{"status": "unhealthy"}', content_type='application/json', status=503)
    
    app = web.Application()
    app.router.add_get('/health', health_handler)
    
    port = int(config.server_port)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"HTTP health server running on port {port}")


async def main():
    """Main server entry point."""
    import os
    
    try:
        # Validate configuration
        if not config.validate_config():
            logger.error("Configuration validation failed")
            return
        
        # Perform initial health check
        if not await health_check():
            logger.error("Initial health check failed")
            return
            
        logger.info("AmaCoach MCP Server starting up...")
        logger.info(f"Database path: {config.database_path}")
        logger.info(f"Debug mode: {config.debug_mode}")
        logger.info("Plan limits: Unlimited active plans with Claude 3-plan set lifecycle management")
        
        # Check if HTTP_MODE environment variable is set for MCP-over-HTTP
        if os.getenv('HTTP_MODE') == 'true' or os.getenv('PORT'):
            # MCP-over-HTTP mode - serve MCP protocol for Claude.ai Remote MCP
            logger.info("MCP-over-HTTP mode detected - starting MCP HTTP server")
            port = int(os.environ.get("PORT", 8000))
            
            # OAuth 2.1 helper functions
            def create_access_token(data: dict, expires_delta: timedelta | None = None):
                to_encode = data.copy()
                if expires_delta:
                    expire = datetime.utcnow() + expires_delta
                else:
                    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                to_encode.update({"exp": expire})
                return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            
            def verify_token(token: str):
                try:
                    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                    return payload
                except ExpiredSignatureError:
                    return None
                except JWTError:
                    return None
            
            # OAuth 2.1 endpoints
            async def oauth_authorize(request):
                """OAuth 2.1 authorization endpoint"""
                # Simplified authorization - in production, show login form
                client_id = request.query_params.get("client_id")
                redirect_uri = request.query_params.get("redirect_uri") 
                state = request.query_params.get("state")
                
                if client_id != OAUTH_CLIENT_ID:
                    return PlainTextResponse("Invalid client_id", status_code=400)
                
                # Generate authorization code
                auth_code = secrets.token_hex(32)
                oauth_tokens[auth_code] = {
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "expires": time.time() + 600,  # 10 minutes
                    "user_id": "claude_user"  # Default user for Claude
                }
                
                # Redirect back with authorization code
                redirect_url = f"{redirect_uri}?code={auth_code}&state={state}"
                return JSONResponse({"redirect_url": redirect_url})
            
            async def oauth_token(request):
                """OAuth 2.1 token endpoint"""
                form = await request.form()
                grant_type = form.get("grant_type")
                
                if grant_type == "authorization_code":
                    code = form.get("code")
                    client_id = form.get("client_id")
                    client_secret = form.get("client_secret")
                    
                    # Validate client credentials
                    if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
                        return JSONResponse({"error": "invalid_client"}, status_code=401)
                    
                    # Validate authorization code
                    if code not in oauth_tokens or oauth_tokens[code]["expires"] < time.time():
                        return JSONResponse({"error": "invalid_grant"}, status_code=400)
                    
                    auth_data = oauth_tokens[code]
                    del oauth_tokens[code]  # Use code only once
                    
                    # Create access token
                    access_token = create_access_token({
                        "sub": auth_data["user_id"],
                        "client_id": client_id,
                        "scope": "mcp"
                    })
                    
                    # Create refresh token
                    refresh_token = secrets.token_hex(32)
                    refresh_tokens[refresh_token] = {
                        "user_id": auth_data["user_id"],
                        "client_id": client_id,
                        "expires": time.time() + 86400 * 30  # 30 days
                    }
                    
                    return JSONResponse({
                        "access_token": access_token,
                        "token_type": "Bearer",
                        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                        "refresh_token": refresh_token,
                        "scope": "mcp"
                    })
                
                return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
            
            class MCPEndpoint:
                """MCP-over-HTTP endpoint with OAuth authentication"""
                
                def __init__(self):
                    self.transport = StreamableHTTPServerTransport(
                        mcp_session_id=None,
                        is_json_response_enabled=False
                    )
                
                async def __call__(self, scope, receive, send):
                    # Extract auth header from scope
                    auth_header = ""
                    for header_name, header_value in scope.get("headers", []):
                        if header_name == b"authorization":
                            auth_header = header_value.decode("utf-8")
                            break
                    
                    # OAuth 2.1 authentication
                    if not auth_header.startswith("Bearer "):
                        response = PlainTextResponse("Missing or invalid authorization header", status_code=401)
                        await response(scope, receive, send)
                        return
                    
                    token = auth_header[7:]
                    payload = verify_token(token)
                    if not payload:
                        response = PlainTextResponse("Invalid or expired token", status_code=401)
                        await response(scope, receive, send)
                        return
                    
                    # Add user context to scope
                    scope["user_id"] = payload.get("sub", "claude_user")
                    
                    # Handle MCP request
                    await self.transport.handle_request(scope, receive, send)
            
            mcp_endpoint = MCPEndpoint()
            
            from starlette.routing import Mount
            
            # Public health endpoint (no auth required)
            async def http_health_check(request):
                logger.info("HTTP health check accessed")
                return PlainTextResponse("OK", status_code=200)
            
            app = Starlette(routes=[
                Route("/health", http_health_check, methods=["GET"]),  # Health check first (no auth)
                Route("/oauth/authorize", oauth_authorize, methods=["GET", "POST"]),
                Route("/oauth/token", oauth_token, methods=["POST"]),
                Route("/mcp", mcp_endpoint, methods=["GET", "POST"]),  # MCP endpoint at /mcp
                Route("/", mcp_endpoint, methods=["GET", "POST"]),  # Root MCP endpoint
            ])
            
            # Start uvicorn server
            uvicorn_config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=port,
                log_level="info"
            )
            server_instance = uvicorn.Server(uvicorn_config)
            await server_instance.serve()
            
        elif os.getenv('RAILWAY_ENVIRONMENT'):
            # Railway deployment - run HTTP server for health checks only
            logger.info("Railway environment detected - starting HTTP health server")
            await run_http_server()
            
            # Keep the process alive
            import asyncio
            await asyncio.Event().wait()
        else:
            # Local development - run MCP stdio server for Claude Desktop
            logger.info("Local environment detected - starting MCP stdio server")
            from mcp.server.stdio import stdio_server
            
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream, 
                    write_stream, 
                    InitializationOptions(
                        server_name="amacoach",
                        server_version="0.1.0",
                        capabilities=ServerCapabilities(
                            tools=ToolsCapability(),
                            resources=ResourcesCapability()
                        )
                    )
                )
            
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        raise
    finally:
        logger.info("AmaCoach MCP Server shutting down...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())