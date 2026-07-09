import re
from typing import Dict, List, Set
from rapidfuzz import distance

class NameAnalyzer:
    """
    Analyzes participant display names against candidate and interviewer metadata.
    Handles typos, generic names, and interviewer exclusions.
    """
    GENERIC_NAMES = {
        "macbook", "iphone", "ipad", "android", "windows", "zoom", "user", 
        "guest", "anonymous", "call-in", "meeting room", "conference", 
        "unknown", "pc", "laptop", "mobile", "phone", "tablet"
    }

    def __init__(self, candidate_name: str, candidate_email: str, interviewer_names: List[str]):
        self.candidate_name = candidate_name.strip().lower()
        self.candidate_email_prefix = candidate_email.split("@")[0].strip().lower() if "@" in candidate_email else ""
        self.interviewer_names = [name.strip().lower() for name in interviewer_names]

    def is_generic(self, display_name: str) -> bool:
        name_clean = re.sub(r'[^a-zA-Z0-9\s]', '', display_name.lower())
        words = name_clean.split()
        return any(word in self.GENERIC_NAMES for word in words) or not words

    def analyze(self, display_name: str) -> Dict[str, float]:
        """
        Returns a score in [-1.0, 1.0] and a reasoning string.
        """
        name_lower = display_name.strip().lower()
        
        if not name_lower:
            return {"score": 0.0, "is_generic": True, "reason": "Empty display name"}

        # 1. Check if generic name (e.g. MacBook Pro)
        if self.is_generic(display_name):
            return {
                "score": 0.0, 
                "is_generic": True, 
                "reason": f"Generic device/placeholder name '{display_name}' provides no identity signals."
            }

        # 2. Check if name matches observer/recorder keywords (Negative indicator)
        observer_keywords = {"observer", "recorder", "bot", "assistant", "gong", "otter", "notetaker", "spectator"}
        if any(kw in name_lower for kw in observer_keywords):
            return {
                "score": -1.0,
                "is_generic": False,
                "reason": f"Identified as meeting observer/bot based on display name ('{display_name}'). Strongly unlikely to be the candidate."
            }

        # 3. Check match with Interviewers (Negative indicator)
        best_interviewer_match = 0.0
        matched_interviewer = ""
        for int_name in self.interviewer_names:
            # We use Jaro-Winkler similarity (0 to 1)
            sim = distance.JaroWinkler.similarity(name_lower, int_name)
            if sim > best_interviewer_match:
                best_interviewer_match = sim
                matched_interviewer = int_name

        if best_interviewer_match > 0.85:
            # Very strong negative match: this is an interviewer
            return {
                "score": -1.0,
                "is_generic": False,
                "reason": f"Matches interviewer '{matched_interviewer}' ({best_interviewer_match:.1%} similarity). Strongly unlikely to be the candidate."
            }

        # 3. Check match with Candidate Name (Positive indicator)
        cand_name_sim = distance.JaroWinkler.similarity(name_lower, self.candidate_name)
        
        # 4. Check match with Candidate Email prefix
        email_sim = 0.0
        if self.candidate_email_prefix:
            email_sim = distance.JaroWinkler.similarity(name_lower, self.candidate_email_prefix)

        best_cand_sim = max(cand_name_sim, email_sim)

        if best_cand_sim > 0.85:
            return {
                "score": best_cand_sim,
                "is_generic": False,
                "reason": f"High name similarity to candidate '{self.candidate_name}' ({best_cand_sim:.1%})."
            }
        elif best_cand_sim > 0.60:
            return {
                "score": best_cand_sim * 0.5,
                "is_generic": False,
                "reason": f"Moderate name similarity to candidate '{self.candidate_name}' ({best_cand_sim:.1%})."
            }
        
        # If we got here, it's not a generic name, doesn't match interviewer, and doesn't match candidate.
        # It could be a nickname or another participant.
        return {
            "score": -0.1,  # Slight penalty because it doesn't match the candidate name at all
            "is_generic": False,
            "reason": f"Name '{display_name}' does not match candidate metadata."
        }


