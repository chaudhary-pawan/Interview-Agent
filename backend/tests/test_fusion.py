import unittest
import sys
import os

# Adjust import path to include backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.signal_analyzers import (
    NameAnalyzer, SpeakingBehaviorAnalyzer, 
    EngagementGraphAnalyzer, NLPTranscriptAnalyzer,
    JoinTimingAnalyzer, EmailDomainAnalyzer, AdaptiveWeightManager
)
from engine.fusion_engine import FusionEngine


class TestNameAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.candidate_name = "Alex Mercer"
        self.candidate_email = "alex.mercer@gmail.com"
        self.interviewers = ["Sarah Chen", "David Miller"]
        self.analyzer = NameAnalyzer(
            self.candidate_name, 
            self.candidate_email, 
            self.interviewers
        )

    def test_exact_candidate_match(self):
        res = self.analyzer.analyze("Alex Mercer")
        self.assertTrue(res["score"] > 0.8)
        
    def test_candidate_typo_match(self):
        res = self.analyzer.analyze("Alx Mercer")
        self.assertTrue(res["score"] > 0.6)
        
    def test_email_prefix_match(self):
        res = self.analyzer.analyze("alex.mercer")
        self.assertTrue(res["score"] > 0.8)

    def test_interviewer_negative_match(self):
        res1 = self.analyzer.analyze("Sarah Chen")
        self.assertEqual(res1["score"], -1.0)
        
        res2 = self.analyzer.analyze("David Miller")
        self.assertEqual(res2["score"], -1.0)

    def test_generic_device_names(self):
        for name in ["MacBook Pro", "iPhone 14", "Android", "Windows PC"]:
            res = self.analyzer.analyze(name)
            self.assertEqual(res["score"], 0.0, f"Failed for: {name}")
            self.assertTrue(res["is_generic"])

    def test_observer_keywords(self):
        for name in ["Otter.ai Recorder", "Meeting Observer", "Gong Bot"]:
            res = self.analyzer.analyze(name)
            self.assertEqual(res["score"], -1.0, f"Failed for: {name}")

    def test_empty_name(self):
        res = self.analyzer.analyze("")
        self.assertEqual(res["score"], 0.0)

    def test_unknown_name_penalty(self):
        res = self.analyzer.analyze("Random Person")
        self.assertTrue(res["score"] < 0, "Unknown names should get a slight penalty")


class TestSpeakingBehaviorAnalyzer(unittest.TestCase):

    def test_silent_participant(self):
        analyzer = SpeakingBehaviorAnalyzer()
        analyzer.record_speaking("p2", 10.0)
        res = analyzer.analyze("p1")
        self.assertTrue(res["score"] < 0)

    def test_optimal_candidate_ratio(self):
        analyzer = SpeakingBehaviorAnalyzer()
        analyzer.record_speaking("p1", 10.0)
        analyzer.record_speaking("p2", 10.0)
        res = analyzer.analyze("p1")
        # 50% ratio is in the sweet spot
        self.assertTrue(res["score"] >= 0.8)

    def test_dominant_speaker_penalty(self):
        analyzer = SpeakingBehaviorAnalyzer()
        analyzer.record_speaking("p1", 95.0)
        analyzer.record_speaking("p2", 5.0)
        res = analyzer.analyze("p1")
        self.assertTrue(res["score"] <= 0.5)

    def test_no_speaking_data(self):
        analyzer = SpeakingBehaviorAnalyzer()
        res = analyzer.analyze("p1")
        self.assertEqual(res["score"], 0.0)

    def test_low_speaking_ratio(self):
        analyzer = SpeakingBehaviorAnalyzer()
        analyzer.record_speaking("p1", 2.0)
        analyzer.record_speaking("p2", 50.0)
        res = analyzer.analyze("p1")
        self.assertTrue(res["score"] < 0.5, "Low speaking ratio should not score highly")


