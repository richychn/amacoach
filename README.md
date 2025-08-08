# AmaCoach MCP Server

A fitness coaching system that provides data storage and retrieval capabilities through a Model Context Protocol (MCP) server. Works with Claude.ai to deliver personalized workout plans, track personal records, and manage exercise databases.

## Project Structure

```
amacoach/
├── server.py           # Main MCP server implementation
├── database.py         # SQLite database operations  
├── models.py          # Data model definitions
├── config.py          # Configuration settings
├── healthcheck.py     # Health check endpoint
├── test_database.py   # Database schema verification tests
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
└── README.md          # This file
```

## Features Implemented

### Core Database Schema (5 Tables)

1. **Users** - User profiles with rotation settings
2. **Exercises** - Exercise library with metadata
3. **WorkoutPlans** - User workout plans with 3-plan constraint
4. **PlannedExercises** - Exercises within workout plans
5. **PersonalRecords** - User personal bests/records

### MCP Tools (6 Tools)

1. `list_exercises` - Return available exercises with optional filters
2. `create_exercise` - Add new exercises to the database
3. `save_workout_plan` - Store workout plans (max 3 active per user)
4. `load_workout_plan` - Retrieve workout plans and exercises
5. `save_personal_record` - Store personal records
6. `load_personal_records` - Retrieve personal records with filters

### Key Features

- **3-Plan Rotation System** - Enforced at database level with triggers
- **User Data Isolation** - All queries filtered by user_id
- **Parameterized Queries** - SQL injection protection
- **Data Validation** - Input sanitization and constraint checking
- **Plan Lifecycle Management** - Automatic rotation and deactivation
- **Comprehensive Error Handling** - Proper exception management

## Setup & Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Verify Installation

```bash
# Run database schema tests
python3 test_database.py

# Run health check
python3 healthcheck.py
```

### 4. Start MCP Server

```bash
python3 server.py
```

## Database Schema Verification

The database schema has been thoroughly tested and verified:

✅ **Schema Creation** - All 5 tables created with proper relationships  
✅ **3-Plan Constraint** - Database-level enforcement prevents > 3 active plans  
✅ **Foreign Key Constraints** - Referential integrity maintained  
✅ **Data Validation** - Input validation for difficulty levels and record types  
✅ **Plan Rotation System** - Cycle management with automatic deactivation  
✅ **User Data Isolation** - All operations scoped to authenticated user  
✅ **Personal Records** - Full CRUD operations with filtering  
✅ **Exercise Management** - Creation and filtering by multiple criteria  

## Security Implementation

- **Parameterized Queries** - All SQL uses parameter binding
- **User Data Isolation** - Query-level filtering by user_id
- **Input Validation** - Sanitization of all user inputs
- **Error Handling** - No sensitive information leaked in errors
- **OAuth 2.1 Ready** - Framework for authentication integration

## Health Monitoring

The `healthcheck.py` script provides comprehensive health monitoring:

- Database connectivity verification
- Schema validation (all tables present)
- Configuration validation
- Basic operation testing
- Environment detection

## Configuration Options

Key configuration parameters (see `.env.example`):

- `MAX_ACTIVE_PLANS=3` - Maximum active workout plans per user
- `DEFAULT_ROTATION_WEEKS=6` - Default rotation cycle length
- `DATABASE_PATH=amacoach.db` - SQLite database file path
- `DEBUG_MODE=false` - Development vs production mode

## Testing

Run the comprehensive test suite:

```bash
python3 test_database.py
```

This verifies:
- Database schema creation and constraints
- 3-plan constraint enforcement
- Data validation and error handling
- Plan rotation system
- Personal records management
- Exercise filtering and creation

## Architecture Notes

This implementation follows the project specifications exactly:

1. **Pure Data Layer** - No workout intelligence, only data storage
2. **MCP Integration** - Designed for Claude.ai interaction
3. **SQLite Foundation** - Single-file database for simplicity
4. **3-Plan System** - Core constraint enforced at database level
5. **User-Centric** - All data operations scoped to individual users

The MCP server provides the data foundation while Claude.ai handles all workout intelligence, equipment adaptation, and user coaching.

## Database Foundation Status

🎉 **COMPLETE**: The complete SQLite database foundation has been implemented and verified according to project specifications.

All requirements from the task assignment have been fulfilled:
- ✅ Complete SQLite schema with all 5 tables
- ✅ Proper relationships and foreign key constraints  
- ✅ 3-plan constraint enforced at database level
- ✅ Python file architecture created (server.py, database.py, models.py, config.py)
- ✅ Security foundation with parameterized queries
- ✅ User data isolation built into database layer
- ✅ Plan rotation system operational
- ✅ Comprehensive testing and verification