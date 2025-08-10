# AmaCoach Task List - Updated Project Status

## 📋 Project Overview
AmaCoach is a functional MCP (Model Context Protocol) server that enables Claude.ai to provide fitness coaching through workout plans, personal record tracking, and equipment adaptation. The core system is **COMPLETE** and successfully deployed.

## ✅ COMPLETED - Phase 1: Core MCP Server (Weeks 1-2)

### Database Setup - ✅ COMPLETE
- ✅ **DONE** - SQLite database with complete schema
  - ✅ User table: user_id, name, created_date, rotation_weeks, last_rotation_date, current_cycle_number
  - ✅ Exercise table: exercise_id, name, description, muscle_groups (JSON), equipment_needed (JSON), difficulty_level (1-5), instructions, created_date, created_by_user_id
  - ✅ WorkoutPlan table: plan_id, user_id, plan_name, cycle_number, is_active, created_date, notes, MAX 3 active plans constraint
  - ✅ PlannedExercise table: planned_exercise_id, plan_id, exercise_id, sets, reps, weight, duration, notes, order_in_plan
  - ✅ PersonalRecord table: record_id, user_id, exercise_name, record_type, value, unit, date_achieved, notes
  - ✅ Database triggers enforce 3-plan constraint automatically
  - ✅ Foreign key relationships with proper referential integrity
  - ✅ Performance indexes on commonly queried columns

### MCP Tools Implementation - ✅ COMPLETE
- ✅ **DONE** - `list_exercises` MCP tool
  - Accepts optional filters: muscle_group, equipment, difficulty
  - Returns exercises with complete metadata
  
- ✅ **DONE** - `create_exercise` MCP tool
  - Validates all parameters including difficulty_level (1-5)
  - Supports user-created exercises with proper attribution
  
- ✅ **DONE** - `save_workout_plan` MCP tool
  - Enforces 3-plan maximum constraint at database level
  - Validates exercise_ids exist before saving
  - Returns complete plan object with plan_id
  
- ✅ **DONE** - `load_workout_plan` MCP tool
  - Returns single plan (with exercises) or all active plans
  - Includes complete exercise metadata for each planned exercise
  
- ✅ **DONE** - `save_personal_record` MCP tool
  - Supports all record types: weight, reps, time, distance
  - Validates record_type against allowed values
  - Handles optional date (defaults to current time)
  
- ✅ **DONE** - `load_personal_records` MCP tool
  - Supports filtering by exercise_name and/or record_type
  - Returns chronologically sorted records
  
- ✅ **DONE** - `generate_workout_guidance` MCP tool
  - Provides structured guidance for creating complementary 3-plan sets
  - Returns available exercises filtered by equipment and muscle focus
  - Instructs Claude to use only database exercises across all 3 plans
  - Includes cycle information for rotation decisions
  - Offers multiple split recommendations (Push/Pull/Legs, Upper/Lower/Full, etc.)

### Authentication & Security Implementation - ✅ FOUNDATION COMPLETE
- ✅ **DONE** - OAuth 2.1 framework implemented
  - Bearer token validation structure in place
  - Environment-based configuration for production vs development
  - User identity extraction from MCP context
  - Automatic user creation for new authenticated users
  
- ✅ **DONE** - Data Isolation implemented
  - All database queries filter by authenticated user_id
  - Cross-user data access prevention
  - Parameterized queries prevent SQL injection
  - Input validation on all user inputs

### Basic Testing - ✅ COMPLETE
- ✅ **DONE** - All CRUD operations tested and verified
- ✅ **DONE** - All 6 MCP tools tested with comprehensive test suite
- ✅ **DONE** - Database constraints and triggers verified
- ✅ **DONE** - Type annotations fixed for VSCode/Pylance compatibility

## ✅ COMPLETED - Phase 2: 3-Plan System (Week 3)

### 3-Plan Rotation Logic Implementation - ✅ COMPLETE
- ✅ **COMPLETE** - 3-plan complementary system
  - ✅ **DONE** - Removed database-level trigger that prevented >3 active plans  
  - ✅ **DONE** - Users can now have unlimited active workout plans
  - ✅ **DONE** - save_workout_plan supports create_as_set parameter for Claude 3-plan sets
  - ✅ **DONE** - When Claude creates 3-plan sets, first plan deactivates previous plans
  - ✅ **DONE** - Automatic plan lifecycle management implemented
  
- ✅ **DONE** - Rotation system logic
  - Configurable rotation_weeks (default: 6)
  - Automatic cycle_number incrementing
  - Plan deactivation when creating new cycle
  - last_rotation_date tracking

### Testing & Validation - ✅ COMPLETE
- ✅ **DONE** - 3-plan constraint thoroughly tested
- ✅ **DONE** - Cycle management validated
- ✅ **DONE** - Complete plan lifecycle verified

## ✅ COMPLETED - Phase 3: Railway Deployment

### Railway Infrastructure - ✅ COMPLETE
- ✅ **DONE** - Python 3.10+ runtime with UV package manager
- ✅ **DONE** - Railway deployment configuration
  - `railway.json` with health checks and volume mounting
  - `Procfile` with UV startup command
  - `nixpacks.toml` for Python 3.10 specification
  