class SpeakingBehaviorAnalyzer:
    """
    Analyzes talking patterns, durations, and frequency.
    In a typical interview, candidates speak 30%-70% of the time.
    """
    def __init__(self):
        self.speaking_durations: Dict[str, float] = {}
        self.total_duration = 0.0

    def record_speaking(self, participant_id: str, duration: float):
        if duration <= 0:
            return
        self.speaking_durations[participant_id] = self.speaking_durations.get(participant_id, 0.0) + duration
        self.total_duration += duration

    def analyze(self, participant_id: str) -> Dict[str, float]:
        if self.total_duration == 0:
            return {"score": 0.0, "ratio": 0.0, "reason": "No speaking activity recorded yet."}
            
        dur = self.speaking_durations.get(participant_id, 0.0)
        ratio = dur / self.total_duration
        
        # Bell-shaped curve: peak candidate probability around 45% speaking ratio.
        # Below 20% or above 80% gets penalized.
        if ratio == 0:
            score = -0.8  # Silent participant is very unlikely to be the candidate in an interview
            reason = "Participant has been completely silent. Highly unlikely to be the candidate."
        elif ratio < 0.2:
            score = ratio * 2 - 0.2  # Slight penalty to neutral
            reason = f"Low talking activity ({ratio:.1%}). Speaks in short bursts, typical of observer or minor interviewer."
        elif ratio <= 0.7:
            # 0.2 to 0.7 is the sweet spot.
            # Max score of 1.0 around 0.45 ratio.
            dist_from_peak = abs(ratio - 0.45)
            score = 1.0 - (dist_from_peak / 0.25)
            score = max(0.2, min(1.0, score))
            reason = f"Optimal candidate speaking ratio ({ratio:.1%}). Active responder."
        else:
            # Over 70% talking means they are taking over the call entirely (could be a dominant interviewer or a solo presenter)
            score = 1.0 - (ratio - 0.7) * 2
            score = max(-0.2, score)
            reason = f"Very high speaking ratio ({ratio:.1%}). Monologuing, potential solo presenter."
            
        return {
            "score": score,
            "ratio": ratio,
            "reason": reason
        }


class EngagementGraphAnalyzer:
    """
    Tracks turn-taking interaction graph.
    Builds a directed edge when Speaker A speaks followed by Speaker B.
    In standard interviews, the Candidate interacts heavily with Interviewers.
    """
    def __init__(self):
        self.last_speaker: str = None
        # Adjacency matrix: turn transitions. {speaker_from: {speaker_to: count}}
        self.transitions: Dict[str, Dict[str, int]] = {}
        self.verified_interviewers: Set[str] = set()

    def set_verified_interviewers(self, interviewer_ids: Set[str]):
        self.verified_interviewers = interviewer_ids

    def record_turn(self, speaker_id: str):
        if self.last_speaker and self.last_speaker != speaker_id:
            if self.last_speaker not in self.transitions:
                self.transitions[self.last_speaker] = {}
            self.transitions[self.last_speaker][speaker_id] = self.transitions[self.last_speaker].get(speaker_id, 0) + 1
        self.last_speaker = speaker_id

    def analyze(self, participant_id: str) -> Dict[str, float]:
        if not self.transitions or not self.verified_interviewers:
            return {"score": 0.0, "reason": "No conversation flow data yet."}

        # If they are a verified interviewer, their graph score as a candidate should be low
        if participant_id in self.verified_interviewers:
            return {"score": -0.5, "reason": "Interactions align with interviewer role."}

        # Count mutual exchanges with verified interviewers
        interviewer_exchanges = 0
        total_exchanges = 0

        for speaker_from, targets in self.transitions.items():
            for speaker_to, count in targets.items():
                if speaker_from == participant_id or speaker_to == participant_id:
                    total_exchanges += count
                    other = speaker_to if speaker_from == participant_id else speaker_from
                    if other in self.verified_interviewers:
                        interviewer_exchanges += count

        if total_exchanges == 0:
            return {"score": -0.5, "reason": "No dialogue turns involving this participant. Silent observers score negatively."}

        ratio = interviewer_exchanges / total_exchanges
        
        # If they interact mostly with the interviewers, they are highly likely the candidate
        if ratio > 0.6 and interviewer_exchanges >= 2:
            score = min(1.0, ratio * 0.8 + 0.2)
            reason = f"High conversational interaction with interviewers ({ratio:.1%} of turns are Q&A exchanges)."
        elif interviewer_exchanges >= 1:
            score = 0.3
            reason = "Some conversation exchange with interviewers detected."
        else:
            score = -0.2
            reason = "No direct dialogue exchanges with verified interviewers."

        return {
            "score": score,
            "reason": reason
        }


