import unittest
import sys
import os

# Adjust import path to include backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.signal_analyzers import NameAnalyzer, SpeakingBehaviorAnalyzer
from engine.fusion_engine import FusionEngine


class TestSignalAnalyzers(unittest.TestCase):
    
    def setUp(self):
        self.candidate_name = "Alex Mercer"
        self.candidate_email = "alex.mercer@gmail.com"
        self.interviewers = ["Sarah Chen", "David Miller"]
        self.name_analyzer = NameAnalyzer(
            self.candidate_name, 
            self.candidate_email, 
            self.interviewers
        )

    def test_name_analyzer_candidate_match(self):
        # Direct match
        res = self.name_analyzer.analyze("Alex Mercer")
        self.assertTrue(res["score"] > 0.8)
        
        # Minor typo match (Jaro-Winkler should handle this)
        res_typo = self.name_analyzer.analyze("Alx Mercer")
        self.assertTrue(res_typo["score"] > 0.6)
        
        # Email username prefix match
        res_email = self.name_analyzer.analyze("alex.mercer")
        self.assertTrue(res_email["score"] > 0.8)

    def test_name_analyzer_interviewer_match(self):
        # Interviewers should yield -1.0
        res1 = self.name_analyzer.analyze("Sarah Chen")
        self.assertEqual(res1["score"], -1.0)
        
        res2 = self.name_analyzer.analyze("David Miller")
        self.assertEqual(res2["score"], -1.0)

    def test_name_analyzer_generic_device(self):
        # Default devices should yield 0.0 score
        res = self.name_analyzer.analyze("MacBook Pro")
        self.assertEqual(res["score"], 0.0)
        self.assertTrue(res["is_generic"])
        
        res_iphone = self.name_analyzer.analyze("iPhone 14")
        self.assertEqual(res_iphone["score"], 0.0)
        self.assertTrue(res_iphone["is_generic"])

    def test_speaking_behavior_analyzer(self):
        analyzer = SpeakingBehaviorAnalyzer()
        
        # Record speaking for another participant first to establish total duration
        analyzer.record_speaking("p2", 10.0)
        res_silent = analyzer.analyze("p1")
        self.assertEqual(res_silent["score"], -0.3)
        
        # Record speaking turns
        analyzer.record_speaking("p1", 10.0)  # Now p1 is 10/20 = 50%
        
        res_p1 = analyzer.analyze("p1")
        # Speaks 50% of the time, should be in candidate sweet spot
        self.assertTrue(res_p1["score"] >= 0.8)
        
        # Dominant talker (monologuing)
        analyzer_dom = SpeakingBehaviorAnalyzer()
        analyzer_dom.record_speaking("p1", 95.0)
        analyzer_dom.record_speaking("p2", 5.0)
        res_dom = analyzer_dom.analyze("p1")
        self.assertTrue(res_dom["score"] <= 0.5)  # Penalized for monologuing


class TestFusionEngine(unittest.TestCase):
    
    def test_fusion_scenario_execution(self):
        # Alex Mercer vs Sarah Chen (Interviewer)
        engine = FusionEngine(
            candidate_name="Alex Mercer",
            candidate_email="alex.mercer@gmail.com",
            interviewer_names=["Sarah Chen"]
        )
        
        # Start state: nobody is registered
        status = engine.get_candidate_status()
        self.assertFalse(status["candidate_identified"])
        
        # 1. Sarah joins (Interviewer)
        engine.handle_join("p_sarah", "Sarah Chen")
        
        # 2. Alex joins as 'MacBook Pro' (Generic Name)
        engine.handle_join("p_macbook", "MacBook Pro")
        
        # At this point, name analysis matches Sarah as interviewer, MacBook is generic.
        # Candidate should NOT be identified yet.
        status = engine.get_candidate_status()
        self.assertFalse(status["candidate_identified"])
        
        # 3. Sarah speaks to prompt
        engine.handle_speaking("p_sarah", 5.0)
        engine.handle_transcript("p_sarah", "Hi, are you Alex? Can you tell me about your background?")
        
        # 4. Alex speaks and self-identifies in transcript with candidate keywords, and turns on camera
        engine.handle_speaking("p_macbook", 10.0)
        engine.handle_webcam("p_macbook", True)
        engine.handle_transcript("p_macbook", "Yes hello, in my resume I listed my experience. Sorry for the device display name.")
        
        # 5. Sarah replies and Alex answers again to establish solid turn-taking graph interaction (>1 exchange)
        engine.handle_speaking("p_sarah", 3.0)
        engine.handle_transcript("p_sarah", "Excellent. Thanks for turning on your camera.")
        engine.handle_speaking("p_macbook", 5.0)
        engine.handle_transcript("p_macbook", "No problem, in my previous role I always kept it on.")
        
        # Now, speaking behavior, camera status, NLP transcript matching, and graph interaction should kick in
        status_after_speaking = engine.get_candidate_status()
        
        # Should identify MacBook Pro as candidate
        self.assertTrue(status_after_speaking["candidate_identified"])
        self.assertEqual(status_after_speaking["candidate_id"], "p_macbook")
        self.assertTrue(status_after_speaking["confidence"] > 0.4)
        
        # 6. Alex shares screen (Strong positive signal)
        engine.handle_screen_share("p_macbook", True)
        
        status_after_share = engine.get_candidate_status()
        # Confidence should increase further
        self.assertTrue(status_after_share["confidence"] > status_after_speaking["confidence"])



if __name__ == "__main__":
    unittest.main()