- ✅ **DONE** - Environment management
  - Production vs development environment detection
  - Railway-specific configuration handling
  - HTTP health server for Railway monitoring
  - MCP stdio server for Claude.ai integration

### Project Structure - ✅ COMPLETE
- ✅ **DONE** - `server.py` - Complete MCP server with dual-mode operation
- ✅ **DONE** - `database.py` - Full SQLite operations with security measures
- ✅ **DONE** - `models.py` - All data models with validation
- ✅ **DONE** - `config.py` - Comprehensive configuration management
- ✅ **DONE** - `healthcheck.py` - Railway health monitoring
- ✅ **DONE** - `pyproject.toml` - UV dependency management
- ✅ **DONE** - `.env.example` - Production environment template

### Deployment Status - ✅ COMPLETE
- ✅ **DONE** - Successfully deployed to Railway
- ✅ **DONE** - Health checks passing
- ✅ **DONE** - Database persistence configured
- ✅ **DONE** - HTTP endpoints responding correctly

## 🔄 IN PROGRESS - Claude.ai Integration

### Local MCP Connection - 🔄 TESTING
- ✅ **DONE** - Created `claude_desktop_config.json` at `~/Library/Application Support/Claude/`
- ✅ **DONE** - Configured UV command execution with proper working directory
- 🔄 **TESTING** - User testing Claude Desktop app connection
  - Download Claude Desktop app from https://claude.ai/download
  - Restart Claude Desktop after config file creation
  - Test MCP tools: "List available exercises in my AmaCoach database"

## ✅ COMPLETED UPDATES (August 2025)

### MCP-over-HTTP + OAuth 2.1 Integration - ✅ COMPLETE
- ✅ **DONE** - Replaced FastAPI with MCP-over-HTTP protocol
  - Removed all FastAPI endpoints (/tools, /call-tool)
  - Implemented proper MCP protocol over HTTP using StreamableHTTPServerTransport
  - Added ASGI-compliant endpoint for Claude.ai Remote MCP compatibility
  
- ✅ **DONE** - Added full OAuth 2.1 authentication
  - Implemented /oauth/authorize endpoint for authorization flow
  - Implemented /oauth/token endpoint for token exchange
  - Added JWT token system with access/refresh tokens
  - Proper client credentials validation
  - Secure token signing and verification
  
- ✅ **DONE** - Fixed all type safety issues
  - Corrected JWT exception imports (ExpiredSignatureError, JWTError)
  - Fixed timedelta type annotations
  - Resolved ASGI parameter handling
  - All Pylance errors resolved

### HTTP API Integration - ⚠️ DEPRECATED
- ✅ **DONE** - Switched from UV to pyenv + requirements.txt
  - Removed UV-related files (uv.lock, pyproject.toml)
  - Installed pyenv and Python 3.10.18
  - Created new virtual environment with pip
  - Generated requirements.txt with all dependencies
  
- ✅ **DONE** - Added dual-mode HTTP API support
  - Implemented FastAPI alongside existing MCP server
  - Added bearer token authentication via MCP_AUTH_TOKEN
  - Created HTTP endpoints: /tools, /call-tool, /health
  - Fixed type errors and response formatting
  - All 7 MCP tools now accessible via HTTP API

### Deployment Modes - ✅ UPDATED
- ✅ **MCP Mode (Claude Desktop)**: `python server.py` - Local stdio MCP
- ✅ **MCP-over-HTTP Mode (Claude.ai Remote MCP)**: `HTTP_MODE=true python server.py`
- ✅ **Railway Mode**: Automatic MCP-over-HTTP based on PORT environment variable
- ✅ **OAuth 2.1 Authentication**: Full OAuth flow with JWT tokens

### Testing Results - ✅ VERIFIED
- ✅ **MCP-over-HTTP Protocol**: Proper MCP protocol implementation
- ✅ **OAuth 2.1 Flow**: Complete authorization and token endpoints
- ✅ **JWT Authentication**: Secure token validation working
- ✅ **Type Safety**: All Pylance errors resolved
- ✅ **ASGI Integration**: Proper ASGI parameter handling

## 📝 REMAINING TASKS

### Priority: HIGH - Claude.ai Remote MCP Integration
- [ ] **HIGH** - Deploy to Railway with OAuth 2.1 configuration
  - Set OAuth environment variables (CLIENT_ID, CLIENT_SECRET, JWT_SECRET_KEY)
  - Test MCP-over-HTTP endpoints on Railway deployment
  - Verify OAuth authorization flow works in cloud environment

- [ ] **HIGH** - Configure Claude.ai Remote MCP connection
  - Add Railway server URL to Claude.ai MCP settings
  - Configure OAuth 2.1 credentials in Claude.ai
  - Test all 7 MCP tools through Claude.ai web interface
  - Validate fitness coaching workflow end-to-end

### Priority: MEDIUM - Documentation & Repository
- [ ] **MEDIUM** - Initialize git repository and push to GitHub
  - Create initial commit with all current files
  - Create GitHub repository named "AmaCoach"
  - Push codebase for version control
  
