from typing import List, Dict
from datetime import datetime


class DecayScorer:
    DECAY_RATE = 0.95
    MIN_CONFIDENCE = 0.1

    def calculate_decay(self, access_count: int, days_since_last_access: float) -> float:
        access_decay = self.DECAY_RATE ** access_count
        time_decay = max(0.1, 1.0 - (days_since_last_access / 30.0))
        score = access_decay * time_decay
        return max(self.MIN_CONFIDENCE, round(score, 4))

    def get_effective_importance(self, base_confidence: float, decay_score: float) -> float:
        return round(base_confidence * decay_score, 4)
