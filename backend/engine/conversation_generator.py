import os
import random
import re
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ConversationGenerator:
    """
    Generates real-time dialogue between interviewer and candidate.
    Uses Gemini API if available, otherwise falls back to a rich template-based random generator.
    """
    def __init__(self, candidate_name: str, candidate_joined_name: str, interviewer_names: List[str]):
        self.candidate_name = candidate_name
        self.candidate_joined_name = candidate_joined_name
        self.interviewer_names = interviewer_names
        self.current_interviewer = interviewer_names[0] if interviewer_names else "Interviewer"
        
        # Configure Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_llm = False
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Use gemini-2.0-flash for fast, real-time dialogue (no thinking step)
                self.model = genai.GenerativeModel("gemini-2.0-flash")
                # Validate the API key on startup
                self.model.generate_content("ping", request_options={"timeout": 10.0})
                self.use_llm = True
                print("Gemini API key validated successfully. Using LLM mode.")
            except Exception as e:
                print(f"Gemini API key validation failed: {e}. Falling back to local template mode.")
                self.use_llm = False

        # Template Pools for fallback mode
        self.interviewer_greetings = [
            "Hi, welcome everyone. I see we have some new participants. Who is the candidate?",
            "Good morning. Thanks for joining today's session. Let's do a quick roll call.",
            "Hello, welcome. Let's verify who is in the room. Are you the candidate?"
        ]
        
        self.candidate_identifications = [
            "Hi! Sorry about the display name, my laptop default name is {joined_name}. I am {name}.",
            "Yes hello, I'm {name}. I joined as {joined_name} because I'm using my work profile.",
            "Hi, I am {name}. Sorry, it seems my profile default name is {joined_name}. I'll rename myself soon."
        ]
        
        # Paired QA templates to guarantee semantic coherence in fallback mode
        self.qa_pairs = [
            {
                "question": "Can you tell me about your experience building React applications and managing state?",
                "answer": "In my previous role, I migrated our core dashboard to React. I used Zustand for lightweight state management and optimized re-renders, which cut bundle sizes by 30%."
            },
            {
                "question": "Walk us through a major bug you resolved in production and how you went about it.",
                "answer": "I resolved a major memory leak in a Node.js API. By capturing heap dumps and analyzing them in Chrome DevTools, I found that an event listener closure was retaining database references."
            },
            {
                "question": "How do you handle scalability and backend performance optimization in your previous roles?",
                "answer": "In my resume, I detailed building a real-time analytics pipeline using FastAPI and Redis cache. We implemented connection pooling and query optimization to handle 5k requests per second."
            },
            {
                "question": "Tell me about a project on your resume that you are most proud of.",
                "answer": "I built a custom state-management library for our frontend stack. My background is in front-end performance tuning and micro-frontends architecture."
            }
        ]
        
        # Select a single QA pair to maintain consistency throughout this session
        self.selected_qa = random.choice(self.qa_pairs)

        self.screenshare_prompts = [
            "Great, thanks. Do you have a project or some code you can share and walk us through?",
            "Awesome answer. Let's do a quick walk-through of your portfolio. Can you share your screen?",
            "Nice. I'd love to see some of your code. If you're ready, please share your screen."
        ]
        
        self.screenshare_answers = [
            "Yes, I am sharing my screen now. Here is a custom state-management utility I built.",
            "Sure, let me open my IDE. I am sharing my screen. Here is my system design diagram.",
            "No problem, sharing my screen now. You should see my terminal and VS Code."
        ]

    def _generate_llm_turn(self, speaker_role: str, speaker_name: str, target_role: str, target_name: str, history: List[Dict[str, str]], prompt_instruction: str) -> str:
        """
        Queries Gemini API to generate natural, dynamic dialogue turn.
        """
        history_formatted = "\n".join([f"{h['speaker']}: {h['text']}" for h in history[-6:]])
        
        system_prompt = (
            f"You are simulating a live virtual job interview between an interviewer named '{self.current_interviewer}' "
            f"and a candidate named '{self.candidate_name}' (who initially joined the call as '{self.candidate_joined_name}').\n\n"
            f"The conversation history is:\n{history_formatted}\n\n"
            f"Generate the next turn in the conversation. You are writing the response for '{speaker_name}' (role: {speaker_role}) speaking to '{target_name}' (role: {target_role}).\n"
            f"Context: {prompt_instruction}\n"
            f"Guidelines:\n"
            f"- Make it sound natural, professional, and conversational.\n"
            f"- Keep the length short (1-3 sentences), suitable for a live voice call.\n"
            f"- Do NOT include the speaker's name or colon at the beginning. Return ONLY the spoken text.\n"
            f"- Do NOT include actions in parentheses (e.g. (laughs)). Only return words spoken."
        )

        try:
            response = self.model.generate_content(
                system_prompt,
                request_options={"timeout": 15.0}
            )
            text = response.text.strip()
            # Strip potential name headers (e.g. "Sarah Chen: Hello" -> "Hello")
            text = re.sub(r'^[A-Za-z\s]+:\s*', '', text)
            return text
        except Exception as e:
            print(f"Gemini API call failed: {e}. Falling back to template mode for this turn.")
            return self._generate_template_turn(speaker_role, history)

    def _generate_template_turn(self, speaker_role: str, history: List[Dict[str, str]]) -> str:
        """
        Template-based fallback dialogue generator.
        """
        # Count candidate and interviewer turns in history to decide the stage
        cand_turns = sum(1 for h in history if h["role"] == "candidate")
        int_turns = sum(1 for h in history if h["role"] == "interviewer")
        
        if speaker_role == "interviewer":
            if int_turns == 0:
                return random.choice(self.interviewer_greetings)
            elif int_turns == 1:
                return self.selected_qa["question"]
            elif int_turns == 2:
                return random.choice(self.screenshare_prompts)
            else:
                return "Excellent. That matches what we are looking for. Do you have any questions for me?"
        else: # candidate
            if cand_turns == 0:
                return random.choice(self.candidate_identifications).format(
                    joined_name=self.candidate_joined_name, 
                    name=self.candidate_name
                )
            elif cand_turns == 1:
                return self.selected_qa["answer"]
            elif cand_turns == 2:
                return random.choice(self.screenshare_answers)
            else:
                return "Thank you. Yes, in my previous role I worked closely with product stakeholders..."

    def generate_turn(self, speaker_id: str, speaker_name: str, role: str, history: List[Dict[str, str]]) -> str:
        """
        Public entrypoint to generate the next turn's transcript.
        """
        if not self.use_llm:
            return self._generate_template_turn(role, history)
            
        # Determine the contextual instruction based on turn counts
        cand_turns = sum(1 for h in history if h["role"] == "candidate")
        int_turns = sum(1 for h in history if h["role"] == "interviewer")
        
        if role == "interviewer":
            if int_turns == 0:
                instruction = "Greet the call and ask who the candidate is, noting that someone is logged in as a generic hardware name."
            elif int_turns == 1:
                instruction = "Acknowledge the candidate's introduction. Ask them a technical software engineering question about their resume, experience, or React/FastAPI."
            elif int_turns == 2:
                instruction = "Acknowledge their answer. Ask them if they can share their screen to walk through a project or do a coding challenge."
            else:
                instruction = "Give a positive response and ask if they have any final questions about the role or company."
                
            return self._generate_llm_turn(
                "interviewer", speaker_name, 
                "candidate", self.candidate_name, 
                history, instruction
            )
        else: # candidate
            if cand_turns == 0:
                instruction = f"Introduce yourself as '{self.candidate_name}'. Explain politely that you are logged in as '{self.candidate_joined_name}' because of a device/profile default."
            elif cand_turns == 1:
                instruction = "Answer the interviewer's technical question. Mention candidate keyphrases like 'in my resume', 'my experience', or 'my previous role' and describe a concrete project or bug you fixed."
            elif cand_turns == 2:
                instruction = "Acknowledge the request to share your screen. Say that you are opening your IDE or terminal and starting the screen share now."
            else:
                instruction = "Answer politely and ask about team size or deployment schedules."
                
            return self._generate_llm_turn(
                "candidate", self.candidate_name, 
                "interviewer", self.current_interviewer, 
                history, instruction
            )