class TestEngagementGraphAnalyzer(unittest.TestCase):

    def test_no_data(self):
        analyzer = EngagementGraphAnalyzer()
        res = analyzer.analyze("p1")
        self.assertEqual(res["score"], 0.0)

    def test_interviewer_self_score(self):
        analyzer = EngagementGraphAnalyzer()
        analyzer.set_verified_interviewers({"p_sarah"})
        analyzer.record_turn("p_sarah")
        analyzer.record_turn("p_candidate")
        analyzer.record_turn("p_sarah")
        res = analyzer.analyze("p_sarah")
        self.assertTrue(res["score"] < 0, "Interviewers should get negative graph score")

    def test_candidate_high_interaction(self):
        analyzer = EngagementGraphAnalyzer()
        analyzer.set_verified_interviewers({"p_sarah"})
        # Simulate multiple Q&A exchanges
        for _ in range(5):
            analyzer.record_turn("p_sarah")
            analyzer.record_turn("p_candidate")
        res = analyzer.analyze("p_candidate")
        self.assertTrue(res["score"] > 0.5, "Candidate interacting with interviewers should score high")

    def test_silent_observer_penalty(self):
        analyzer = EngagementGraphAnalyzer()
        analyzer.set_verified_interviewers({"p_sarah"})
        analyzer.record_turn("p_sarah")
        analyzer.record_turn("p_candidate")
        # Observer never speaks
        res = analyzer.analyze("p_observer")
        self.assertTrue(res["score"] < 0, "Silent observers should score negatively")


class TestNLPTranscriptAnalyzer(unittest.TestCase):

    def test_candidate_language(self):
        analyzer = NLPTranscriptAnalyzer()
        analyzer.analyze_segment("p1", "In my previous role, I built a microservice using Python.")
        analyzer.analyze_segment("p1", "My experience includes working with React and FastAPI.")
        analyzer.analyze_segment("p1", "I graduated from MIT and I specialize in backend systems.")
        res = analyzer.analyze("p1")
        self.assertTrue(res["score"] > 0.3, f"Candidate language should score positively, got {res['score']}")

    def test_interviewer_language(self):
        analyzer = NLPTranscriptAnalyzer()
        analyzer.analyze_segment("p1", "Tell me about a time you handled a difficult situation.")
        analyzer.analyze_segment("p1", "Can you explain your approach to system design?")
        analyzer.analyze_segment("p1", "Walk us through your most recent project.")
        res = analyzer.analyze("p1")
        self.assertTrue(res["score"] < 0, f"Interviewer language should score negatively, got {res['score']}")

    def test_no_transcript(self):
        analyzer = NLPTranscriptAnalyzer()
        res = analyzer.analyze("p1")
        self.assertTrue(res["score"] < 0, "No transcript should score negatively")

    def test_mixed_language(self):
        analyzer = NLPTranscriptAnalyzer()
        analyzer.analyze_segment("p1", "Tell me about your experience building React apps.")
        analyzer.analyze_segment("p1", "My experience is mostly in frontend development.")
        res = analyzer.analyze("p1")
        # Should be mixed — close to neutral
        self.assertTrue(-0.5 < res["score"] < 0.5)


class TestJoinTimingAnalyzer(unittest.TestCase):

    def test_early_joiner(self):
        analyzer = JoinTimingAnalyzer()
        analyzer.record_join("p_sarah", 0)
        analyzer.record_join("p_candidate", 2)
        analyzer.record_join("p_observer", 30)
        res = analyzer.analyze("p_candidate")
        self.assertTrue(res["score"] > 0, "Early joiners should score positively")

    def test_late_joiner_penalty(self):
        analyzer = JoinTimingAnalyzer()
        analyzer.record_join("p_sarah", 0)
        analyzer.record_join("p_candidate", 2)
        analyzer.record_join("p_obs1", 3)
        analyzer.record_join("p_obs2", 4)
        analyzer.record_join("p_obs3", 5)
        analyzer.record_join("p_late", 70)
        res = analyzer.analyze("p_late")
        self.assertTrue(res["score"] < 0, "Very late joiners should score negatively")

    def test_not_enough_participants(self):
        analyzer = JoinTimingAnalyzer()
        analyzer.record_join("p1", 0)
        res = analyzer.analyze("p1")
        self.assertEqual(res["score"], 0.0)

    def test_no_join_recorded(self):
        analyzer = JoinTimingAnalyzer()
        res = analyzer.analyze("p_unknown")
        self.assertEqual(res["score"], 0.0)


