"""
AmaCoach MCP Server Implementation.

This is the main MCP server that exposes the 6 required tools to Claude.ai:
1. list_exercises
2. create_exercise  
3. save_workout_plan
4. load_workout_plan
5. save_personal_record
6. load_personal_records

The server provides secure data storage and retrieval with user isolation.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability, ResourcesCapability
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl

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


def get_user_from_context(context) -> str:
    """
    Extract user ID from MCP context.
    In production, this would validate OAuth tokens and extract user identity.
    For development, we'll use a default user or extract from context.
    """
    # In production: validate Bearer token and extract user_id from JWT
    # For development: use default user or extract from request context
    if hasattr(context, 'user_id'):
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
            description="Store workout plans for users (enforces 3-plan maximum)",
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
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any], context) -> List[TextContent]:
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
    
    # Validate exercises exist
    for exercise_data in exercises_list:
        exercise = db.get_exercise_by_id(exercise_data["exercise_id"])
        if not exercise:
            raise ValueError(f"Exercise ID {exercise_data['exercise_id']} not found")
    
    plan = db.save_workout_plan(
        user_id=user_id,
        plan_name=plan_name,
        exercises_list=exercises_list,
        notes=notes
    )
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "message": f"Workout plan '{plan_name}' saved successfully",
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
        logger.info(f"Max active plans: {config.max_active_plans}")
        
        # Start HTTP server for Railway health checks
        await run_http_server()
        
        # Run the server using stdio transport (standard for MCP servers)
        from mcp.server.stdio import stdio_server
        
        logger.info("AmaCoach MCP Server is running")
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