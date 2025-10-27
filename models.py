# models.py
# Zentrale Datenbankmodelle für FitLog
# (Deutsch/Englisch kommentiert, damit klar ist, was wozu gehört)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)

    # Relationship: Übungen, die in diesem Plan enthalten sind (mit Plan-spezifischen Feldern)
    exercises = db.relationship("PlanExercise", back_populates="plan", cascade="all, delete-orphan")

class Exercise(db.Model):
    __tablename__ = "exercises"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)

    # Reverse-Relation: in welchen Plänen kommt diese Übung vor
    plans = db.relationship("PlanExercise", back_populates="exercise", cascade="all, delete-orphan")

class PlanExercise(db.Model):
    """
    Join-Tabelle mit Zusatzattributen:
    - sets, reps, default_weight: plan-spezifische Vorgaben
    """
    __tablename__ = "plan_exercises"
    id = db.Column(db.Integer, primary_key=True)

    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)

    sets = db.Column(db.Integer, nullable=False, default=3)
    reps = db.Column(db.Integer, nullable=False, default=10)
    default_weight = db.Column(db.Integer, nullable=False, default=20)
    note = db.Column(db.String(255))

    plan = db.relationship("Plan", back_populates="exercises")
    exercise = db.relationship("Exercise", back_populates="plans")

class Training(db.Model):
    """
    Eine Trainingseinheit zu einem Plan (z. B. Datum, Dauer)
    """
    __tablename__ = "trainings"
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    duration_min = db.Column(db.Integer)

    sets = db.relationship("TrainingSet", back_populates="training", cascade="all, delete-orphan")

class TrainingSet(db.Model):
    """
    Ein tatsächlicher Satz während des Trainings – mit realem Gewicht/Wdh/Notiz.
    """
    __tablename__ = "training_sets"
    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey("trainings.id"), nullable=False)
    plan_exercise_id = db.Column(db.Integer, db.ForeignKey("plan_exercises.id"), nullable=False)

    weight = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255))

    training = db.relationship("Training", back_populates="sets")
    plan_exercise = db.relationship("PlanExercise")
