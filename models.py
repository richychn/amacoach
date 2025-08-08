"""
Data model definitions for AmaCoach MCP server.

This module defines the data structures used throughout the application
according to the project specifications in project_plan.md.
"""

from dataclasses import dataclass
from typing import List, Optional, Union
from datetime import datetime
import json


@dataclass
class User:
    """User model with rotation settings."""
    user_id: str
    name: str
    created_date: datetime
    rotation_weeks: int = 6
    last_rotation_date: Optional[datetime] = None
    current_cycle_number: int = 1

    def to_dict(self) -> dict:
        """Convert user to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'created_date': self.created_date.isoformat(),
            'rotation_weeks': self.rotation_weeks,
            'last_rotation_date': self.last_rotation_date.isoformat() if self.last_rotation_date else None,
            'current_cycle_number': self.current_cycle_number
        }


@dataclass
class Exercise:
    """Exercise model with metadata."""
    exercise_id: int
    name: str
    description: str
    muscle_groups: List[str]
    equipment_needed: List[str]
    difficulty_level: int  # 1-5 scale
    instructions: str
    created_date: datetime
    created_by_user_id: str

    def to_dict(self) -> dict:
        """Convert exercise to dictionary for JSON serialization."""
        return {
            'exercise_id': self.exercise_id,
            'name': self.name,
            'description': self.description,
            'muscle_groups': self.muscle_groups,
            'equipment_needed': self.equipment_needed,
            'difficulty_level': self.difficulty_level,
            'instructions': self.instructions,
            'created_date': self.created_date.isoformat(),
            'created_by_user_id': self.created_by_user_id
        }


@dataclass
class WorkoutPlan:
    """Workout plan model with 3-plan constraint support."""
    plan_id: int
    user_id: str
    plan_name: str
    cycle_number: int
    is_active: bool
    created_date: datetime
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert workout plan to dictionary for JSON serialization."""
        return {
            'plan_id': self.plan_id,
            'user_id': self.user_id,
            'plan_name': self.plan_name,
            'cycle_number': self.cycle_number,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat(),
            'notes': self.notes
        }


@dataclass
class PlannedExercise:
    """Planned exercise model for exercises within workout plans."""
    planned_exercise_id: int
    plan_id: int
    exercise_id: int
    sets: int
    reps: int
    weight: Optional[float] = None
    duration: Optional[int] = None  # in seconds
    notes: Optional[str] = None
    order_in_plan: int = 1

    def to_dict(self) -> dict:
        """Convert planned exercise to dictionary for JSON serialization."""
        return {
            'planned_exercise_id': self.planned_exercise_id,
            'plan_id': self.plan_id,
            'exercise_id': self.exercise_id,
            'sets': self.sets,
            'reps': self.reps,
            'weight': self.weight,
            'duration': self.duration,
            'notes': self.notes,
            'order_in_plan': self.order_in_plan
        }


@dataclass
class PersonalRecord:
    """Personal record model for tracking user PRs."""
    record_id: int
    user_id: str
    exercise_name: str
    record_type: str  # weight/reps/time/distance
    value: float
    unit: str
    date_achieved: datetime
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert personal record to dictionary for JSON serialization."""
        return {
            'record_id': self.record_id,
            'user_id': self.user_id,
            'exercise_name': self.exercise_name,
            'record_type': self.record_type,
            'value': self.value,
            'unit': self.unit,
            'date_achieved': self.date_achieved.isoformat(),
            'notes': self.notes
        }


# Type aliases for better code readability
ExerciseFilter = dict
WorkoutPlanWithExercises = dict
PersonalRecordFilter = dict


def validate_difficulty_level(difficulty: int) -> bool:
    """Validate difficulty level is within 1-5 range."""
    return 1 <= difficulty <= 5


def validate_record_type(record_type: str) -> bool:
    """Validate record type is one of the allowed types."""
    valid_types = {'weight', 'reps', 'time', 'distance'}
    return record_type.lower() in valid_types


def serialize_json_field(data: Union[List[str], dict]) -> str:
    """Serialize Python data structures to JSON string for database storage."""
    return json.dumps(data)


def deserialize_json_field(json_str: str) -> Union[List[str], dict]:
    """Deserialize JSON string from database to Python data structures."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []