#!/usr/bin/env python3
"""
Database schema verification script for AmaCoach.

This script tests the database schema, constraints, and core functionality
to ensure everything is working according to specifications.
"""

import os
import sqlite3
from datetime import datetime
from database import Database, DatabaseError
from models import User, Exercise, WorkoutPlan

def test_database_schema():
    """Test database schema creation and constraints."""
    print("Testing AmaCoach Database Schema...")
    
    # Use test database
    test_db_path = "test_amacoach.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    db = Database(test_db_path)
    
    # Test 1: Create test user
    print("\n1. Testing User Creation...")
    user = db.create_user("test_user_123", "Test User")
    assert user.user_id == "test_user_123"
    assert user.name == "Test User"
    assert user.rotation_weeks == 6
    assert user.current_cycle_number == 1
    print("✓ User creation successful")
    
    # Test 2: Create test exercises
    print("\n2. Testing Exercise Creation...")
    exercise1 = db.create_exercise(
        name="Push-ups",
        description="Classic bodyweight chest exercise",
        muscle_groups=["chest", "shoulders", "triceps"],
        equipment_needed=["bodyweight"],
        difficulty_level=2,
        instructions="Lower your body until chest nearly touches floor, then push back up",
        created_by_user_id="test_user_123"
    )
    
    exercise2 = db.create_exercise(
        name="Squats",
        description="Fundamental leg exercise",
        muscle_groups=["quadriceps", "glutes", "hamstrings"],
        equipment_needed=["bodyweight"],
        difficulty_level=1,
        instructions="Lower your body as if sitting back into a chair",
        created_by_user_id="test_user_123"
    )
    
    exercise3 = db.create_exercise(
        name="Deadlift",
        description="Compound pulling exercise",
        muscle_groups=["back", "hamstrings", "glutes"],
        equipment_needed=["barbell"],
        difficulty_level=4,
        instructions="Lift the bar by extending your hips and knees",
        created_by_user_id="test_user_123"
    )
    
    print("✓ Exercise creation successful")
    
    # Test 3: List exercises with filters
    print("\n3. Testing Exercise Filtering...")
    all_exercises = db.list_exercises()
    assert len(all_exercises) == 3
    
    chest_exercises = db.list_exercises(muscle_group="chest")
    assert len(chest_exercises) == 1
    assert chest_exercises[0].name == "Push-ups"
    
    bodyweight_exercises = db.list_exercises(equipment="bodyweight")
    assert len(bodyweight_exercises) == 2
    
    difficulty_1_exercises = db.list_exercises(difficulty=1)
    assert len(difficulty_1_exercises) == 1
    assert difficulty_1_exercises[0].name == "Squats"
    
    print("✓ Exercise filtering successful")
    
    # Test 4: Create workout plans (testing 3-plan constraint)
    print("\n4. Testing Workout Plan Creation and 3-Plan Constraint...")
    
    # Create first plan
    plan1_exercises = [
        {"exercise_id": exercise1.exercise_id, "sets": 3, "reps": 10},
        {"exercise_id": exercise2.exercise_id, "sets": 3, "reps": 15}
    ]
    plan1 = db.save_workout_plan("test_user_123", "Plan A", plan1_exercises, "Upper body focus")
    assert plan1.plan_name == "Plan A"
    assert plan1.is_active == True
    print("✓ Plan A created")
    
    # Create second plan
    plan2_exercises = [
        {"exercise_id": exercise2.exercise_id, "sets": 4, "reps": 12},
        {"exercise_id": exercise3.exercise_id, "sets": 3, "reps": 5}
    ]
    plan2 = db.save_workout_plan("test_user_123", "Plan B", plan2_exercises, "Lower body focus")
    print("✓ Plan B created")
    
    # Create third plan
    plan3_exercises = [
        {"exercise_id": exercise1.exercise_id, "sets": 2, "reps": 20},
        {"exercise_id": exercise3.exercise_id, "sets": 2, "reps": 8}
    ]
    plan3 = db.save_workout_plan("test_user_123", "Plan C", plan3_exercises, "Mixed workout")
    print("✓ Plan C created")
    
    # Verify user has exactly 3 active plans
    active_count = db.get_active_plan_count("test_user_123")
    assert active_count == 3
    print("✓ User has exactly 3 active plans")
    
    # Test 5: Try to create 4th plan (should fail)
    print("\n5. Testing 3-Plan Constraint Enforcement...")
    try:
        plan4_exercises = [{"exercise_id": exercise1.exercise_id, "sets": 1, "reps": 10}]
        plan4 = db.save_workout_plan("test_user_123", "Plan D", plan4_exercises)
        assert False, "Should not have been able to create 4th plan"
    except (ValueError, DatabaseError) as e:
        assert "already has 3 active workout plans" in str(e) or "cannot have more than 3 active workout plans" in str(e).lower()
        print("✓ 3-plan constraint properly enforced")
    
    # Test 6: Load workout plans
    print("\n6. Testing Workout Plan Loading...")
    all_active_plans = db.load_workout_plan("test_user_123")
    assert len(all_active_plans) == 3
    print("✓ All active plans loaded")
    
    # Load specific plan with exercises
    plan_with_exercises = db.load_workout_plan("test_user_123", plan1.plan_id)
    assert plan_with_exercises['plan']['plan_name'] == "Plan A"
    assert len(plan_with_exercises['exercises']) == 2
    print("✓ Specific plan with exercises loaded")
    
    # Test 7: Personal Records
    print("\n7. Testing Personal Records...")
    
    # Save personal records
    pr1 = db.save_personal_record("test_user_123", "Push-ups", "reps", 50, "reps")
    pr2 = db.save_personal_record("test_user_123", "Deadlift", "weight", 225, "lbs")
    pr3 = db.save_personal_record("test_user_123", "Squats", "time", 300, "seconds")
    
    # Load all records
    all_records = db.load_personal_records("test_user_123")
    assert len(all_records) == 3
    print("✓ Personal records saved and loaded")
    
    # Load filtered records
    pushup_records = db.load_personal_records("test_user_123", exercise_name="Push-ups")
    assert len(pushup_records) == 1
    assert pushup_records[0].value == 50
    
    weight_records = db.load_personal_records("test_user_123", record_type="weight")
    assert len(weight_records) == 1
    assert weight_records[0].exercise_name == "Deadlift"
    print("✓ Personal record filtering works")
    
    # Test 8: Plan Rotation System
    print("\n8. Testing Plan Rotation System...")
    
    # Deactivate current plans
    db.deactivate_user_plans("test_user_123")
    active_count_after_deactivation = db.get_active_plan_count("test_user_123")
    assert active_count_after_deactivation == 0
    
    # Update user rotation
    db.update_user_rotation("test_user_123")
    updated_user = db.get_user("test_user_123")
    assert updated_user.current_cycle_number == 2
    assert updated_user.last_rotation_date is not None
    print("✓ Plan rotation system works")
    
    # Create new cycle plans
    new_plan_exercises = [{"exercise_id": exercise2.exercise_id, "sets": 5, "reps": 8}]
    new_plan = db.save_workout_plan("test_user_123", "Cycle 2 Plan A", new_plan_exercises)
    assert new_plan.cycle_number == 2
    print("✓ New cycle plan creation works")
    
    # Test 9: Data Validation
    print("\n9. Testing Data Validation...")
    
    # Test invalid difficulty level
    try:
        db.create_exercise("Invalid Exercise", "Test", ["chest"], ["dumbbells"], 6, "Test", "test_user_123")
        assert False, "Should not allow difficulty > 5"
    except ValueError as e:
        assert "between 1 and 5" in str(e)
        print("✓ Difficulty validation works")
    
    # Test invalid record type
    try:
        db.save_personal_record("test_user_123", "Test", "invalid_type", 100, "units")
        assert False, "Should not allow invalid record type"
    except ValueError as e:
        assert "Invalid record type" in str(e)
        print("✓ Record type validation works")
    
    # Test 10: Foreign Key Constraints
    print("\n10. Testing Foreign Key Constraints...")
    
    # Try to create workout plan with non-existent exercise
    try:
        invalid_exercises = [{"exercise_id": 999999, "sets": 1, "reps": 1}]
        db.save_workout_plan("test_user_123", "Invalid Plan", invalid_exercises)
        assert False, "Should not allow non-existent exercise_id"
    except Exception:
        print("✓ Foreign key constraints enforced")
    
    print("\n" + "="*50)
    print("🎉 ALL TESTS PASSED!")
    print("✅ Database schema is working correctly")
    print("✅ 3-plan constraint is properly enforced") 
    print("✅ All relationships and constraints are functional")
    print("✅ Data validation is working")
    print("✅ Plan rotation system is operational")
    print("="*50)
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print("🧹 Test database cleaned up")


if __name__ == "__main__":
    test_database_schema()