- [ ] **MEDIUM** - Create production environment documentation
  - Document Railway environment variables needed
  - Create setup instructions for new deployments
  - Document MCP configuration for Claude Desktop

### Priority: LOW - Future Enhancements
- [ ] **LOW** - Railway MCP server support (WebSocket/HTTP transport)
- [ ] **LOW** - Workout analytics and progress visualization
- [ ] **LOW** - Data export/import capabilities
- [ ] **LOW** - Advanced authentication (production OAuth setup)

## 🎯 Current Status Summary

### What's Working ✅
- **Complete MCP server** with all 7 required tools (including generate_workout_guidance)
- **MCP-over-HTTP protocol** with proper StreamableHTTPServerTransport integration
- **Full OAuth 2.1 authentication** with authorization and token endpoints
- **Railway deployment** with health checks and persistence
- **3-plan rotation system** updated for complementary plans (no hard constraints)
- **JWT token system** with secure signing and validation
- **Comprehensive data models** with validation and security
- **Type-safe codebase** with all Pylance errors resolved
- **ASGI-compliant endpoints** for proper MCP transport handling

### Current Target: Claude.ai Remote MCP (Claude Mobile) 🎯
- **MCP-over-HTTP Mode**: Ready for Claude.ai Remote MCP integration
- **OAuth 2.1 Flow**: Complete authorization endpoints implemented
- **Railway Deployment**: Configured for cloud-based MCP-over-HTTP access
- **All 7 MCP Tools**: Accessible via Remote MCP protocol

### What Needs Testing 🔄
- **Railway OAuth deployment** - Set environment variables and deploy
- **Claude.ai Remote MCP setup** - Configure OAuth credentials
- **End-to-end fitness coaching** - Test workout planning through Claude.ai web/mobile

### Architecture Overview 🏗️
```
DUAL-MODE ARCHITECTURE:

Mode 1: Claude Desktop (MCP)
Claude Desktop App (MCP Client)
    ↓ stdio transport  
Local MCP Server (server.py)
    ↓ SQLite operations
AmaCoach Database (amacoach.db)

Mode 2: Claude.ai Remote MCP
Claude.ai Remote MCP
    ↓ MCP-over-HTTP + OAuth 2.1
MCP Server (server.py HTTP_MODE=true)
    ↓ SQLite operations
AmaCoach Database (amacoach.db)

Mode 3: Railway Deployment
Railway Cloud Platform
    ↓ MCP-over-HTTP + OAuth 2.1
Production MCP Server (PORT env var)
    ↓ SQLite operations with volume persistence
Production Database
```

## 🚀 Next Steps for New Claude Code Session

### Immediate Actions Available
1. **Claude.ai Remote MCP Integration** - User can add server with OAuth 2.1 setup
2. **Railway MCP Deployment** - Set OAuth environment variables and deploy
3. **OAuth Setup** - Generate secure client credentials and JWT secrets

### Optional (If User Wants Claude Desktop Later)
4. **Local MCP Mode** - Can re-enable local Claude Desktop connection if needed
5. **Plan Approval Workflow** - Address any UX issues in local mode

### Advanced Features
6. **JWT Authentication** - Upgrade from bearer tokens to JWT with user claims  
7. **Rate Limiting** - Add per-user/per-app request limits
8. **Monitoring** - Add logging and metrics for production use

## 📚 Key Technical Details for Context

### Technology Stack
- **Python 3.10+** with UV package manager
- **SQLite** database with triggers and constraints
- **MCP Protocol** for Claude.ai integration
- **Railway** cloud deployment platform
- **aiohttp** for health check endpoints

### File Organization
- `server.py` - **UPDATED** - Main application with dual-mode operation (MCP + HTTP API)
- `database.py` - Data access layer with security (3-plan constraints removed)
- `models.py` - Data structures and validation
- `config.py` - Environment and configuration management
- `requirements.txt` - **NEW** - pip dependency management (replaces uv)
- `.venv/` - **NEW** - pyenv-based virtual environment
- MCP configuration at `~/Library/Application Support/Claude/claude_desktop_config.json`

### Key Environment Variables
- `HTTP_MODE=true` - Enable MCP-over-HTTP mode for Claude.ai Remote MCP
- `OAUTH_CLIENT_ID=amacoach-client` - OAuth client identifier
- `OAUTH_CLIENT_SECRET=secret` - OAuth client secret
- `JWT_SECRET_KEY=secret` - JWT token signing key
- `PORT=8000` - Railway auto-detects and enables MCP-over-HTTP mode
- `RAILWAY_ENVIRONMENT` - Auto-detected Railway deployment

### Key Features Implemented
- **User data isolation** - Each user only sees their own data
- **3-plan constraint** - Enforced at database level with triggers
- **Exercise metadata** - Muscle groups, equipment, difficulty levels
- **Personal record tracking** - Multiple record types with history
- **Equipment adaptation** - Filter exercises by available equipment
- **Cycle management** - Automatic plan rotation after configurable weeks

The core system is complete and functional. Focus should be on testing, documentation, and user experience refinement.