class NLPTranscriptAnalyzer:
    """
    Analyzes live transcript text for candidate-indicative semantic cues vs interviewer cues.
    Acts as a lightweight, zero-latency classifier mimicking sentence embeddings.
    """
    # Phrases typically spoken by a candidate answering questions
    CANDIDATE_KEYWORDS = [
        r"\bi\s+worked\s+at\b", r"\bmy\s+experience\b", r"\bmy\s+resume\b", 
        r"\bmy\s+previous\s+role\b", r"\bin\s+my\s+past\b", r"\bi\s+built\s+a\b", 
        r"\bmy\s+background\s+is\b", r"\bi\s+graduated\b", r"\bmy\s+major\b", 
        r"\bi\s+specialize\s+in\b", r"\bi\s+have\s+been\s+using\b", r"\bmy\s+stack\b",
        r"\bi\s+implemented\b", r"\bmy\s+responsibilities\b", r"\bi\s+design\b"
    ]

    # Phrases typically spoken by an interviewer guiding/asking
    INTERVIEWER_KEYWORDS = [
        r"\btell\s+me\s+about\b", r"\bcan\s+you\s+explain\b", r"\bwhy\s+do\s+you\s+want\b", 
        r"\bdescribe\s+a\s+scenario\b", r"\bhow\s+would\s+you\s+handle\b", 
        r"\bwelcome\s+to\s+the\s+interview\b", r"\bquestions\s+for\s+us\b",
        r"\bwe\s+are\s+looking\s+for\b", r"\byour\s+background\b", r"\bwalk\s+us\s+through\b",
        r"\bwhat\s+is\s+your\s+experience\b"
    ]

    def __init__(self):
        self.candidate_counts: Dict[str, int] = {}
        self.interviewer_counts: Dict[str, int] = {}

    def analyze_segment(self, participant_id: str, text: str):
        text_lower = text.lower()
        
        # Count candidate markers
        cand_matches = 0
        for pattern in self.CANDIDATE_KEYWORDS:
            if re.search(pattern, text_lower):
                cand_matches += 1

        # Count interviewer markers
        int_matches = 0
        for pattern in self.INTERVIEWER_KEYWORDS:
            if re.search(pattern, text_lower):
                int_matches += 1

        self.candidate_counts[participant_id] = self.candidate_counts.get(participant_id, 0) + cand_matches
        self.interviewer_counts[participant_id] = self.interviewer_counts.get(participant_id, 0) + int_matches

    def analyze(self, participant_id: str) -> Dict[str, float]:
        cand = self.candidate_counts.get(participant_id, 0)
        interv = self.interviewer_counts.get(participant_id, 0)

        total = cand + interv
        if total == 0:
            return {"score": -0.3, "reason": "No transcript activity from this participant. No semantic markers to analyze."}

        # Candidate ratio
        ratio = cand / total
        
        if ratio > 0.7:
            score = min(1.0, 0.4 + ratio * 0.6)
            reason = f"Strong semantic matching: Speaker uses self-referencing candidate language ({cand} matches, e.g. resume, experience)."
        elif ratio < 0.3:
            score = -ratio * 0.8 - 0.2
            reason = f"Strong interviewer semantics: Speaker uses inquiry and prompt language ({interv} matches, e.g. 'tell me about', 'explain')."
        else:
            score = 0.1
            reason = f"Mixed semantic indicators (Candidate markers: {cand}, Interviewer markers: {interv})."

        return {
            "score": score,
            "reason": reason
        }