class TestEmailDomainAnalyzer(unittest.TestCase):

    def test_matching_candidate_domain(self):
        analyzer = EmailDomainAnalyzer("alex@gmail.com")
        res = analyzer.analyze("candidate@gmail.com")
        self.assertTrue(res["score"] > 0)

    def test_company_domain_negative(self):
        analyzer = EmailDomainAnalyzer("alex@gmail.com", company_domains=["acme.com"])
        res = analyzer.analyze("sarah@acme.com")
        self.assertTrue(res["score"] < 0)

    def test_no_email(self):
        analyzer = EmailDomainAnalyzer("alex@gmail.com")
        res = analyzer.analyze("")
        self.assertEqual(res["score"], 0.0)

    def test_personal_domain_slight_positive(self):
        analyzer = EmailDomainAnalyzer("alex@protonmail.com")
        res = analyzer.analyze("someone@outlook.com")
        self.assertTrue(res["score"] >= 0)


class TestAdaptiveWeightManager(unittest.TestCase):

    def test_initial_weights_preserved(self):
        weights = {"name": 0.5, "speaking": 0.3, "nlp": 0.2}
        mgr = AdaptiveWeightManager(weights)
        result = mgr.get_weights()
        for k in weights:
            self.assertAlmostEqual(result[k], weights[k], places=5)

    def test_correct_identification_boosts_positive_signals(self):
        weights = {"name": 0.5, "speaking": 0.3, "nlp": 0.2}
        mgr = AdaptiveWeightManager(weights)
        # Signal scores: name was very helpful, nlp was not
        signal_scores = {"name": 0.9, "speaking": 0.5, "nlp": -0.3}
        mgr.update_weights(signal_scores, was_correct=True)
        new_weights = mgr.get_weights()
        # Name weight should increase relative to nlp
        self.assertTrue(new_weights["name"] > new_weights["nlp"])

    def test_incorrect_identification_reduces_contributing_signals(self):
        weights = {"name": 0.5, "speaking": 0.3, "nlp": 0.2}
        mgr = AdaptiveWeightManager(weights)
        signal_scores = {"name": 0.9, "speaking": 0.5, "nlp": -0.3}
        mgr.update_weights(signal_scores, was_correct=False)
        new_weights = mgr.get_weights()
        # Name was the strongest positive but was wrong — should be reduced
        self.assertTrue(new_weights["name"] < 0.5)

    def test_weights_always_sum_to_one(self):
        weights = {"a": 0.3, "b": 0.3, "c": 0.2, "d": 0.2}
        mgr = AdaptiveWeightManager(weights)
        for _ in range(10):
            mgr.update_weights({"a": 0.5, "b": -0.2, "c": 0.8, "d": 0.1}, was_correct=True)
        total = sum(mgr.get_weights().values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_min_weight_enforced(self):
        weights = {"a": 0.9, "b": 0.1}
        mgr = AdaptiveWeightManager(weights)
        # Hammer b with negative updates
        for _ in range(100):
            mgr.update_weights({"a": 1.0, "b": -1.0}, was_correct=False)
        new_weights = mgr.get_weights()
        self.assertTrue(new_weights["b"] >= AdaptiveWeightManager.MIN_WEIGHT)


class TestFusionEngineIntegration(unittest.TestCase):

    def test_scenario_macbook_pro(self):
        """Scenario 1: Candidate joins as MacBook Pro — should be identified via behavior."""
        engine = FusionEngine(
            candidate_name="Alex Mercer",
            candidate_email="alex.mercer@gmail.com",
            interviewer_names=["Sarah Chen"]
        )
        
        # Empty state
        status = engine.get_candidate_status()
        self.assertFalse(status["candidate_identified"])
        
        # Joins
        engine.handle_join("p_sarah", "Sarah Chen", join_time=0)
        engine.handle_join("p_macbook", "MacBook Pro", join_time=2)
        engine.handle_join("p_otter", "Otter.ai Recorder", join_time=4)
        
        # Not identified yet
        status = engine.get_candidate_status()
        self.assertFalse(status["candidate_identified"])
        
        # Q&A exchange
        engine.handle_speaking("p_sarah", 5.0)
        engine.handle_transcript("p_sarah", "Hi, are you Alex? Tell me about your background.")
        engine.handle_speaking("p_macbook", 10.0)
        engine.handle_webcam("p_macbook", True)
        engine.handle_transcript("p_macbook", "Yes hello, in my resume I listed my experience at Google.")
        
        # More exchange to build graph
        engine.handle_speaking("p_sarah", 3.0)
        engine.handle_transcript("p_sarah", "Excellent. Can you explain your system design approach?")
        engine.handle_speaking("p_macbook", 8.0)
        engine.handle_transcript("p_macbook", "In my previous role I built distributed caching systems.")
        
        # Additional exchange to push past threshold with new weight distribution
        engine.handle_speaking("p_sarah", 3.0)
        engine.handle_transcript("p_sarah", "How would you handle scaling that?")
        engine.handle_speaking("p_macbook", 7.0)
        engine.handle_transcript("p_macbook", "I implemented horizontal sharding. My background is in distributed systems.")
        engine.handle_screen_share("p_macbook", True)
        
        # Should be identified now
        status = engine.get_candidate_status()
        self.assertTrue(status["candidate_identified"])
        self.assertEqual(status["candidate_id"], "p_macbook")
        self.assertTrue(status["confidence"] > 0.3)

    def test_scenario_wrong_name(self):
        """Scenario 3: Metadata says 'John Smith' but candidate is 'Jonathan Smythe'."""
        engine = FusionEngine(
            candidate_name="John Smith",
            candidate_email="jsmith99@yahoo.com",
            interviewer_names=["Sarah Chen", "David Miller"]
        )
        
        engine.handle_join("p_sarah", "Sarah Chen", join_time=0)
        engine.handle_join("p_david", "David Miller", join_time=2)
        engine.handle_join("p_jonathan", "Jonathan Smythe", join_time=4)
        engine.handle_webcam("p_jonathan", True)
        
        # Q&A
        engine.handle_speaking("p_sarah", 4.0)
        engine.handle_transcript("p_sarah", "Tell me about your experience with microservices.")
        engine.handle_speaking("p_jonathan", 8.0)
        engine.handle_transcript("p_jonathan", "My experience includes building APIs. In my resume I listed 3 projects.")
        engine.handle_speaking("p_david", 3.0)
        engine.handle_transcript("p_david", "Walk us through your deployment strategy.")
        engine.handle_speaking("p_jonathan", 10.0)
        engine.handle_transcript("p_jonathan", "I built CI/CD pipelines in my previous role using Kubernetes.")
        
        status = engine.get_candidate_status()
        self.assertTrue(status["candidate_identified"])
        self.assertEqual(status["candidate_id"], "p_jonathan")

    def test_scenario_silent_observers(self):
        """Scenario 6: Silent observers should not be identified as candidate."""
        engine = FusionEngine(
            candidate_name="Alice Johnson",
            candidate_email="alice.j@ucla.edu",
            interviewer_names=["Sarah Chen", "Elena Rostova"]
        )
        
        engine.handle_join("p_sarah", "Sarah Chen", join_time=0)
        engine.handle_join("p_elena", "Elena Rostova", join_time=1)
        engine.handle_join("p_alice", "Alice Johnson", join_time=3)
        engine.handle_join("p_vp_obs", "VP Product Observer", join_time=4)
        engine.handle_join("p_gong", "Gong Meeting Recorder", join_time=5)
        
        engine.handle_webcam("p_alice", True)
        
        # Only Alice and interviewers speak
        engine.handle_speaking("p_elena", 8.0)
        engine.handle_transcript("p_elena", "Welcome Alice. Tell me about your background.")
        engine.handle_speaking("p_alice", 6.0)
        engine.handle_transcript("p_alice", "My experience is in machine learning. I graduated from UCLA.")
        engine.handle_speaking("p_sarah", 5.0)
        engine.handle_transcript("p_sarah", "Can you explain your thesis work?")
        engine.handle_speaking("p_alice", 12.0)
        engine.handle_transcript("p_alice", "I built a transformer model in my previous role for NLP tasks.")
        engine.handle_speaking("p_sarah", 3.0)
        engine.handle_transcript("p_sarah", "How would you handle deploying that at scale?")
        engine.handle_speaking("p_alice", 8.0)
        engine.handle_transcript("p_alice", "I have been using Kubernetes and my stack includes Docker and Terraform.")
        engine.handle_screen_share("p_alice", True)
        
        status = engine.get_candidate_status()
        self.assertTrue(status["candidate_identified"])
        self.assertEqual(status["candidate_id"], "p_alice")
        
        # Observers should have very low confidence
        for p in status["participants"]:
            if p["id"] in ["p_vp_obs", "p_gong"]:
                self.assertTrue(p["confidence"] < 0.1, 
                    f"Observer {p['display_name']} should have near-zero confidence, got {p['confidence']}")

    def test_confirm_identification_learning(self):
        """Test that confirm_identification triggers weight updates."""
        engine = FusionEngine(
            candidate_name="Test User",
            candidate_email="test@gmail.com",
            interviewer_names=["Interviewer One"]
        )
        
        engine.handle_join("p_int", "Interviewer One", join_time=0)
        engine.handle_join("p_cand", "Test User", join_time=2)
        engine.handle_webcam("p_cand", True)
        engine.handle_speaking("p_int", 5.0)
        engine.handle_transcript("p_int", "Tell me about your experience.")
        engine.handle_speaking("p_cand", 10.0)
        engine.handle_transcript("p_cand", "My experience includes building systems in my previous role.")
        engine.handle_speaking("p_int", 3.0)
        engine.handle_transcript("p_int", "Can you explain that further?")
        engine.handle_speaking("p_cand", 8.0)
        engine.handle_transcript("p_cand", "I built a microservice in my previous role using Python and FastAPI.")
        engine.handle_screen_share("p_cand", True)
        
        # Verify candidate is actually identified first
        status = engine.get_candidate_status()
        self.assertTrue(status["candidate_identified"], 
            f"Candidate must be identified before testing learning. Confidence: {status['confidence']}")
        
        initial_weights = engine.weight_manager.get_weights()
        
        # Confirm correct identification
        engine.confirm_identification(was_correct=True)
        
        updated_weights = engine.weight_manager.get_weights()
        self.assertEqual(engine.weight_manager.session_count, 1)
        # Weights should have shifted (at least one should be different)
        self.assertFalse(
            all(abs(initial_weights[k] - updated_weights[k]) < 1e-10 for k in initial_weights),
            "Weights should update after confirmation"
        )

    def test_learning_stats_in_status(self):
        """Test that get_candidate_status includes learning_stats."""
        engine = FusionEngine(
            candidate_name="Test",
            candidate_email="test@test.com",
            interviewer_names=["Int"]
        )
        engine.handle_join("p1", "Test", join_time=0)
        status = engine.get_candidate_status()
        self.assertIn("learning_stats", status)
        self.assertIn("session_count", status["learning_stats"])
        self.assertIn("current_weights", status["learning_stats"])


class TestZeroKnowledgeMode(unittest.TestCase):

    def test_zero_knowledge_single_candidate(self):
        """Verify that candidate can be identified purely on behavioral/conversational cues without any metadata."""
        engine = FusionEngine(
            candidate_name=None,
            candidate_email=None,
            interviewer_names=[]
        )
        
        # Joins
        engine.handle_join("p_int1", "Sarah Chen", join_time=0)
        engine.handle_join("p_int2", "David Miller", join_time=2)
        engine.handle_join("p_unknown", "Dev_Ninja_42", join_time=4)
        engine.handle_webcam("p_unknown", True)
        
        # Recalculate - none identified yet
        engine.recalculate()
        status = engine.get_candidate_status()
        self.assertFalse(status["candidate_identified"])

        # Q&A Exchanges
        # 1. p_int1 speaks interviewer text
        engine.handle_speaking("p_int1", 5.0)
        engine.handle_transcript("p_int1", "Welcome to the interview. Tell me about your background.")
        
        # 2. p_unknown speaks candidate text
        engine.handle_speaking("p_unknown", 10.0)
        engine.handle_transcript("p_unknown", "My experience includes working with React. In my resume I built several dashboards.")
        
        # 3. p_int2 speaks interviewer text
        engine.handle_speaking("p_int2", 6.0)
        engine.handle_transcript("p_int2", "Can you explain how you optimized database performance?")
        
        # 4. p_unknown speaks candidate text
        engine.handle_speaking("p_unknown", 12.0)
        engine.handle_transcript("p_unknown", "In my previous role, I implemented indexing and caching.")

        # Trigger screen sharing (strong candidate indicator)
        engine.handle_screen_share("p_unknown", True)
        
        # Recalculate
        engine.recalculate()
        status = engine.get_candidate_status()
        
        # Verify candidate is correctly identified
        self.assertTrue(status["candidate_identified"])
        self.assertEqual(status["candidate_id"], "p_unknown")
        
        # Verify interviewers were dynamically bootstrapped
        self.assertIn("p_int1", engine.verified_interviewers)
        self.assertIn("p_int2", engine.verified_interviewers)
        self.assertNotIn("p_unknown", engine.verified_interviewers)


if __name__ == "__main__":
    unittest.main()
