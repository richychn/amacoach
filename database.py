"""
SQLite database operations for AmaCoach MCP server.

This module handles all database initialization, schema creation, and CRUD operations
with proper security measures including parameterized queries and user data isolation.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Iterator
from contextlib import contextmanager

from models import (
    User, Exercise, WorkoutPlan, PlannedExercise, PersonalRecord,
    serialize_json_field, deserialize_json_field,
    validate_difficulty_level, validate_record_type
)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


class UserPermissionError(Exception):
    """Custom exception for user permission violations."""
    pass


class Database:
    """SQLite database manager with security and constraint enforcement."""
    
    def __init__(self, db_path: str = "amacoach.db"):
        """Initialize database connection and ensure schema exists."""
        self.db_path = db_path
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with foreign key constraints enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_cursor(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for database transactions."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initialize database schema with all tables and constraints."""
        with self.get_cursor() as cursor:
            # Create User table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    rotation_weeks INTEGER DEFAULT 6,
                    last_rotation_date TEXT,
                    current_cycle_number INTEGER DEFAULT 1
                )
            """)

            # Create Exercise table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    muscle_groups TEXT NOT NULL,  -- JSON array
                    equipment_needed TEXT NOT NULL,  -- JSON array
                    difficulty_level INTEGER NOT NULL CHECK (difficulty_level >= 1 AND difficulty_level <= 5),
                    instructions TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    created_by_user_id TEXT NOT NULL,
                    FOREIGN KEY (created_by_user_id) REFERENCES users (user_id)
                )
            """)

            # Create WorkoutPlan table with 3-plan constraint
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_plans (
                    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan_name TEXT NOT NULL,
                    cycle_number INTEGER NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_date TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, plan_name, cycle_number)
                )
            """)

            # Create trigger to enforce max 3 active plans per user
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS enforce_max_active_plans
                BEFORE INSERT ON workout_plans
                WHEN NEW.is_active = 1
                BEGIN
                    SELECT CASE
                        WHEN (SELECT COUNT(*) FROM workout_plans 
                              WHERE user_id = NEW.user_id AND is_active = 1) >= 3
                        THEN RAISE(ABORT, 'User cannot have more than 3 active workout plans')
                    END;
                END
            """)

            # Create PlannedExercise table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS planned_exercises (
                    planned_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
                    exercise_id INTEGER NOT NULL,
                    sets INTEGER NOT NULL,
                    reps INTEGER NOT NULL,
                    weight REAL,
                    duration INTEGER,  -- in seconds
                    notes TEXT,
                    order_in_plan INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (plan_id) REFERENCES workout_plans (plan_id) ON DELETE CASCADE,
                    FOREIGN KEY (exercise_id) REFERENCES exercises (exercise_id),
                    UNIQUE(plan_id, order_in_plan)
                )
            """)

            # Create PersonalRecord table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS personal_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    exercise_name TEXT NOT NULL,
                    record_type TEXT NOT NULL CHECK (record_type IN ('weight', 'reps', 'time', 'distance')),
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    date_achieved TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercises_muscle_groups ON exercises (muscle_groups)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_workout_plans_user_active ON workout_plans (user_id, is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_planned_exercises_plan ON planned_exercises (plan_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personal_records_user ON personal_records (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personal_records_exercise ON personal_records (user_id, exercise_name)")

    def _validate_user_access(self, cursor, user_id: str, table: str, record_user_id: Optional[str] = None) -> None:
        """Validate user can only access their own data."""
        if record_user_id and record_user_id != user_id:
            raise UserPermissionError(f"User {user_id} cannot access data belonging to {record_user_id}")

    # User operations
    def create_user(self, user_id: str, name: str) -> User:
        """Create a new user if they don't exist."""
        with self.get_cursor() as cursor:
            # Check if user already exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                # User exists, return existing user
                existing_user = self.get_user(user_id)
                if existing_user is None:
                    raise DatabaseError(f"User {user_id} exists in database but could not be retrieved")
                return existing_user

            # Create new user
            created_date = datetime.now()
            cursor.execute("""
                INSERT INTO users (user_id, name, created_date, rotation_weeks, current_cycle_number)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, name, created_date.isoformat(), 6, 1))

            return User(
                user_id=user_id,
                name=name,
                created_date=created_date,
                rotation_weeks=6,
                current_cycle_number=1
            )

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by user_id."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None

            return User(
                user_id=row['user_id'],
                name=row['name'],
                created_date=datetime.fromisoformat(row['created_date']),
                rotation_weeks=row['rotation_weeks'],
                last_rotation_date=datetime.fromisoformat(row['last_rotation_date']) if row['last_rotation_date'] else None,
                current_cycle_number=row['current_cycle_number']
            )

    def update_user_rotation(self, user_id: str) -> None:
        """Update user's rotation date and increment cycle number."""
        with self.get_cursor() as cursor:
            now = datetime.now()
            cursor.execute("""
                UPDATE users 
                SET last_rotation_date = ?, current_cycle_number = current_cycle_number + 1
                WHERE user_id = ?
            """, (now.isoformat(), user_id))

    # Exercise operations
    def create_exercise(self, name: str, description: str, muscle_groups: List[str], 
                       equipment_needed: List[str], difficulty_level: int, 
                       instructions: str, created_by_user_id: str) -> Exercise:
        """Create a new exercise."""
        if not validate_difficulty_level(difficulty_level):
            raise ValueError("Difficulty level must be between 1 and 5")

        with self.get_cursor() as cursor:
            created_date = datetime.now()
            cursor.execute("""
                INSERT INTO exercises (name, description, muscle_groups, equipment_needed, 
                                     difficulty_level, instructions, created_date, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, description, 
                serialize_json_field(muscle_groups),
                serialize_json_field(equipment_needed),
                difficulty_level, instructions, created_date.isoformat(), created_by_user_id
            ))

            exercise_id = cursor.lastrowid
            if exercise_id is None:
                raise DatabaseError("Failed to create exercise: no row ID returned")
            return Exercise(
                exercise_id=exercise_id,
                name=name,
                description=description,
                muscle_groups=muscle_groups,
                equipment_needed=equipment_needed,
                difficulty_level=difficulty_level,
                instructions=instructions,
                created_date=created_date,
                created_by_user_id=created_by_user_id
            )

    def list_exercises(self, muscle_group: Optional[str] = None, 
                      equipment: Optional[str] = None, 
                      difficulty: Optional[int] = None) -> List[Exercise]:
        """List exercises with optional filters."""
        with self.get_cursor() as cursor:
            query = "SELECT * FROM exercises"
            params = []
            conditions = []

            if muscle_group:
                conditions.append("muscle_groups LIKE ?")
                params.append(f'%"{muscle_group}"%')

            if equipment:
                conditions.append("equipment_needed LIKE ?")
                params.append(f'%"{equipment}"%')

            if difficulty:
                conditions.append("difficulty_level = ?")
                params.append(difficulty)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY name"

            cursor.execute(query, params)
            exercises = []
            for row in cursor.fetchall():
                # Deserialize JSON fields with type assertion for lists
                muscle_groups_data = deserialize_json_field(row['muscle_groups'])
                equipment_data = deserialize_json_field(row['equipment_needed'])
                
                # Ensure they're lists (fallback to empty list if not)
                muscle_groups = muscle_groups_data if isinstance(muscle_groups_data, list) else []
                equipment_needed = equipment_data if isinstance(equipment_data, list) else []
                
                exercises.append(Exercise(
                    exercise_id=row['exercise_id'],
                    name=row['name'],
                    description=row['description'],
                    muscle_groups=muscle_groups,
                    equipment_needed=equipment_needed,
                    difficulty_level=row['difficulty_level'],
                    instructions=row['instructions'],
                    created_date=datetime.fromisoformat(row['created_date']),
                    created_by_user_id=row['created_by_user_id']
                ))
            return exercises

    def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        """Get exercise by ID."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM exercises WHERE exercise_id = ?", (exercise_id,))
            row = cursor.fetchone()
            if not row:
                return None

            # Deserialize JSON fields with type assertion for lists
            muscle_groups_data = deserialize_json_field(row['muscle_groups'])
            equipment_data = deserialize_json_field(row['equipment_needed'])
            
            # Ensure they're lists (fallback to empty list if not)
            muscle_groups = muscle_groups_data if isinstance(muscle_groups_data, list) else []
            equipment_needed = equipment_data if isinstance(equipment_data, list) else []
            
            return Exercise(
                exercise_id=row['exercise_id'],
                name=row['name'],
                description=row['description'],
                muscle_groups=muscle_groups,
                equipment_needed=equipment_needed,
                difficulty_level=row['difficulty_level'],
                instructions=row['instructions'],
                created_date=datetime.fromisoformat(row['created_date']),
                created_by_user_id=row['created_by_user_id']
            )

    # Workout Plan operations
    def save_workout_plan(self, user_id: str, plan_name: str, 
                         exercises_list: List[Dict], notes: Optional[str] = None) -> WorkoutPlan:
        """Save workout plan with exercises, enforcing 3-plan constraint."""
        with self.get_cursor() as cursor:
            # Get user's current cycle number
            user = self.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            created_date = datetime.now()
            
            try:
                # Insert workout plan (trigger will enforce 3-plan constraint)
                cursor.execute("""
                    INSERT INTO workout_plans (user_id, plan_name, cycle_number, is_active, created_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, plan_name, user.current_cycle_number, True, created_date.isoformat(), notes))

                plan_id = cursor.lastrowid
                if plan_id is None:
                    raise DatabaseError("Failed to create workout plan: no row ID returned")

                # Insert planned exercises
                for order, exercise_data in enumerate(exercises_list, 1):
                    cursor.execute("""
                        INSERT INTO planned_exercises (plan_id, exercise_id, sets, reps, weight, duration, notes, order_in_plan)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        plan_id, exercise_data['exercise_id'], exercise_data['sets'], 
                        exercise_data['reps'], exercise_data.get('weight'), 
                        exercise_data.get('duration'), exercise_data.get('notes'), order
                    ))

                return WorkoutPlan(
                    plan_id=plan_id,
                    user_id=user_id,
                    plan_name=plan_name,
                    cycle_number=user.current_cycle_number,
                    is_active=True,
                    created_date=created_date,
                    notes=notes
                )

            except sqlite3.IntegrityError as e:
                if "cannot have more than 3 active workout plans" in str(e):
                    raise ValueError("User already has 3 active workout plans. Cannot create more.")
                raise DatabaseError(f"Failed to save workout plan: {str(e)}")

    def load_workout_plan(self, user_id: str, plan_id: Optional[int] = None) -> Union[Dict[str, Any], List[WorkoutPlan], None]:
        """Load workout plan(s) for user. Returns single plan if plan_id given, else all active plans."""
        with self.get_cursor() as cursor:
            if plan_id:
                # Load specific plan
                cursor.execute("""
                    SELECT * FROM workout_plans 
                    WHERE plan_id = ? AND user_id = ?
                """, (plan_id, user_id))
                
                row = cursor.fetchone()
                if not row:
                    return None

                # Load exercises for the plan
                cursor.execute("""
                    SELECT pe.*, e.name, e.description, e.muscle_groups, e.equipment_needed, e.difficulty_level
                    FROM planned_exercises pe
                    JOIN exercises e ON pe.exercise_id = e.exercise_id
                    WHERE pe.plan_id = ?
                    ORDER BY pe.order_in_plan
                """, (plan_id,))
                
                exercises = []
                for ex_row in cursor.fetchall():
                    exercises.append({
                        'planned_exercise_id': ex_row['planned_exercise_id'],
                        'exercise_id': ex_row['exercise_id'],
                        'name': ex_row['name'],
                        'description': ex_row['description'],
                        'muscle_groups': deserialize_json_field(ex_row['muscle_groups']),
                        'equipment_needed': deserialize_json_field(ex_row['equipment_needed']),
                        'difficulty_level': ex_row['difficulty_level'],
                        'sets': ex_row['sets'],
                        'reps': ex_row['reps'],
                        'weight': ex_row['weight'],
                        'duration': ex_row['duration'],
                        'notes': ex_row['notes'],
                        'order_in_plan': ex_row['order_in_plan']
                    })

                plan = WorkoutPlan(
                    plan_id=row['plan_id'],
                    user_id=row['user_id'],
                    plan_name=row['plan_name'],
                    cycle_number=row['cycle_number'],
                    is_active=row['is_active'],
                    created_date=datetime.fromisoformat(row['created_date']),
                    notes=row['notes']
                )
                
                return {'plan': plan.to_dict(), 'exercises': exercises}
            
            else:
                # Load all active plans for user
                cursor.execute("""
                    SELECT * FROM workout_plans 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_date DESC
                """, (user_id,))
                
                plans = []
                for row in cursor.fetchall():
                    plans.append(WorkoutPlan(
                        plan_id=row['plan_id'],
                        user_id=row['user_id'],
                        plan_name=row['plan_name'],
                        cycle_number=row['cycle_number'],
                        is_active=row['is_active'],
                        created_date=datetime.fromisoformat(row['created_date']),
                        notes=row['notes']
                    ))
                
                return plans

    def deactivate_user_plans(self, user_id: str) -> None:
        """Deactivate all active plans for user (used during rotation)."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE workout_plans 
                SET is_active = 0 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))

    # Personal Record operations
    def save_personal_record(self, user_id: str, exercise_name: str, record_type: str,
                           value: float, unit: str, date: Optional[datetime] = None,
                           notes: Optional[str] = None) -> PersonalRecord:
        """Save personal record for user."""
        if not validate_record_type(record_type):
            raise ValueError("Invalid record type. Must be one of: weight, reps, time, distance")

        if date is None:
            date = datetime.now()

        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO personal_records (user_id, exercise_name, record_type, value, unit, date_achieved, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, exercise_name, record_type, value, unit, date.isoformat(), notes))

            record_id = cursor.lastrowid
            if record_id is None:
                raise DatabaseError("Failed to create personal record: no row ID returned")
            return PersonalRecord(
                record_id=record_id,
                user_id=user_id,
                exercise_name=exercise_name,
                record_type=record_type,
                value=value,
                unit=unit,
                date_achieved=date,
                notes=notes
            )

    def load_personal_records(self, user_id: str, exercise_name: Optional[str] = None, 
                             record_type: Optional[str] = None) -> List[PersonalRecord]:
        """Load personal records for user with optional filters."""
        with self.get_cursor() as cursor:
            query = "SELECT * FROM personal_records WHERE user_id = ?"
            params = [user_id]

            if exercise_name:
                query += " AND exercise_name = ?"
                params.append(exercise_name)

            if record_type:
                if not validate_record_type(record_type):
                    raise ValueError("Invalid record type")
                query += " AND record_type = ?"
                params.append(record_type)

            query += " ORDER BY date_achieved DESC"

            cursor.execute(query, params)
            records = []
            for row in cursor.fetchall():
                records.append(PersonalRecord(
                    record_id=row['record_id'],
                    user_id=row['user_id'],
                    exercise_name=row['exercise_name'],
                    record_type=row['record_type'],
                    value=row['value'],
                    unit=row['unit'],
                    date_achieved=datetime.fromisoformat(row['date_achieved']),
                    notes=row['notes']
                ))
            return records

    def get_active_plan_count(self, user_id: str) -> int:
        """Get count of active plans for user."""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count FROM workout_plans 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            return cursor.fetchone()['count']

    def health_check(self) -> bool:
        """Check if database is accessible and healthy."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False