import math
from typing import Dict, List, Any, Set
from .signal_analyzers import (
    NameAnalyzer, 
    SpeakingBehaviorAnalyzer, 
    EngagementGraphAnalyzer, 
    NLPTranscriptAnalyzer
)

class FusionEngine:
    """
    Sherlock Multi-Signal Fusion Engine.
    Fuses Name Matching, Speaking Behavior, NLP Transcripts, turn-taking graphs, 
    and presence data into a real-time confidence score.
    """
    # Signal Weights (sum to 1.0)
    WEIGHTS = {
        "name": 0.35,
        "speaking": 0.20,
        "graph": 0.20,
        "nlp": 0.15,
        "presence": 0.10
    }
    
    # Baseline threshold score for "Null Participant" (no candidate identified yet)
    # Higher values require stronger positive evidence to identify a candidate.
    NULL_THRESHOLD = 0.4

    def __init__(self, candidate_name: str, candidate_email: str, interviewer_names: List[str]):
        self.candidate_name = candidate_name
        self.candidate_email = candidate_email
        self.interviewer_names = interviewer_names
        
        # Instantiate analyzers
        self.name_analyzer = NameAnalyzer(candidate_name, candidate_email, interviewer_names)
        self.speak_analyzer = SpeakingBehaviorAnalyzer()
        self.graph_analyzer = EngagementGraphAnalyzer()
        self.nlp_analyzer = NLPTranscriptAnalyzer()
        
        # Registry of participants
        # { participant_id: { metadata } }
        self.participants: Dict[str, Dict[str, Any]] = {}
        
        # Keep track of identified interviewers to feed the Turn Graph
        self.verified_interviewers: Set[str] = set()

    def register_participant(self, participant_id: str, display_name: str):
        if participant_id not in self.participants:
            self.participants[participant_id] = {
                "id": participant_id,
                "display_name": display_name,
                "webcam_on": False,
                "screen_share_on": False,
                "is_present": True,
                "confidence": 0.0,
                "signals": {},
                "explanation": ""
            }
            
        # Re-check if this participant matches an interviewer's name to verify them
        name_analysis = self.name_analyzer.analyze(display_name)
        if name_analysis["score"] == -1.0:
            self.verified_interviewers.add(participant_id)
            self.graph_analyzer.set_verified_interviewers(self.verified_interviewers)

    def handle_join(self, participant_id: str, display_name: str):
        self.register_participant(participant_id, display_name)
        self.participants[participant_id]["is_present"] = True
        self.recalculate()

    def handle_leave(self, participant_id: str):
        if participant_id in self.participants:
            self.participants[participant_id]["is_present"] = False
            self.participants[participant_id]["screen_share_on"] = False
            self.recalculate()

    def handle_name_change(self, participant_id: str, new_display_name: str):
        if participant_id in self.participants:
            self.participants[participant_id]["display_name"] = new_display_name
            # Recheck interviewer status
            name_analysis = self.name_analyzer.analyze(new_display_name)
            if name_analysis["score"] == -1.0:
                self.verified_interviewers.add(participant_id)
            else:
                self.verified_interviewers.discard(participant_id)
            self.graph_analyzer.set_verified_interviewers(self.verified_interviewers)
            self.recalculate()

    def handle_webcam(self, participant_id: str, is_on: bool):
        if participant_id in self.participants:
            self.participants[participant_id]["webcam_on"] = is_on
            self.recalculate()

    def handle_screen_share(self, participant_id: str, is_on: bool):
        if participant_id in self.participants:
            self.participants[participant_id]["screen_share_on"] = is_on
            self.recalculate()

    def handle_speaking(self, participant_id: str, duration: float):
        if participant_id in self.participants:
            self.speak_analyzer.record_speaking(participant_id, duration)
            self.graph_analyzer.record_turn(participant_id)
            self.recalculate()

    def handle_transcript(self, participant_id: str, text: str):
        if participant_id in self.participants:
            self.nlp_analyzer.analyze_segment(participant_id, text)
            self.graph_analyzer.record_turn(participant_id)
            self.recalculate()

    def recalculate(self):
        """
        Runs multi-signal fusion and calculates probability for each participant.
        """
        active_participants = [p for p in self.participants.values() if p["is_present"]]
        if not active_participants:
            return

        scores: Dict[str, float] = {}
        raw_signals_data: Dict[str, Dict[str, Any]] = {}

        # 1. Compute individual signal scores
        for p in active_participants:
            pid = p["id"]
            
            # Analyze components
            name_res = self.name_analyzer.analyze(p["display_name"])
            speak_res = self.speak_analyzer.analyze(pid)
            graph_res = self.graph_analyzer.analyze(pid)
            nlp_res = self.nlp_analyzer.analyze(pid)
            
            # Presence score calculation
            pres_score = 0.0
            pres_reasons = []
            if p["webcam_on"]:
                pres_score += 0.2
                pres_reasons.append("Webcam active (+20%)")
            else:
                pres_score -= 0.1
                pres_reasons.append("Webcam off (-10%)")
                
            if p["screen_share_on"]:
                # Sharing screens is a very strong candidate signal
                pres_score += 1.0
                pres_reasons.append("Sharing screen (+100%)")
                
            pres_score = max(-0.2, min(1.0, pres_score))
            pres_reason = ", ".join(pres_reasons) if pres_reasons else "No presence indicators."

            # Package sub-signals
            signals = {
                "name": {
                    "score": name_res["score"],
                    "weight": self.WEIGHTS["name"],
                    "weighted": name_res["score"] * self.WEIGHTS["name"],
                    "reason": name_res["reason"]
                },
                "speaking": {
                    "score": speak_res["score"],
                    "weight": self.WEIGHTS["speaking"],
                    "weighted": speak_res["score"] * self.WEIGHTS["speaking"],
                    "reason": speak_res["reason"]
                },
                "graph": {
                    "score": graph_res["score"],
                    "weight": self.WEIGHTS["graph"],
                    "weighted": graph_res["score"] * self.WEIGHTS["graph"],
                    "reason": graph_res["reason"]
                },
                "nlp": {
                    "score": nlp_res["score"],
                    "weight": self.WEIGHTS["nlp"],
                    "weighted": nlp_res["score"] * self.WEIGHTS["nlp"],
                    "reason": nlp_res["reason"]
                },
                "presence": {
                    "score": pres_score,
                    "weight": self.WEIGHTS["presence"],
                    "weighted": pres_score * self.WEIGHTS["presence"],
                    "reason": pres_reason
                }
            }

            raw_signals_data[pid] = signals

            # Calculate total weighted score (no overrides — let signals speak for themselves)
            total_weighted_score = sum(s["weighted"] for s in signals.values())

            scores[pid] = total_weighted_score

        # 2. Probability normalization via Softmax with a Null Threshold
        # P(C_i) = exp(Score_i) / (exp(Null_threshold) + sum(exp(Score_k)))
        exp_sum = math.exp(self.NULL_THRESHOLD)
        for pid, score in scores.items():
            exp_sum += math.exp(score)

        for p in active_participants:
            pid = p["id"]
            p["confidence"] = math.exp(scores[pid]) / exp_sum
            p["signals"] = raw_signals_data[pid]

        # Handle non-present participants (set confidence to 0)
        for p in self.participants.values():
            if not p["is_present"]:
                p["confidence"] = 0.0

        # 3. Generate natural language explanations
        for p in active_participants:
            pid = p["id"]
            signals = p["signals"]
            
            # Sort signal contributions to explain supporting/conflicting items
            supporting = []
            conflicting = []
            
            for name, data in signals.items():
                if data["score"] > 0.1:
                    supporting.append(f"{name.capitalize()} ({data['reason']})")
                elif data["score"] < -0.1:
                    conflicting.append(f"{name.capitalize()} ({data['reason']})")

            explanation_lines = []
            confidence_pct = p["confidence"] * 100
            
            is_obs = any(kw in p["display_name"].lower() for kw in ["observer", "recorder", "bot", "assistant", "gong", "otter", "notetaker", "spectator"])
            if is_obs:
                explanation_lines.append("Identified as a silent meeting observer or recording bot based on display name. Excluded from candidate selection.")
            elif p["display_name"] in self.interviewer_names or pid in self.verified_interviewers:
                explanation_lines.append(f"Identified as an Interviewer with high confidence. Matches interviewer metadata.")
            else:
                if confidence_pct > 50:
                    explanation_lines.append(
                        f"Identified as the candidate with {confidence_pct:.1f}% confidence."
                    )
                else:
                    explanation_lines.append(
                        f"Uncertain if candidate (Confidence: {confidence_pct:.1f}%)."
                    )

                if supporting:
                    explanation_lines.append("Supporting evidence: " + "; ".join(supporting))
                if conflicting:
                    explanation_lines.append("Conflicting evidence: " + "; ".join(conflicting))
                    
            p["explanation"] = " \n".join(explanation_lines)

    def get_candidate_status(self) -> Dict[str, Any]:
        """
        Returns the current state of all participants and identifies the top candidate.
        """
        active_participants = [p for p in self.participants.values() if p["is_present"]]
        
        if not active_participants:
            return {
                "candidate_identified": False,
                "candidate_id": None,
                "confidence": 0.0,
                "explanation": "No participants present in the meeting.",
                "participants": []
            }

        # Sort by confidence descending
        sorted_p = sorted(active_participants, key=lambda x: x["confidence"], reverse=True)
        top = sorted_p[0]

        # The probability of Null Participant is 1.0 - sum of present active probabilities
        total_active_prob = sum(p["confidence"] for p in active_participants)
        null_probability = 1.0 - total_active_prob
        
        # If the top candidate's confidence is above 40% and greater than null probability
        candidate_identified = top["confidence"] > 0.4 and top["confidence"] > null_probability

        return {
            "candidate_identified": candidate_identified,
            "candidate_id": top["id"] if candidate_identified else None,
            "confidence": top["confidence"] if candidate_identified else 0.0,
            "explanation": top["explanation"] if candidate_identified else "Confidence too low to definitively identify a candidate. Monitoring meeting signals...",
            "participants": sorted_p
        }
