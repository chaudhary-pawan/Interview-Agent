import asyncio
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from engine.fusion_engine import FusionEngine
from engine.scenarios import SCENARIOS
from engine.conversation_generator import ConversationGenerator

app = FastAPI(
    title="Sherlock Candidate Identifier",
    description="Real-time multi-signal fusion engine for interview candidate identification."
)

# Allow CORS for React frontend (defaulting to localhost:5173 or other dev ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/scenarios")
async def get_scenarios():
    """
    Returns lists of available simulation scenarios and their metadata.
    """
    return [
        {
            "id": key,
            "title": val["title"],
            "description": val["description"],
            "metadata": val["metadata"]
        }
        for key, val in SCENARIOS.items()
    ]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scenario simulation control and streaming.
    """
    await websocket.accept()
    
    sim_task = None
    is_paused = False
    is_stopped = False
    speed = 1.0

    async def non_blocking_sleep(delay: float):
        nonlocal is_paused, is_stopped
        elapsed = 0.0
        while elapsed < delay:
            if is_stopped:
                break
            if is_paused:
                await asyncio.sleep(0.1)
                continue
            await asyncio.sleep(0.1)
            elapsed += 0.1

    async def simulation_runner(scenario_id: str):
        nonlocal is_paused, is_stopped, speed
        
        scenario = SCENARIOS.get(scenario_id)
        if not scenario:
            await websocket.send_json({"type": "error", "message": f"Scenario {scenario_id} not found."})
            return
            
        meta = scenario["metadata"]
        # Instantiate FusionEngine in pure Zero-Knowledge Mode (no name metadata matching)
        engine = FusionEngine(
            candidate_name=None,
            candidate_email=None,
            interviewer_names=[]
        )
        
        # Determine candidate initial display name for LLM setup
        joined_name = "MacBook Pro"
        if len(scenario["events"]) > 1:
            joined_name = scenario["events"][1].get("name", "MacBook Pro")
            
        generator = ConversationGenerator(
            candidate_name=meta["candidate_name"],
            candidate_joined_name=joined_name,
            interviewer_names=meta["interviewer_names"]
        )
        
        conversation_history = []
        
        events = scenario["events"]
        prev_time = 0
        
        for idx, event in enumerate(events):
            if is_stopped:
                break
                
            # Calculate duration to sleep
            delay = (event["time"] - prev_time) / speed
            prev_time = event["time"]
            
            # Non-blocking check for pauses
            await non_blocking_sleep(delay)
                
            if is_stopped:
                break
                
            # Apply the event to our fusion engine
            etype = event["type"]
            epid = event["id"]
            
            event_desc = ""
            text = event.get("text", "")
            
            # Generate transcript line dynamically if tag is present
            if etype == "transcript" and "generate_role" in event:
                role = event["generate_role"]
                speaker_name = engine.participants.get(epid, {}).get("display_name", epid)
                
                # Fetch dynamically from generator
                text = generator.generate_turn(epid, speaker_name, role, conversation_history)
                
                conversation_history.append({
                    "speaker": speaker_name,
                    "text": text,
                    "role": role
                })
            
            if etype == "join":
                engine.handle_join(epid, event["name"], join_time=event["time"])
                event_desc = f"Participant '{event['name']}' joined the meeting."
            elif etype == "leave":
                pname = engine.participants.get(epid, {}).get("display_name", epid)
                engine.handle_leave(epid)
                event_desc = f"Participant '{pname}' left the meeting."
            elif etype == "rename":
                old_name = engine.participants.get(epid, {}).get("display_name", epid)
                engine.handle_name_change(epid, event["name"])
                event_desc = f"Participant '{old_name}' renamed to '{event['name']}'."
            elif etype == "webcam":
                pname = engine.participants.get(epid, {}).get("display_name", epid)
                engine.handle_webcam(epid, event["is_on"])
                action = "enabled" if event["is_on"] else "disabled"
                event_desc = f"Participant '{pname}' {action} their webcam."
            elif etype == "screenshare":
                pname = engine.participants.get(epid, {}).get("display_name", epid)
                engine.handle_screen_share(epid, event["is_on"])
                action = "started" if event["is_on"] else "stopped"
                event_desc = f"Participant '{pname}' {action} screen sharing."
            elif etype == "speaking":
                pname = engine.participants.get(epid, {}).get("display_name", epid)
                engine.handle_speaking(epid, event["duration"])
                event_desc = f"Active speech from '{pname}' ({event['duration']} seconds)."
            elif etype == "transcript":
                pname = engine.participants.get(epid, {}).get("display_name", epid)
                engine.handle_transcript(epid, text)
                event_desc = f"Transcript segment received from '{pname}'."

            # Re-calculate confidence scores
            engine.recalculate()
            status = engine.get_candidate_status()
            
            # Broadcast the state change to the UI
            await websocket.send_json({
                "type": "update",
                "step": idx,
                "total_steps": len(events),
                "current_time": event["time"],
                "event": {
                    "type": etype,
                    "id": epid,
                    "name": engine.participants.get(epid, {}).get("display_name", epid),
                    "description": event_desc,
                    "text": text
                },
                "status": status
            })
            
        # After static setup events are completed, keep the Q&A conversation going indefinitely!
        if not is_stopped:
            # Alternate speaker roles
            # Let's find the active candidate and interviewer IDs present
            candidate_id = "p_macbook"
            for p in engine.participants.values():
                if p["is_present"] and p["id"] not in engine.verified_interviewers and "otter" not in p["display_name"].lower() and "observer" not in p["display_name"].lower():
                    candidate_id = p["id"]
                    break
                    
            interviewer_id = list(engine.verified_interviewers)[0] if engine.verified_interviewers else "p_sarah"
            
            current_speaker_id = candidate_id
            current_speaker_role = "candidate"
            
            step_idx = len(events)
            
            while not is_stopped:
                # Toggle speaker
                if current_speaker_id == candidate_id:
                    current_speaker_id = interviewer_id
                    current_speaker_role = "interviewer"
                else:
                    current_speaker_id = candidate_id
                    current_speaker_role = "candidate"
                    
                speaker_name = engine.participants.get(current_speaker_id, {}).get("display_name", current_speaker_id)
                
                # Sleep between turns (4 seconds to simulate natural speaking)
                delay = 4.0 / speed
                await non_blocking_sleep(delay)
                    
                if is_stopped:
                    break
                    
                # Generate next turn
                text = generator.generate_turn(
                    current_speaker_id,
                    speaker_name,
                    current_speaker_role,
                    conversation_history
                )
                
                if text == "Meeting has ended.":
                    break
                
                conversation_history.append({
                    "speaker": speaker_name,
                    "text": text,
                    "role": current_speaker_role
                })
                
                # Update engine
                # Estimate speaking duration
                dur = max(2.0, min(10.0, len(text.split()) / 3.0))
                engine.handle_speaking(current_speaker_id, dur)
                engine.handle_transcript(current_speaker_id, text)
                engine.recalculate()
                status = engine.get_candidate_status()
                
                # Broadcast turn to UI
                await websocket.send_json({
                    "type": "update",
                    "step": step_idx,
                    "total_steps": step_idx + 10, # dynamic progress display
                    "current_time": prev_time + int(dur),
                    "event": {
                        "type": "transcript",
                        "id": current_speaker_id,
                        "name": speaker_name,
                        "description": f"Live transcript received from '{speaker_name}'.",
                        "text": text
                    },
                    "status": status
                })
                
                prev_time += int(dur)
                step_idx += 1
                
        if not is_stopped:
            await websocket.send_json({"type": "complete"})

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")
            
            if action == "start":
                # Clear running task if any
                if sim_task and not sim_task.done():
                    is_stopped = True
                    sim_task.cancel()
                    try:
                        await sim_task
                    except asyncio.CancelledError:
                        pass
                
                is_paused = False
                is_stopped = False
                speed = float(msg.get("speed", 1.0))
                scenario_id = msg.get("scenario_id")
                
                sim_task = asyncio.create_task(simulation_runner(scenario_id))
                await websocket.send_json({"type": "state", "playing": True})
                
            elif action == "pause":
                is_paused = True
                await websocket.send_json({"type": "state", "paused": True})
                
            elif action == "resume":
                is_paused = False
                await websocket.send_json({"type": "state", "paused": False})
                
            elif action == "stop":
                is_stopped = True
                if sim_task and not sim_task.done():
                    sim_task.cancel()
                await websocket.send_json({"type": "state", "stopped": True})
                
    except WebSocketDisconnect:
        is_stopped = True
        if sim_task and not sim_task.done():
            sim_task.cancel()
        print("WebSocket disconnected")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
