# AmaCoach Task List

## Phase 1: Core MCP Server (Weeks 1-2)

### Database Setup
- [ ] **High** - Set up SQLite database with complete schema
  - Create User table with user_id, name, created_date, rotation_weeks, last_rotation_date, current_cycle_number
  - Create Exercise table with exercise_id, name, description, muscle_groups (JSON), equipment_needed (JSON), difficulty_level (1-5), instructions, created_date, created_by_user_id
  - Create WorkoutPlan table with plan_id, user_id, plan_name, cycle_number, is_active, created_date, notes, MAX 3 active plans constraint
  - Create PlannedExercise table with planned_exercise_id, plan_id, exercise_id, sets, reps, weight, duration, notes, order_in_plan
  - Create PersonalRecord table with record_id, user_id, exercise_name, record_type, value, unit, date_achieved, notes

### MCP Tools Implementation
- [ ] **High** - Implement list_exercises MCP tool
  - Accept optional filters: muscle_group, equipment, difficulty
  - Return exercises with metadata: name, muscle groups, equipment needed, difficulty
  
- [ ] **High** - Implement create_exercise MCP tool
  - Accept parameters: name, description, muscle_groups, equipment_needed, difficulty_level, instructions
  - Return confirmation of exercise creation
  - Allow Claude to expand exercise database based on user needs

- [ ] **High** - Implement save_workout_plan MCP tool
  - Accept parameters: user_id, plan_name, exercises_list, notes
  - Return confirmation and plan_id
  - Enforce 3-plan maximum per user constraint

- [ ] **High** - Implement load_workout_plan MCP tool
  - Accept parameters: user_id, plan_id (optional)
  - Return workout plan details including exercises and metadata
  - If plan_id omitted, return all active plans

- [ ] **High** - Implement save_personal_record MCP tool
  - Accept parameters: user_id, exercise_name, record_type (weight/reps/time/distance), value, date
  - Return confirmation of record save

- [ ] **High** - Implement load_personal_records MCP tool
  - Accept parameters: user_id, exercise_name (optional), record_type (optional)
  - Return list of personal records with dates and values

### Authentication & Security Implementation
- [ ] **High** - Implement OAuth 2.1 Standard authentication
  - Full OAuth 2.1 implementation for secure user authentication
  - Bearer Token Authorization with Authorization: Bearer <token> headers
  - Identity Provider Integration leveraging Claude.ai's authentication system
  - HTTPS enforcement for all authentication endpoints

- [ ] **High** - Implement User Identity Management
  - AuthInfo Object handling in MCP server
  - Automatic User Creation for first-time authenticated users
  - User ID Mapping from OAuth identity to internal user_id
  - Session Persistence throughout MCP connection lifecycle

- [ ] **High** - Implement Data Isolation Strategy
  - Query-Level Filtering with automatic WHERE user_id = {authenticated_user}
  - Tool-Level Security validation for every MCP tool
  - Cross-User Prevention ensuring no access to different users' data
  - Audit Trail logging all data access attempts with user identity

- [ ] **Medium** - Implement Security Requirements
  - Token Validation on every MCP tool request
  - Token Rotation support for automatic refresh and expiration handling
  - Proper 401 responses for authentication failures
  - Secure Storage following OAuth token security best practices

- [ ] **Medium** - Implement Security Measures
  - Input Sanitization to prevent injection attacks
  - Parameterized Queries for SQLite to prevent SQL injection
  - Rate Limiting per-user on MCP tool usage
  - Connection Security for all MCP communications

### Basic Testing
- [ ] **Medium** - Test basic CRUD operations for all data models
- [ ] **Medium** - Verify Claude.ai integration with all 6 MCP tools

## Phase 2: 3-Plan System (Week 3)

### 3-Plan Rotation Logic Implementation
- [ ] **High** - Implement 3-plan constraint enforcement
  - Exactly 3 active workout plans per user at any time
  - Weekly rotation system (Plan A Monday, Plan B Wednesday, Plan C Friday)
  - Cycle management after configurable weeks (default 6)
  - Automatic lifecycle with old plans deactivated when new cycle begins

