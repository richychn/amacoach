# AmaCoach Project Plan

## Overview

AmaCoach is a fitness coaching system that leverages Claude.ai's intelligence through a Model Context Protocol (MCP) server. Users interact directly with Claude.ai to receive personalized workout plans, track personal records, and adapt workouts to available equipment. The MCP server provides data storage and retrieval capabilities, while Claude handles all workout intelligence and user interaction.

## Core Architecture

### System Design
- **Frontend**: Direct interaction with Claude.ai (no separate UI)
- **Backend**: Python MCP server providing data tools to Claude
- **Database**: SQLite for local data persistence
- **Intelligence Layer**: Claude.ai handles workout adaptation, equipment substitution, and coaching

### Key Principle
The MCP server is purely a data layer. All workout logic, equipment adaptation, exercise explanations, and user coaching intelligence is handled by Claude.ai.

## Required MCP Tools

The MCP server must expose exactly these 6 tools to Claude:

### 1. `list_exercises`
- **Purpose**: Return available exercises for Claude to choose from
- **Parameters**: Optional filters (muscle_group, equipment, difficulty)
- **Returns**: List of exercises with metadata (name, muscle groups, equipment needed, difficulty)

### 2. `create_exercise`
- **Purpose**: Add new exercises to the database
- **Parameters**: name, description, muscle_groups, equipment_needed, difficulty_level, instructions
- **Returns**: Confirmation of exercise creation
- **Note**: Allows Claude to expand the exercise database based on user needs

### 3. `save_workout_plan`
- **Purpose**: Store workout plans for users
- **Parameters**: user_id, plan_name, exercises_list, notes
- **Returns**: Confirmation and plan_id
- **Constraint**: Enforces 3-plan maximum per user

### 4. `load_workout_plan`
- **Purpose**: Retrieve stored workout plans
- **Parameters**: user_id, plan_id (optional - if omitted, returns all active plans)
- **Returns**: Workout plan details including exercises and metadata

### 5. `save_personal_record`
- **Purpose**: Store user personal bests/records
- **Parameters**: user_id, exercise_name, record_type (weight, reps, time, distance), value, date
- **Returns**: Confirmation of record save

### 6. `load_personal_records`
- **Purpose**: Retrieve user personal records
- **Parameters**: user_id, exercise_name (optional), record_type (optional)
- **Returns**: List of personal records with dates and values

## User Authentication & Data Security

### Authentication Implementation
- **OAuth 2.1 Standard**: Full OAuth 2.1 implementation for secure user authentication
- **Bearer Token Authorization**: All MCP requests include `Authorization: Bearer <token>` headers
- **Identity Provider Integration**: Leverages Claude.ai's existing authentication system
- **HTTPS Enforcement**: All authentication endpoints served over HTTPS only

### User Identity Management
- **AuthInfo Object**: MCP server receives authenticated user details in `authInfo` parameter
- **Automatic User Creation**: First-time authenticated users automatically get database records
- **User ID Mapping**: Map OAuth identity to internal `user_id` for database operations
- **Session Persistence**: User identity maintained throughout MCP connection lifecycle

### Data Isolation Strategy
- **Query-Level Filtering**: All database queries automatically include `WHERE user_id = {authenticated_user}`
- **Tool-Level Security**: Every MCP tool validates user identity before data access
- **Cross-User Prevention**: No MCP tool can access data from different users
- **Audit Trail**: Log all data access attempts with user identity for security monitoring

### Implementation Requirements
- **Token Validation**: Verify OAuth tokens on every MCP tool request
- **Token Rotation**: Support automatic token refresh and expiration handling
- **Error Handling**: Proper 401 responses for authentication failures
- **Secure Storage**: OAuth tokens stored following security best practices

### Security Measures
- **Input Sanitization**: Validate all user inputs to prevent injection attacks
- **Parameterized Queries**: Use SQLite parameterized queries to prevent SQL injection
- **Rate Limiting**: Implement per-user rate limits on MCP tool usage
- **Connection Security**: Secure transport for all MCP communications

## Core Data Models

### User
```python
- user_id (primary key)
- name
- created_date
- rotation_weeks (default: 6)
- last_rotation_date
- current_cycle_number
```

### Exercise
```python
- exercise_id (primary key)
- name (unique)
- description
- muscle_groups (JSON array)
- equipment_needed (JSON array)
- difficulty_level (1-5)
- instructions (text)
- created_date
- created_by_user_id
```

### WorkoutPlan
```python
- plan_id (primary key)
- user_id (foreign key)
- plan_name
- cycle_number
- is_active (boolean)
- created_date
- notes
- Constraint: MAX 3 active plans per user
```

### PlannedExercise
```python
- planned_exercise_id (primary key)
- plan_id (foreign key)
- exercise_id (foreign key)
- sets
- reps
- weight (optional)
- duration (optional)
- notes
- order_in_plan
```

