# models/drama.py
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Character:
    id: str
    name: str
    role: str  # male_lead, female_lead, supporting
    description: str
    personality_traits: List[str]

@dataclass
class PlotPoint:
    id: str
    episode: int
    sequence: int
    description: str
    characters_involved: List[str]
    plot_type: str  # conflict, romance, revelation, choice
    emotional_tone: str  # happy, sad, tense, romantic

@dataclass
class Drama:
    id: str
    title: str
    genre: List[str]
    tags: List[str]
    description: str
    characters: List[Character]
    plot_points: List[PlotPoint]
    total_episodes: int
    source_platform: str
    popularity_score: float
    created_at: datetime
    updated_at: datetime