- [ ] **High** - Implement rotation system logic
  - Users start with 3 plans in cycle 1
  - After rotation_weeks, allow Claude to create 3 new plans
  - Mark old plans as is_active = False
  - Increment cycle_number for new plans
  - Update last_rotation_date

- [ ] **High** - Implement save_workout_plan constraint checking
  - Check if user already has 3 active plans
  - Handle plan replacement or rejection based on parameters
  - Ensure load_workout_plan only returns active plans by default
  - Support rotation triggered by time-based logic or manual user request

### Testing & Validation
- [ ] **Medium** - Test 3-plan constraint logic thoroughly
- [ ] **Medium** - Test cycle management functionality
- [ ] **Medium** - Validate plan lifecycle from creation to deactivation

## Phase 3: Testing & Refinement (Week 4)

### Comprehensive Testing
- [ ] **High** - End-to-end testing with Claude.ai integration
  - Test initial setup workflow (talk to Claude, list exercises, create 3 plans)
  - Test weekly workout workflow (load plans, present rotation, save records)
  - Test equipment adaptation workflow (filter exercises, dynamic adaptation)
  - Test new exercise addition workflow (create_exercise integration)
  - Test plan rotation workflow (check rotation date, create new plans, deactivate old)

### Performance & Error Handling
- [ ] **Medium** - Performance optimization for all MCP tools
- [ ] **Medium** - Comprehensive error handling implementation
- [ ] **Low** - Documentation completion for setup and deployment

## Phase 4: Advanced Features (Future)

### Future Enhancements
- [ ] **Low** - Workout analytics implementation
- [ ] **Low** - Progress tracking visualization
- [ ] **Low** - Export/import capabilities
- [ ] **Low** - Multi-user support enhancements

## Railway Deployment Requirements

### Infrastructure Setup
- [ ] **High** - Configure Python 3.9+ runtime with Railway Python buildpack
- [ ] **High** - Set up SQLite with Railway volume mounting for persistence
- [ ] **High** - Configure production-ready environment variables
- [ ] **Medium** - Implement health check endpoint for Railway monitoring
- [ ] **Medium** - Set up automatic HTTPS and domain management through Railway

### Project Structure Implementation
- [ ] **High** - Create server.py (Main MCP server implementation)
- [ ] **High** - Create database.py (SQLite database operations)
- [ ] **High** - Create models.py (Data model definitions)
- [ ] **High** - Create config.py (Configuration settings)
- [ ] **Medium** - Create railway.json (Railway deployment configuration)
- [ ] **Medium** - Create Procfile (Process definition for Railway)
- [ ] **Medium** - Create requirements.txt (Python dependencies: mcp, sqlite3, json, datetime)
- [ ] **Medium** - Create .env.example (Environment variable template)
- [ ] **Medium** - Create healthcheck.py (Health check endpoint for Railway)

## Success Criteria Validation

### Technical Metrics
- [ ] **High** - Verify all 6 MCP tools respond correctly
- [ ] **High** - Ensure 3-plan constraint is never violated
- [ ] **High** - Confirm rotation system works automatically
- [ ] **High** - Validate database maintains data integrity

### User Experience Metrics
- [ ] **Medium** - Test users can get workout plans through Claude.ai conversation
- [ ] **Medium** - Verify personal records are accurately tracked
- [ ] **Medium** - Confirm equipment adaptation works seamlessly
- [ ] **Medium** - Validate plan rotation creates fresh, varied workouts

## Risk Mitigation Tasks

### Data Protection
- [ ] **Medium** - Implement SQLite database backup strategy
- [ ] **Medium** - Ensure transaction-based operations
- [ ] **Medium** - Add data validation on all inputs

### Integration Reliability
- [ ] **Medium** - Comprehensive MCP tool testing
- [ ] **Medium** - Create clear tool documentation
- [ ] **Low** - Implement fallback error messages

### User Experience Protection
- [ ] **Low** - Ensure simple, intuitive tool naming
- [ ] **Low** - Maintain consistent data format expectations
- [ ] **Low** - Implement clear error handling and user feedback