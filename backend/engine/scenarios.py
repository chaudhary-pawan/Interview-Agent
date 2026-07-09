from typing import List, Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO 1: Candidate joins as a generic device name (MacBook Pro)
    # Challenge: No name match. Must identify via behavior signals.
    # ─────────────────────────────────────────────────────────────────────
    "scenario_1": {
        "title": "Scenario 1: Generic Device Name & Screen Share",
        "description": "Candidate 'Alex Mercer' joins as 'MacBook Pro' with camera off. They later turn on camera, speak in detail, and share screen.",
        "metadata": {
            "candidate_name": "Alex Mercer",
            "candidate_email": "alex.mercer@gmail.com",
            "interviewer_names": ["Sarah Chen"]
        },
        "events": [
            {"time": 0,  "type": "join",        "id": "p_sarah",   "name": "Sarah Chen"},
            {"time": 2,  "type": "join",        "id": "p_macbook", "name": "MacBook Pro"},
            {"time": 4,  "type": "join",        "id": "p_otter",   "name": "Otter.ai Recorder"},
            {"time": 6,  "type": "speaking",    "id": "p_sarah",   "duration": 4.0},
            {"time": 6,  "type": "transcript",  "id": "p_sarah",   "generate_role": "interviewer"},
            {"time": 9,  "type": "speaking",    "id": "p_macbook", "duration": 6.0},
            {"time": 9,  "type": "transcript",  "id": "p_macbook", "generate_role": "candidate"},
            {"time": 12, "type": "webcam",      "id": "p_macbook", "is_on": True},
            {"time": 14, "type": "speaking",    "id": "p_sarah",   "duration": 5.0},
            {"time": 14, "type": "transcript",  "id": "p_sarah",   "generate_role": "interviewer"},
            {"time": 17, "type": "speaking",    "id": "p_macbook", "duration": 10.0},
            {"time": 17, "type": "transcript",  "id": "p_macbook", "generate_role": "candidate"},
            {"time": 20, "type": "speaking",    "id": "p_sarah",   "duration": 3.0},
            {"time": 20, "type": "transcript",  "id": "p_sarah",   "generate_role": "interviewer"},
            {"time": 23, "type": "screenshare", "id": "p_macbook", "is_on": True},
            {"time": 25, "type": "speaking",    "id": "p_macbook", "duration": 8.0},
            {"time": 25, "type": "transcript",  "id": "p_macbook", "generate_role": "candidate"}
        ]
    },

    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO 2: Candidate joins using a nickname ("Dev_Ninja_42")
    # Challenge: Name is completely unrelated to expected candidate.
    # ─────────────────────────────────────────────────────────────────────
    "scenario_2": {
        "title": "Scenario 2: Candidate Joins with a Nickname",
        "description": "Expected candidate 'Priya Sharma' joins as 'Dev_Ninja_42'. Must identify via speaking, transcript semantics, and self-introduction.",
        "metadata": {
            "candidate_name": "Priya Sharma",
            "candidate_email": "priya.sharma@outlook.com",
            "interviewer_names": ["Michael Torres", "Sarah Chen"]
        },
        "events": [
            {"time": 0,  "type": "join",       "id": "p_michael", "name": "Michael Torres"},
            {"time": 2,  "type": "join",       "id": "p_sarah",   "name": "Sarah Chen"},
            {"time": 3,  "type": "join",       "id": "p_ninja",   "name": "Dev_Ninja_42"},
            {"time": 5,  "type": "webcam",     "id": "p_ninja",   "is_on": True},
            {"time": 7,  "type": "speaking",   "id": "p_michael", "duration": 5.0},
            {"time": 7,  "type": "transcript", "id": "p_michael", "generate_role": "interviewer"},
            {"time": 10, "type": "speaking",   "id": "p_ninja",   "duration": 7.0},
            {"time": 10, "type": "transcript", "id": "p_ninja",   "generate_role": "candidate"},
            {"time": 14, "type": "speaking",   "id": "p_sarah",   "duration": 5.0},
            {"time": 14, "type": "transcript", "id": "p_sarah",   "generate_role": "interviewer"},
            {"time": 18, "type": "speaking",   "id": "p_ninja",   "duration": 12.0},
            {"time": 18, "type": "transcript", "id": "p_ninja",   "generate_role": "candidate"},
            {"time": 22, "type": "speaking",   "id": "p_michael", "duration": 4.0},
            {"time": 22, "type": "transcript", "id": "p_michael", "generate_role": "interviewer"},
            {"time": 25, "type": "speaking",   "id": "p_ninja",   "duration": 10.0},
            {"time": 25, "type": "transcript", "id": "p_ninja",   "generate_role": "candidate"}
        ]
    },

    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO 3: Interviewer enters wrong candidate name
    # Challenge: Metadata says "John Smith" but candidate is "Jonathan Smythe".
    #            Must rely on fuzzy matching + behavioral signals.
    # ─────────────────────────────────────────────────────────────────────
    "scenario_3": {
        "title": "Scenario 3: Interviewer Entered Wrong Candidate Name",
        "description": "HR registered 'John Smith' but the real candidate is 'Jonathan Smythe'. Fuzzy name matching + transcript signals must resolve the mismatch.",
        "metadata": {
            "candidate_name": "John Smith",
            "candidate_email": "jsmith99@yahoo.com",
            "interviewer_names": ["Sarah Chen", "David Miller"]
        },
        "events": [
            {"time": 0,  "type": "join",       "id": "p_sarah",    "name": "Sarah Chen"},
            {"time": 2,  "type": "join",       "id": "p_david",    "name": "David Miller"},
            {"time": 4,  "type": "join",       "id": "p_jonathan", "name": "Jonathan Smythe"},
            {"time": 6,  "type": "webcam",     "id": "p_jonathan", "is_on": True},
            {"time": 8,  "type": "speaking",   "id": "p_sarah",    "duration": 4.0},
            {"time": 8,  "type": "transcript", "id": "p_sarah",    "generate_role": "interviewer"},
            {"time": 11, "type": "speaking",   "id": "p_jonathan", "duration": 6.0},
            {"time": 11, "type": "transcript", "id": "p_jonathan", "generate_role": "candidate"},
            {"time": 14, "type": "speaking",   "id": "p_david",    "duration": 6.0},
            {"time": 14, "type": "transcript", "id": "p_david",    "generate_role": "interviewer"},
            {"time": 17, "type": "speaking",   "id": "p_jonathan", "duration": 12.0},
            {"time": 17, "type": "transcript", "id": "p_jonathan", "generate_role": "candidate"},
            {"time": 21, "type": "speaking",   "id": "p_sarah",    "duration": 3.0},
            {"time": 21, "type": "transcript", "id": "p_sarah",    "generate_role": "interviewer"},
            {"time": 24, "type": "screenshare","id": "p_jonathan", "is_on": True},
            {"time": 26, "type": "speaking",   "id": "p_jonathan", "duration": 8.0},
            {"time": 26, "type": "transcript", "id": "p_jonathan", "generate_role": "candidate"}
        ]
    },

    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO 4: Multiple interviewers are present
    # Challenge: 3 interviewers + 1 candidate. Must distinguish the single
    #            candidate from a panel of interviewers.
    # ─────────────────────────────────────────────────────────────────────
    "scenario_4": {
        "title": "Scenario 4: Multiple Interviewers Panel",
        "description": "Candidate 'Ravi Patel' faces a 3-person interview panel: Sarah (tech), David (hiring manager), and Lisa (team lead). System must isolate the single candidate.",
        "metadata": {
            "candidate_name": "Ravi Patel",
            "candidate_email": "ravi.patel@gmail.com",
            "interviewer_names": ["Sarah Chen", "David Miller", "Lisa Wang"]
        },
        "events": [
            {"time": 0,  "type": "join",       "id": "p_sarah",  "name": "Sarah Chen"},
            {"time": 1,  "type": "join",       "id": "p_david",  "name": "David Miller"},
            {"time": 2,  "type": "join",       "id": "p_lisa",   "name": "Lisa Wang"},
            {"time": 4,  "type": "join",       "id": "p_ravi",   "name": "Ravi Patel"},
            {"time": 6,  "type": "webcam",     "id": "p_ravi",   "is_on": True},
            {"time": 8,  "type": "speaking",   "id": "p_sarah",  "duration": 5.0},
            {"time": 8,  "type": "transcript", "id": "p_sarah",  "generate_role": "interviewer"},
            {"time": 11, "type": "speaking",   "id": "p_ravi",   "duration": 7.0},
            {"time": 11, "type": "transcript", "id": "p_ravi",   "generate_role": "candidate"},
            {"time": 15, "type": "speaking",   "id": "p_david",  "duration": 4.0},
            {"time": 15, "type": "transcript", "id": "p_david",  "generate_role": "interviewer"},
            {"time": 18, "type": "speaking",   "id": "p_ravi",   "duration": 10.0},
            {"time": 18, "type": "transcript", "id": "p_ravi",   "generate_role": "candidate"},
            {"time": 22, "type": "speaking",   "id": "p_lisa",   "duration": 5.0},
            {"time": 22, "type": "transcript", "id": "p_lisa",   "generate_role": "interviewer"},
            {"time": 26, "type": "speaking",   "id": "p_ravi",   "duration": 12.0},
            {"time": 26, "type": "transcript", "id": "p_ravi",   "generate_role": "candidate"}
        ]
    },

    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO 5: Candidate changes their display name mid-interview
    # Challenge: Name transitions from "JD" → "Jane Doe". System must
    #            track identity across the rename event.
    # ─────────────────────────────────────────────────────────────────────
    "scenario_5": {
        "title": "Scenario 5: Display Name Change Mid-Interview",
        "description": "Candidate 'Jane Doe' initially joins as 'JD', introduces herself, and later renames to her full name. System tracks identity across the rename.",
        "metadata": {
            "candidate_name": "Jane Doe",
            "candidate_email": "jane.doe@outlook.com",
            "interviewer_names": ["Sarah Chen"]
        },
        "events": [
            {"time": 0,  "type": "join",       "id": "p_sarah", "name": "Sarah Chen"},
            {"time": 2,  "type": "join",       "id": "p_jd",    "name": "JD"},
            {"time": 4,  "type": "speaking",   "id": "p_sarah", "duration": 4.0},
            {"time": 4,  "type": "transcript", "id": "p_sarah", "generate_role": "interviewer"},
            {"time": 7,  "type": "speaking",   "id": "p_jd",    "duration": 6.0},
            {"time": 7,  "type": "transcript", "id": "p_jd",    "generate_role": "candidate"},
            {"time": 10, "type": "rename",     "id": "p_jd",    "name": "Jane Doe"},
            {"time": 12, "type": "webcam",     "id": "p_jd",    "is_on": True},
            {"time": 14, "type": "speaking",   "id": "p_sarah", "duration": 4.0},
            {"time": 14, "type": "transcript", "id": "p_sarah", "generate_role": "interviewer"},
            {"time": 17, "type": "speaking",   "id": "p_jd",    "duration": 10.0},
            {"time": 17, "type": "transcript", "id": "p_jd",    "generate_role": "candidate"},
            {"time": 20, "type": "speaking",   "id": "p_sarah", "duration": 3.0},
            {"time": 20, "type": "transcript", "id": "p_sarah", "generate_role": "interviewer"},
            {"time": 23, "type": "screenshare","id": "p_jd",    "is_on": True},
            {"time": 25, "type": "speaking",   "id": "p_jd",    "duration": 8.0},
            {"time": 25, "type": "transcript", "id": "p_jd",    "generate_role": "candidate"}
        ]
    },

    # ─────────────────────────────────────────────────────────────────────
    # SCENARIO 6: Multiple silent observers join
    # Challenge: 3 silent observers + 1 recorder bot + 1 candidate + 2 interviewers.
    #            System must filter out all non-participants using behavior signals.
    # ─────────────────────────────────────────────────────────────────────
    "scenario_6": {
        "title": "Scenario 6: Silent Observers & Recording Bots",
        "description": "Candidate 'Alice Johnson' faces Sarah (tech) and Elena (HR). A VP observer, Gong recorder, and CTO all sit silently. System must filter noise.",
        "metadata": {
            "candidate_name": "Alice Johnson",
            "candidate_email": "alice.j@ucla.edu",
            "interviewer_names": ["Sarah Chen", "Elena Rostova"]
        },
        "events": [
            {"time": 0,  "type": "join",       "id": "p_sarah",   "name": "Sarah Chen"},
            {"time": 1,  "type": "join",       "id": "p_elena",   "name": "Elena Rostova"},
            {"time": 3,  "type": "join",       "id": "p_alice",   "name": "Alice Johnson"},
            {"time": 4,  "type": "join",       "id": "p_vp_obs",  "name": "VP Product Observer"},
            {"time": 5,  "type": "join",       "id": "p_gong",    "name": "Gong Meeting Recorder"},
            {"time": 6,  "type": "join",       "id": "p_cto",     "name": "James (CTO - Observer)"},
            {"time": 8,  "type": "webcam",     "id": "p_alice",   "is_on": True},
            {"time": 10, "type": "speaking",   "id": "p_elena",   "duration": 8.0},
            {"time": 10, "type": "transcript", "id": "p_elena",   "text": "Hi Alice, welcome. Before Sarah starts the technical session, let me spend a minute explaining our onboarding flow, benefits, and team structures."},
            {"time": 13, "type": "speaking",   "id": "p_alice",   "duration": 3.0},
            {"time": 13, "type": "transcript", "id": "p_alice",   "generate_role": "candidate"},
            {"time": 16, "type": "speaking",   "id": "p_sarah",   "duration": 5.0},
            {"time": 16, "type": "transcript", "id": "p_sarah",   "generate_role": "interviewer"},
            {"time": 19, "type": "speaking",   "id": "p_alice",   "duration": 12.0},
            {"time": 19, "type": "transcript", "id": "p_alice",   "generate_role": "candidate"},
            {"time": 23, "type": "speaking",   "id": "p_sarah",   "duration": 4.0},
            {"time": 23, "type": "transcript", "id": "p_sarah",   "generate_role": "interviewer"},
            {"time": 26, "type": "speaking",   "id": "p_alice",   "duration": 10.0},
            {"time": 26, "type": "transcript", "id": "p_alice",   "generate_role": "candidate"}
        ]
    }
}