### PersonalRecord
```python
- record_id (primary key)
- user_id (foreign key)
- exercise_name
- record_type (weight/reps/time/distance)
- value
- unit
- date_achieved
- notes
```

## 3-Plan Rotation System

### Core Requirements
1. **Exactly 3 Plans**: Each user maintains exactly 3 active workout plans at any time
2. **Weekly Rotation**: Plans are designed for weekly rotation (Plan A Monday, Plan B Wednesday, Plan C Friday)
3. **Cycle Management**: After X weeks (configurable per user, default 6), user rotates to 3 completely new plans
4. **Automatic Lifecycle**: Old plans are automatically deactivated when new cycle begins

### Rotation Logic
- Users start with 3 plans in cycle 1
- After `rotation_weeks`, Claude can create 3 new plans
- Old plans are marked `is_active = False`
- New plans get incremented `cycle_number`
- `last_rotation_date` is updated

### Implementation Rules
- `save_workout_plan` checks if user already has 3 active plans
- If at limit, either replace existing plan or reject (based on parameters)
- `load_workout_plan` only returns active plans by default
- Rotation triggered by time-based logic or manual user request

## Technology Stack

### Backend
- **Language**: Python 3.9+
- **MCP Framework**: Official Python MCP SDK
- **Database**: SQLite (single file, local storage)
- **Dependencies**: mcp, sqlite3, json, datetime
- **Deployment**: Railway cloud platform

### Railway Deployment Requirements
- **Runtime**: Python 3.9+ with Railway Python buildpack
- **Database**: SQLite with Railway volume mounting for persistence
- **Environment**: Production-ready configuration with environment variables
- **Networking**: Railway provides automatic HTTPS and domain management
- **Health Checks**: Built-in health monitoring for MCP server availability

### Project Structure
```
amacoach/
├── server.py           # Main MCP server implementation
├── database.py         # SQLite database operations
├── models.py          # Data model definitions
├── config.py          # Configuration settings
├── railway.json       # Railway deployment configuration
├── Procfile           # Process definition for Railway
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
├── healthcheck.py     # Health check endpoint for Railway
├── amacoach.db        # SQLite database file (volume-mounted)
└── README.md          # Setup and deployment instructions
```

## User Workflow

### Initial Setup
1. User talks to Claude.ai about fitness goals
2. Claude uses `list_exercises` to see available exercises
3. Claude creates 3 initial workout plans using `save_workout_plan`
4. Plans are saved with cycle_number = 1

### Weekly Workouts
1. User asks Claude "What's my workout today?"
2. Claude uses `load_workout_plan` to get active plans
3. Claude presents appropriate plan based on user's rotation
4. User logs results, Claude uses `save_personal_record` to track progress

### Equipment Adaptation
1. User says "I only have dumbbells today"
2. Claude uses `list_exercises` with equipment filter
3. Claude adapts the planned workout using available exercises
4. No database changes needed - Claude handles adaptation dynamically

### Adding New Exercises
1. User mentions an exercise not in database
2. Claude uses `create_exercise` to add it
3. Exercise becomes available for future workout plans
4. Claude can immediately incorporate into workouts

### Plan Rotation
1. After X weeks, user asks for new plans
2. Claude checks rotation date and cycle number
3. Claude creates 3 new plans with incremented cycle_number
4. Old plans automatically become inactive

## Development Phases

### Phase 1: Core MCP Server (Weeks 1-2)
- Implement all 6 MCP tools
- Set up SQLite database with schema
- Test basic CRUD operations
- Verify Claude.ai integration

### Phase 2: 3-Plan System (Week 3)
- Implement 3-plan constraint logic
- Add cycle management
- Test rotation system
- Validate plan lifecycle

### Phase 3: Testing & Refinement (Week 4)
- End-to-end testing with Claude.ai
- Performance optimization
- Error handling
- Documentation completion

### Phase 4: Advanced Features (Future)
- Workout analytics
- Progress tracking visualization
- Export/import capabilities
- Multi-user support enhancements

## Success Metrics

### Technical Metrics
- All 6 MCP tools respond correctly
- 3-plan constraint never violated
- Rotation system works automatically
- Database maintains data integrity

### User Experience Metrics
- Users can get workout plans through Claude.ai conversation
- Personal records are accurately tracked
- Equipment adaptation works seamlessly
- Plan rotation creates fresh, varied workouts

## Risk Mitigation

### Data Loss Prevention
- SQLite database backup strategy
- Transaction-based operations
- Data validation on all inputs

### Claude.ai Integration Issues
- Comprehensive MCP tool testing
- Clear tool documentation
- Fallback error messages

### User Experience Risks
- Simple, intuitive tool naming
- Consistent data format expectations
- Clear error handling and user feedback

## Conclusion

AmaCoach leverages the power of Claude.ai's intelligence while providing a robust data foundation through its MCP server. The unique 3-plan rotation system ensures users always have fresh, varied workouts while maintaining progression tracking. By keeping the architecture simple and focused, the system can deliver powerful fitness coaching capabilities through natural conversation with Claude.ai.