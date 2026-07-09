# Sherlock Real-Time Candidate Identification System (SCI)

Sherlock is an AI platform designed to detect interview fraud in real time over virtual meeting systems (Google Meet, Microsoft Teams, Zoom). This repository contains a working prototype of the **Sherlock Candidate Identification System (SCI)**. 

SCI automatically identifies the candidate in a live virtual meeting, updates identification confidence dynamically as events occur, handles typos and generic device names, and explains why a participant was selected using a **Multi-Signal Bayesian Evidence Fusion Engine**.

---

## 🚀 How to Run the Prototype

The system is split into a **Python FastAPI Backend** (which runs the fusion logic) and a **React + TypeScript Frontend** (which simulates the meeting and displays the dashboard).

### Prerequisites
* **Python**: 3.10 or higher
* **Node.js**: v18 or higher & `npm`

---

### Step 1: Run the Python Backend
1. Open a terminal and navigate to the `backend/` folder:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\activate

   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   python main.py
   ```
   *The backend will start on [http://localhost:8000](http://localhost:8000) and establish a WebSocket listener on `/ws`.*

---

### Step 2: Run the React Frontend
1. Open a new terminal window and navigate to the `frontend/` folder:
   ```bash
   cd frontend
   ```
2. Install Node modules:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to the link printed in the terminal (usually [http://localhost:5173](http://localhost:5173)).

---

## 🛠️ System Architecture

SCI is built using **event-driven streaming**. Instead of polling, it processes meeting events (joins, speech activity, webcam changes, screensharing, live transcript lines) in real time over a WebSocket connection.

```
       +-----------------------------------------------------------------+
       |                       VIRTUAL MEETING CLIENT                    |
       |       (Ingests Speech Activity, Webcams, Transcripts, etc.)      |
       +-------------------------------+---------------------------------+
                                       | (Real-time Stream)
                                       v
                             +-------------------+
                             |  FastAPI WebSocket|
                             +---------+---------+
                                       |
                                       v
                         +---------------------------+
                         |    Fusion Ingestion API   |
                         +-------------+-------------+
                                       |
    +----------------------------------+------------------------------------+
    |                          FUSION ENGINE LAYER                          |
    |                                                                       |
    |  +--------------------+  +----------------------+  +---------------+  |
    |  | Name Similarity    |  | Acoustic Analyzer    |  | Turn-Taking   |  |
    |  | (Jaro-Winkler/J-W) |  | (Speaking Durations) |  | Graph Tracker |  |
    |  +---------+----------+  +----------+-----------+  +-------+-------+  |
    |            |                        |                      |          |
    |            +------------------+     |     +----------------+          |
    |                               |     |     |                           |
    |                               v     v     v                           |
    |                         +-----------------------+                     |
    |                         |  Weighted Evidence    |                     |
    |                         |  Accumulator Matrix   |                     |
    |                         +-----------+-----------+                     |
    |                                     |                                 |
    |                                     v                                 |
    |                         +-----------------------+                     |
    |                         |    Bayesian Belief    |                     |
    |                         |    Softmax Scaling    |                     |
    |                         +-----------+-----------+                     |
    |                                     |                                 |
    +-------------------------------------|---------------------------------+
                                          v
                              +-----------------------+
                              | Explainability Block  |
                              |  (LIME-like Weight    |
                              |   Signal Attribution) |
                              +-----------+-----------+
                                          |
                                          v (Update JSON Broadcast)
                              +-----------------------+
                              |   React UI Simulator  |
                              +-----------------------+
```

### Core Algorithms and Weak Signals

1. **Identity & Name Matcher (Jaro-Winkler Similarity)**:
   Matches the display name against expected metadata. Checks for typos, handles email prefixes, and blocks known interviewers (negative weight). It also filters generic devices (e.g., "MacBook Pro") to prevent false name match outputs.
2. **Behavioral Speech Ratio Classifier**:
   Calculates the candidate's talking duration ratio over the call. Peak candidate likelihood is mapped to a bell-shaped curve around $45\%$. A silent participant or a monologuer is penalized.
3. **Turn-Taking Interaction Graph**:
   Tracks turn dynamics (Speaker A $\rightarrow$ Speaker B). In standard interviews, the candidate has high interaction density with verified interviewers.
4. **Semantic Keyphrase Classifier (NLP)**:
   Scans the transcript stream for semantic candidate indicators (e.g., *"in my resume"*, *"my experience"*) vs interviewer indicators (e.g., *"tell me about"*, *"walk us through"*).
5. **Presence Actions**:
   Webcam status (+20% active, -10% inactive) and Screen Sharing (+100% active).

---

## 📈 Evaluation & Test Results

We verify the engine using our automated test suite under `backend/tests/test_fusion.py`. In addition, the frontend simulator runs the following 4 real-world test scenarios:

### Scenario 1: The "MacBook Pro" Candidate
* **Ambiguity**: Candidate joins as "MacBook Pro" with camera off.
* **Result**: Initially, confidence is 0% (generic name). Within 10 seconds of speech, the NLP classifier and turn graph detect candidate behavior. Confidence climbs to 58%. When they enable video and start screensharing, confidence hits **95%**, successfully overriding the default name.

### Scenario 2: Interviewer Typo
* **Ambiguity**: Recruiter logs candidate as "John Smith", but participant joins as "Johnathan Smith".
* **Result**: String similarity scores the name match at 78% (low positive). However, when the transcript NLP analyzer registers candidate markers and the turn graph maps high interaction with interviewers, confidence climbs to **88%**, successfully resolving the misspelling.

### Scenario 3: Mid-Interview Name Change
* **Ambiguity**: Candidate joins as "JD" (initials), and renames themselves to "Jane Doe" mid-call.
* **Result**: The engine tracks the participant's unique ID (`p_jd`). As they speak, confidence begins rising. The moment they change their display name to "Jane Doe", the name matcher score updates, and confidence jumps immediately to **94%**.

### Scenario 4: Silent Observers & Talkative HR
* **Ambiguity**: Recruiter speaks a lot explaining benefits; candidate is quiet initially; silent observer is present.
* **Result**: The recruiter is marked as a verified interviewer (from name metadata), giving them 0% candidate confidence. The silent observer speaks 0% of the time, keeping them at 0%. As soon as the candidate answers the coding question, the speaking ratio and NLP classifiers converge on them with **84%** confidence.

---

## 📝 Assumptions Made
1. **Data Accessibility**: The meeting integration layer (e.g., a WebRTC bridge or meeting bot) provides separate audio streams and speaker-attributed transcripts.
2. **Interviewer List**: Recruiter names and interviewer schedules are available in the candidate database metadata.
3. **Active webcam**: The candidate will turn on their webcam during the coding session.

---

## 🔮 Future Enhancements (What I'd build next)
1. **Biometric Face Verification**: Compare the candidate's active webcam frame with their photo from LinkedIn or resume using a Siamese neural network (Facenet) to prevent face-swapping deepfakes.
2. **Acoustic Voiceprints**: Generate a speaker embedding (d-vector) of the candidate's voice in the first 30 seconds, and flag if a different speaker embedding is detected on the candidate's audio track later (voice swapping detection).
3. **Local LLM Classifier**: Replace keyword matching with a local, quantized Llama-3-8B model to classify dialogue turns into Candidate/Interviewer roles with higher semantic accuracy.
