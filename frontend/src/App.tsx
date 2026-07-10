import { useState, useEffect, useRef, useMemo } from "react";
import { 
  Play, Pause, Square, Zap, Users, Video, VideoOff, 
  Monitor, MessageSquare, HelpCircle, ShieldCheck, 
  Activity, Award
} from "lucide-react";


interface ParticipantSignal {
  score: number;
  weight: number;
  weighted: number;
  reason: string;
}

interface Participant {
  id: string;
  display_name: string;
  webcam_on: boolean;
  screen_share_on: boolean;
  is_present: boolean;
  confidence: number;
  signals: Record<string, ParticipantSignal>;
  explanation: string;
  role: "interviewer" | "observer" | "candidate" | "unknown";
}


interface EventLog {
  type: string;
  id: string;
  name: string;
  description: string;
  text: string;
}

interface EngineStatus {
  candidate_identified: boolean;
  candidate_id: string | null;
  confidence: number;
  explanation: string;
  participants: Participant[];
}

interface TimelinePoint {
  time: number;
  confidences: Record<string, number>;
}

export default function App() {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>("scenario_1");
  const [speed, setSpeed] = useState<number>(1.0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  const [selectedParticipantId, setSelectedParticipantId] = useState<string | null>(null);
  const [showHowItWorks, setShowHowItWorks] = useState<boolean>(false);
  
  // Real-time states from backend
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [totalSteps, setTotalSteps] = useState<number>(0);
  const [currentEvent, setCurrentEvent] = useState<EventLog | null>(null);
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [eventLogs, setEventLogs] = useState<EventLog[]>([]);
  const [transcripts, setTranscripts] = useState<{ speaker: string; text: string; role: "candidate" | "interviewer" | "neutral" }[]>([]);
  const [timelineData, setTimelineData] = useState<TimelinePoint[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const eventFeedEndRef = useRef<HTMLDivElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    connectWS();
    fetchScenarios();
    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  // Scroll to bottom helper
  useEffect(() => {
    eventFeedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [eventLogs]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  const fetchScenarios = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/scenarios");
      const data = await res.json();
      setScenarios(data);
      if (data.length > 0) {
        setSelectedScenario(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch scenarios:", err);
    }
  };

  const connectWS = () => {
    setWsStatus("connecting");
    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onopen = () => {
      setWsStatus("connected");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.type === "state") {
        if (msg.playing) {
          setIsPlaying(true);
          setIsPaused(false);
        }
        if (msg.paused) setIsPaused(true);
        if (msg.paused === false) setIsPaused(false);
        if (msg.stopped) {
          setIsPlaying(false);
          setIsPaused(false);
        }
      } else if (msg.type === "update") {
        setCurrentTime(msg.current_time);
        setCurrentStep(msg.step + 1);
        setTotalSteps(msg.total_steps);
        
        // Log event
        const newEvent = msg.event;
        setCurrentEvent(newEvent);
        setEventLogs(prev => [...prev, newEvent]);

        // Add transcript if available
        if (newEvent.type === "transcript") {
          const textLower = newEvent.text.toLowerCase();
          let role: "candidate" | "interviewer" | "neutral" = "neutral";
          
          // Classify role locally for styling highlight tags
          if (textLower.includes("my resume") || textLower.includes("my experience") || textLower.includes("i worked at")) {
            role = "candidate";
          } else if (textLower.includes("tell me about") || textLower.includes("can you explain") || textLower.includes("we are looking for")) {
            role = "interviewer";
          }
          
          setTranscripts(prev => [...prev, { speaker: newEvent.name, text: newEvent.text, role }]);
        }

        // Update engine status
        setEngineStatus(msg.status);

        // Record timeline point
        const confs: Record<string, number> = {};
        msg.status.participants.forEach((p: Participant) => {
          confs[p.id] = p.confidence;
        });
        setTimelineData(prev => [...prev, { time: msg.current_time, confidences: confs }]);

      } else if (msg.type === "complete") {
        setIsPlaying(false);
        setIsPaused(false);
      } else if (msg.type === "error") {
        alert(msg.message);
      }
    };

    ws.onclose = () => {
      setWsStatus("disconnected");
      // Auto-reconnect after 3 seconds
      setTimeout(connectWS, 3000);
    };

    socketRef.current = ws;
  };

  const startSimulation = () => {
    if (!socketRef.current || wsStatus !== "connected") return;
    
    // Clear logs
    setEventLogs([]);
    setTranscripts([]);
    setTimelineData([]);
    setCurrentTime(0);
    setCurrentEvent(null);
    setSelectedParticipantId(null);
    
    socketRef.current.send(JSON.stringify({
      action: "start",
      scenario_id: selectedScenario,
      speed: speed
    }));
    setIsPlaying(true);
    setIsPaused(false);
  };

  const pauseSimulation = () => {
    if (!socketRef.current) return;
    socketRef.current.send(JSON.stringify({ action: "pause" }));
    setIsPaused(true);
  };

  const resumeSimulation = () => {
    if (!socketRef.current) return;
    socketRef.current.send(JSON.stringify({ action: "resume" }));
    setIsPaused(false);
  };

  const stopSimulation = () => {
    if (!socketRef.current) return;
    socketRef.current.send(JSON.stringify({ action: "stop" }));
    setIsPlaying(false);
    setIsPaused(false);
  };

  // Find details of selected scenario metadata
  const currentScenarioMeta = scenarios.find(s => s.id === selectedScenario);

  // SVG Dimension for Sparklines
  const sparkWidth = 450;
  const sparkHeight = 120;

  // Calculate coordinates for SVGs
  const getSparklinePath = (participantId: string) => {
    if (timelineData.length < 2) return "";
    
    const times = timelineData.map(d => d.time);
    const maxTime = Math.max(...times, 60); // min 60s scale

    return timelineData.map((d, idx) => {
      const x = (d.time / maxTime) * (sparkWidth - 40) + 20;
      const confidence = d.confidences[participantId] || 0.0;
      const y = sparkHeight - (confidence * (sparkHeight - 30) + 15);
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(" ");
  };

  // Circular graph positions for turn-taking
  const participantPositions = useMemo(() => {
    if (!engineStatus) return [];
    const count = engineStatus.participants.length;
    const center = 100;
    const radius = 60;
    return engineStatus.participants.map((p, idx) => {
      const angle = (idx * 2 * Math.PI) / count - Math.PI / 2;
      return {
        id: p.id,
        name: p.display_name,
        x: center + radius * Math.cos(angle),
        y: center + radius * Math.sin(angle),
        is_candidate: p.id === engineStatus.candidate_id,
        is_interviewer: p.role === "interviewer"
      };
    });
  }, [engineStatus]);

  // Helper to color confidence
  const getConfidenceColor = (conf: number) => {
    if (conf > 0.7) return "var(--accent-emerald)";
    if (conf > 0.3) return "var(--accent-amber)";
    return "var(--text-muted)";
  };

  const getConfBg = (conf: number) => {
    if (conf > 0.7) return "rgba(16, 185, 129, 0.15)";
    if (conf > 0.3) return "rgba(245, 158, 11, 0.15)";
    return "rgba(255, 255, 255, 0.03)";
  };

  const activeCandidate = engineStatus?.participants.find(p => p.id === engineStatus.candidate_id);

  // Get currently inspected participant (clicked one, or top confidence one, or null)
  const getInspectedParticipant = (): Participant | null => {
    if (!engineStatus || engineStatus.participants.length === 0) return null;
    if (selectedParticipantId) {
      const found = engineStatus.participants.find(p => p.id === selectedParticipantId);
      if (found && found.is_present) return found;
    }
    // Default to the one with the highest confidence
    return engineStatus.participants.reduce((prev, current) => 
      (prev.confidence > current.confidence) ? prev : current
    , engineStatus.participants[0]);
  };

  const inspectedParticipant = getInspectedParticipant();

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", padding: "16px 24px" }}>
      
      {/* HEADER SECTION */}
      <header className="glass-panel" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div className="flex-center" style={{ width: "40px", height: "40px", borderRadius: "8px", background: "linear-gradient(135deg, var(--accent-purple), var(--accent-emerald))" }}>
            <ShieldCheck size={24} color="#FFF" />
          </div>
          <div>
            <h1 style={{ fontSize: "20px", fontWeight: "700", letterSpacing: "-0.5px" }}>SHERLOCK</h1>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "500" }}>Live Candidate Identification System</span>
          </div>
        </div>

        {/* CONNECTION STATUS */}
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          
          {/* HOW IT WORKS BUTTON */}
          <button 
            onClick={() => setShowHowItWorks(prev => !prev)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "6px",
              border: showHowItWorks ? "1px solid var(--accent-purple)" : "1px solid var(--border-subtle)",
              backgroundColor: showHowItWorks ? "rgba(139, 92, 246, 0.15)" : "rgba(255,255,255,0.03)",
              color: showHowItWorks ? "var(--text-primary)" : "var(--text-secondary)",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
          >
            <HelpCircle size={14} /> How it works
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ 
              width: "8px", 
              height: "8px", 
              borderRadius: "50%", 
              backgroundColor: wsStatus === "connected" ? "var(--accent-emerald)" : wsStatus === "connecting" ? "var(--accent-amber)" : "var(--accent-rose)",
              boxShadow: wsStatus === "connected" ? "0 0 8px var(--accent-emerald)" : "none"
            }} />
            <span style={{ fontSize: "13px", fontWeight: "500", color: "var(--text-secondary)" }}>
              {wsStatus === "connected" ? "Websocket Active" : wsStatus === "connecting" ? "Connecting to Engine..." : "Engine Offline"}
            </span>
          </div>
        </div>
      </header>

      {/* HOW IT WORKS DROPDOWN CARD */}
      {showHowItWorks && (
        <section className="glass-panel" style={{ padding: "24px", marginBottom: "20px", border: "1px solid var(--accent-purple-glow)", background: "rgba(139, 92, 246, 0.03)" }}>
          <h2 style={{ fontSize: "16px", fontWeight: "700", color: "var(--accent-purple)", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
            <HelpCircle size={18} /> How Sherlock Candidate Identification System (SCI) Works
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.5" }}>
            Sherlock is a multi-signal Bayesian evidence fusion system designed to identify the correct candidate in virtual meetings (even under adversarial conditions such as typos, generic device profiles, panel interviewers, or nickname masks). Here are the simple steps of how the system works:
          </p>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "20px" }}>
            
            <div style={{ backgroundColor: "rgba(0,0,0,0.15)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--accent-purple)", marginBottom: "8px", letterSpacing: "1px" }}>Step 1: Multi-Signal Ingestion</div>
              <h3 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", marginBottom: "6px" }}>1. Listen to Stream Signals</h3>
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                As the meeting runs, Sherlock listens to 6 different "weak signals": join timing, display name spelling, active webcam/screensharing states, speech ratio, turn dynamics (who speaks next), and spoken transcript keyphrases.
              </p>
            </div>
            
            <div style={{ backgroundColor: "rgba(0,0,0,0.15)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--accent-purple)", marginBottom: "8px", letterSpacing: "1px" }}>Step 2: Bayesian Evidence Fusion</div>
              <h3 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", marginBottom: "6px" }}>2. Calculate & Shift Probabilities</h3>
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                The engine fuses these sub-signals mathematically using a Bayesian belief Softmax model. Positive matches (like screensharing or saying "my resume") boost confidence, while negative indicators (like silent observers or matching interviewer blocklists) push confidence to zero.
              </p>
            </div>
            
            <div style={{ backgroundColor: "rgba(0,0,0,0.15)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--accent-purple)", marginBottom: "8px", letterSpacing: "1px" }}>Step 3: Continuous Learning</div>
              <h3 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", marginBottom: "6px" }}>3. Dynamic Feedback Loop</h3>
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                The dashboard renders real-time explainability verdicts, weak signal charts, and a conversational graph. When the interview ends, correct/incorrect selections update the engine's learning weights so the model improves dynamically over time.
              </p>
            </div>
            
          </div>
        </section>
      )}

      {/* CONTROLS SECTION */}
      <section className="glass-panel" style={{ padding: "20px", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "4px" }}>
          SIMULATION CONTROL PANEL
        </h2>
        <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "16px", lineHeight: "1.3" }}>
          Select a pre-configured meeting scenario, configure the simulation speed, and use the controls to start, pause, or stop the real-time feed.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          
          {/* SCENARIO CHOICE */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "1px" }}>Select Meeting Scenario</label>
            <select 
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              disabled={isPlaying}
              style={{ 
                padding: "8px 12px", 
                borderRadius: "6px", 
                backgroundColor: "rgba(255,255,255,0.05)", 
                border: "1px solid var(--border-subtle)", 
                color: "var(--text-primary)",
                fontSize: "14px",
                outline: "none",
                cursor: "pointer"
              }}
            >
              {scenarios.map(s => (
                <option 
                  key={s.id} 
                  value={s.id}
                  style={{ 
                    backgroundColor: "#1c1926", 
                    color: "var(--text-primary)" 
                  }}
                >
                  {s.title}
                </option>
              ))}
            </select>
          </div>

          {/* SIMULATION SPEED */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "1px" }}>Simulation Speed</label>
            <div style={{ display: "flex", gap: "4px", backgroundColor: "rgba(255,255,255,0.03)", padding: "4px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
              {[1.0, 2.0, 5.0].map(s => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  disabled={isPlaying}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    border: "none",
                    background: speed === s ? "var(--accent-purple)" : "transparent",
                    color: speed === s ? "#FFF" : "var(--text-secondary)",
                    cursor: isPlaying ? "not-allowed" : "pointer",
                    fontSize: "12px",
                    fontWeight: "600",
                    transition: "all 0.2s"
                  }}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>

          {/* SIMULATION PROGRESS STEP */}
          {isPlaying && (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "1px" }}>Progress</label>
              <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--accent-purple)" }}>
                Step {currentStep} / {totalSteps}
              </span>
            </div>
          )}

          {/* PLAYBACK ACTION BUTTONS */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", alignSelf: "flex-end" }}>
            {!isPlaying ? (
              <button 
                onClick={startSimulation}
                disabled={wsStatus !== "connected"}
                style={{ 
                  display: "flex", 
                  alignItems: "center", 
                  gap: "8px", 
                  padding: "10px 20px", 
                  borderRadius: "8px", 
                  border: "none", 
                  backgroundColor: "var(--accent-purple)", 
                  color: "#FFF", 
                  cursor: "pointer", 
                  fontWeight: "600",
                  boxShadow: "0 4px 12px rgba(124, 58, 237, 0.3)"
                }}
              >
                <Play size={16} /> Start Simulation
              </button>
            ) : (
              <>
                {isPaused ? (
                  <button 
                    onClick={resumeSimulation}
                    style={{ 
                      display: "flex", 
                      alignItems: "center", 
                      gap: "8px", 
                      padding: "10px 18px", 
                      borderRadius: "8px", 
                      border: "1px solid var(--accent-purple)", 
                      backgroundColor: "rgba(124, 58, 237, 0.1)", 
                      color: "var(--accent-purple)", 
                      cursor: "pointer", 
                      fontWeight: "600"
                    }}
                  >
                    <Play size={16} /> Resume
                  </button>
                ) : (
                  <button 
                    onClick={pauseSimulation}
                    style={{ 
                      display: "flex", 
                      alignItems: "center", 
                      gap: "8px", 
                      padding: "10px 18px", 
                      borderRadius: "8px", 
                      border: "1px solid rgba(255,255,255,0.2)", 
                      backgroundColor: "rgba(255,255,255,0.05)", 
                      color: "var(--text-primary)", 
                      cursor: "pointer", 
                      fontWeight: "600"
                    }}
                  >
                    <Pause size={16} /> Pause
                  </button>
                )}

                <button 
                  onClick={stopSimulation}
                  style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    gap: "8px", 
                    padding: "10px 18px", 
                    borderRadius: "8px", 
                    border: "none", 
                    backgroundColor: "var(--accent-rose)", 
                    color: "#FFF", 
                    cursor: "pointer", 
                    fontWeight: "600"
                  }}
                >
                  <Square size={16} fill="#FFF" /> Stop
                </button>
              </>
            )}
          </div>

        </div>

        {/* CURRENT SCENARIO DESCRIPTION */}
        {currentScenarioMeta && (
          <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)", fontSize: "14px" }}>
            <span style={{ color: "var(--text-muted)", fontSize: "12px", display: "block", marginBottom: "4px" }}>SCENARIO DESCRIPTION</span>
            <p style={{ color: "var(--text-secondary)", lineHeight: "1.4" }}>{currentScenarioMeta.description}</p>
          </div>
        )}
      </section>

      {/* DASHBOARD COLUMNS */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.2fr 1.6fr", gap: "20px", flex: 1, minHeight: "650px" }}>

        {/* COLUMN 1: LIVE MEETING PARTICIPANTS & EVENTS */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          
          {/* WEBCAM GALLERY */}
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", flex: 1.2 }}>
            <h2 style={{ fontSize: "14px", fontWeight: "600", letterSpacing: "0.5px", color: "var(--text-secondary)", marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Video size={16} /> LIVE MEETING GALLERY
            </h2>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "16px", lineHeight: "1.3" }}>
              Displays active meeting participants, their webcam/screenshare states, and their calculated candidate likelihood percentage.
            </p>
            
            {engineStatus && engineStatus.participants.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", flex: 1 }}>
                {engineStatus.participants.map((p) => {
                  const isCandidate = p.id === engineStatus.candidate_id;
                  const isSpeaking = currentEvent?.type === "speaking" && currentEvent.id === p.id;
                  const isInspected = inspectedParticipant?.id === p.id;
                  
                  return (
                    <div 
                      key={p.id} 
                      onClick={() => setSelectedParticipantId(p.id)}
                      className={`glass-card ${isCandidate ? 'glow-active' : ''}`}
                      style={{ 
                        display: "flex", 
                        flexDirection: "column", 
                        position: "relative",
                        overflow: "hidden",
                        borderWidth: "1.5px",
                        background: getConfBg(p.confidence),
                        cursor: "pointer",
                        borderColor: isInspected 
                          ? "var(--accent-purple)" 
                          : isCandidate 
                          ? "var(--accent-purple-glow)" 
                          : "rgba(255, 255, 255, 0.08)",
                        boxShadow: isInspected ? "0 0 10px rgba(139, 92, 246, 0.25)" : "none"
                      }}
                    >
                      {/* Avatar Simulation */}
                      <div 
                        style={{ 
                          height: "90px", 
                          backgroundColor: "rgba(0,0,0,0.25)", 
                          borderRadius: "6px", 
                          display: "flex", 
                          alignItems: "center", 
                          justifyContent: "center",
                          position: "relative",
                          border: isSpeaking ? "1.5px solid var(--accent-emerald)" : "1px solid transparent"
                        }}
                      >
                        {/* Audio Speaking Ripple */}
                        {isSpeaking && (
                          <div className="speaking-indicator" style={{ width: "12px", height: "12px", borderRadius: "50%", position: "absolute", top: "10px", left: "10px" }} />
                        )}

                        <div style={{ fontSize: "28px", fontWeight: "700", color: isCandidate ? "var(--accent-purple)" : "var(--text-secondary)" }}>
                          {p.display_name.substring(0, 2).toUpperCase()}
                        </div>

                        {/* Webcam state icon */}
                        <div style={{ position: "absolute", bottom: "8px", left: "8px", display: "flex", gap: "6px" }}>
                          {p.webcam_on ? (
                            <Video size={12} color="var(--accent-emerald)" />
                          ) : (
                            <VideoOff size={12} color="var(--accent-rose)" />
                          )}
                          {p.screen_share_on && (
                            <Monitor size={12} className="speaking-indicator" style={{ backgroundColor: "transparent", color: "var(--accent-emerald)" }} />
                          )}
                        </div>

                        {/* Live Confidence Overlay */}
                        <div style={{ 
                          position: "absolute", 
                          top: "8px", 
                          right: "8px", 
                          backgroundColor: "rgba(0,0,0,0.6)",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: "700",
                          color: getConfidenceColor(p.confidence),
                          border: `1px solid ${getConfidenceColor(p.confidence)}`
                        }}>
                          {Math.round(p.confidence * 100)}%
                        </div>
                      </div>

                      {/* Info Panel */}
                      <div style={{ marginTop: "10px" }}>
                        <div style={{ fontWeight: "600", fontSize: "13px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {p.display_name}
                        </div>
                         <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                          Role: {
                            p.role === "interviewer" 
                              ? "Interviewer" 
                              : p.role === "candidate" 
                              ? "Identified Candidate" 
                              : p.role === "observer" 
                              ? "Observer/Bot" 
                              : "External Participant"
                          }
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", color: "var(--text-muted)", border: "1px dashed var(--border-subtle)", borderRadius: "8px" }}>
                <Users size={32} style={{ marginBottom: "8px" }} />
                <span>No participants connected yet.</span>
                <span style={{ fontSize: "11px" }}>Launch the simulation to connect.</span>
              </div>
            )}
          </div>

          {/* SIMULATED SYSTEM LIVE LOGS */}
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", flex: 1 }}>
            <h2 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Activity size={16} /> LIVE INGESTION LOGS
            </h2>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "12px", lineHeight: "1.3" }}>
              A real-time stream of raw event signals (joins, screen sharing, webcam state changes) emitted by meeting participants.
            </p>
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px", maxHeight: "250px" }}>
              {eventLogs.length > 0 ? (
                eventLogs.map((log, idx) => (
                  <div key={idx} style={{ fontSize: "12px", padding: "8px 10px", borderRadius: "6px", backgroundColor: "rgba(0,0,0,0.15)", borderLeft: `3px solid ${log.type === 'join' ? 'var(--accent-emerald)' : log.type === 'leave' ? 'var(--accent-rose)' : 'var(--accent-purple)'}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
                      <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>{log.type.toUpperCase()}</span>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{log.name}</span>
                    </div>
                    <p style={{ color: "var(--text-secondary)" }}>{log.description}</p>
                  </div>
                ))
              ) : (
                <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", color: "var(--text-muted)", fontSize: "12px" }}>
                  Awaiting ingestion feed...
                </div>
              )}
              <div ref={eventFeedEndRef} />
            </div>
          </div>
        </div>

        {/* COLUMN 2: SIGNAL ANALYSIS & EXPLAINABILITY */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          
          {/* TOP DETECTED CANDIDATE SUMMARY */}
          <div className="glass-panel animate-glow" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Award size={16} /> DETECTED CANDIDATE
            </h2>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "10px", lineHeight: "1.3" }}>
              The participant identified as the candidate by the Bayesian fusion engine, along with the automated reasoning verdict.
            </p>

            {engineStatus && engineStatus.candidate_identified && activeCandidate ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                
                {/* Confidence Big Banner */}
                <div style={{ display: "flex", alignItems: "center", gap: "16px", padding: "12px 16px", borderRadius: "8px", backgroundColor: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                  <div style={{ fontSize: "36px", fontWeight: "800", color: "var(--accent-emerald)", lineHeight: 1 }}>
                    {Math.round(engineStatus.confidence * 100)}%
                  </div>
                  <div>
                    <div style={{ fontSize: "15px", fontWeight: "700" }}>{activeCandidate.display_name}</div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>CONFIDENCE SCORE</div>
                  </div>
                </div>

                {/* Explainability natural text */}
                <div style={{ fontSize: "13px", padding: "12px", borderRadius: "6px", backgroundColor: "rgba(255,255,255,0.03)", border: "1px solid var(--border-subtle)" }}>
                  <span style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase", marginBottom: "6px" }}>Reasoning Verdict</span>
                  <p style={{ color: "var(--text-secondary)", lineHeight: "1.4", whiteSpace: "pre-line" }}>{engineStatus.explanation}</p>
                </div>
              </div>
            ) : (
              <div style={{ padding: "24px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", border: "1px dashed var(--border-subtle)", borderRadius: "8px", color: "var(--text-muted)", textAlign: "center" }}>
                <HelpCircle size={32} style={{ marginBottom: "8px" }} />
                <span style={{ fontSize: "13px", fontWeight: "600" }}>No Candidate Confirmed Yet</span>
                <span style={{ fontSize: "11px", marginTop: "4px" }}>
                  {engineStatus?.explanation || "Awaiting signals... Start the interview simulation."}
                </span>
              </div>
            )}
          </div>

          {/* SIGNAL CONTRIBUTION BREAKDOWN */}
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", flex: 1 }}>
            <h2 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Zap size={16} /> WEAK SIGNAL WEIGHTS & SCORES {inspectedParticipant ? `(${inspectedParticipant.display_name})` : ""}
            </h2>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "16px", lineHeight: "1.3" }}>
              Detailed scoring breakdown of individual behavioral metrics (talking ratio, conversational graph, keyword match, presence markers) for the selected participant.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px", flex: 1, justifyContent: "space-around" }}>
              {engineStatus && inspectedParticipant && inspectedParticipant.signals && Object.keys(inspectedParticipant.signals).length > 0 ? (
                Object.entries(inspectedParticipant.signals).map(([sigName, sigData]) => {
                  const scorePercent = Math.max(-100, Math.min(100, sigData.score * 100));
                  const isPositive = sigData.score >= 0;
                  
                  return (
                    <div key={sigName} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                        <span style={{ fontWeight: "600", textTransform: "capitalize", color: "var(--text-primary)" }}>{sigName} Analysis</span>
                        <span style={{ color: getConfidenceColor(Math.abs(sigData.score)) }}>
                          Score: {isPositive ? "+" : ""}{Math.round(scorePercent)}% (wt: {Math.round(sigData.weight * 100)}%)
                        </span>
                      </div>
                      
                      {/* Bidirectional Bar */}
                      <div style={{ height: "6px", backgroundColor: "rgba(255,255,255,0.05)", borderRadius: "3px", position: "relative", overflow: "hidden" }}>
                        <div 
                          style={{ 
                            position: "absolute",
                            top: 0,
                            bottom: 0,
                            left: isPositive ? "50%" : `${50 + (scorePercent / 2)}%`,
                            width: `${Math.abs(scorePercent) / 2}%`,
                            backgroundColor: isPositive ? "var(--accent-emerald)" : "var(--accent-rose)",
                            borderRadius: "3px"
                          }}
                        />
                      </div>
                      <span style={{ fontSize: "10.5px", color: "var(--text-muted)", fontStyle: "italic", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {sigData.reason}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div style={{ display: "flex", justifyContent: "center", alignItems: "center", color: "var(--text-muted)", fontSize: "12px", height: "100%" }}>
                  Awaiting signals... Start the interview simulation.
                </div>
              )}
            </div>
          </div>

        </div>

        {/* COLUMN 3: GRAPH & TIMELINE & TRANSCRIPTS */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          
          {/* TURN TAKING GRAPH & TIMELINE TABS */}
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", height: "320px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Activity size={16} /> CONVERSATION ANALYSIS
            </h2>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "10px", lineHeight: "1.3" }}>
              Visualizes who is interacting with whom (turn-taking graph) and how the engine's confidence curves evolve over time.
            </p>

            <div style={{ display: "flex", flex: 1, gap: "10px", alignItems: "center" }}>
              
              {/* Circular Network Turn taking Graph */}
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", fontWeight: "600" }}>Turn-Taking Graph</span>
                <div style={{ width: "200px", height: "200px", position: "relative" }}>
                  <svg width="200" height="200">
                    {/* Draw links */}
                    {engineStatus && participantPositions.map((posFrom) => {
                      return participantPositions.map((posTo) => {
                        if (posFrom.id === posTo.id) return null;
                        
                        // Fake visual line thickness for turn graph
                        const isInteracting = (posFrom.is_candidate && posTo.is_interviewer) || (posFrom.is_interviewer && posTo.is_candidate);
                        return (
                          <line 
                            key={`${posFrom.id}-${posTo.id}`}
                            x1={posFrom.x}
                            y1={posFrom.y}
                            x2={posTo.x}
                            y2={posTo.y}
                            stroke={isInteracting ? "var(--accent-purple)" : "rgba(255,255,255,0.05)"}
                            strokeWidth={isInteracting ? 2 : 0.5}
                            strokeDasharray={isInteracting ? "0" : "2,2"}
                          />
                        );
                      });
                    })}

                    {/* Draw nodes */}
                    {engineStatus && participantPositions.map((pos) => (
                      <g key={pos.id}>
                        <circle 
                          cx={pos.x} 
                          cy={pos.y} 
                          r={10} 
                          fill={pos.is_candidate ? "var(--accent-purple)" : pos.is_interviewer ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.05)"}
                          stroke={pos.is_candidate ? "var(--accent-purple-glow)" : "rgba(255,255,255,0.1)"}
                          strokeWidth={pos.is_candidate ? 4 : 1}
                        />
                        <text 
                          x={pos.x} 
                          y={pos.y - 14} 
                          fontSize="9px" 
                          fill="var(--text-secondary)" 
                          textAnchor="middle"
                          fontWeight="700"
                        >
                          {pos.name.substring(0, 8)}
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
              </div>

              {/* Real-time sparkline curves */}
              <div style={{ flex: 1.2, display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", fontWeight: "600" }}>Confidence Timeline</span>
                <div style={{ width: "100%", height: "200px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {timelineData.length > 0 && engineStatus ? (
                    <svg viewBox={`0 0 ${sparkWidth} ${sparkHeight}`} style={{ width: "100%", height: "100%" }}>
                      {/* Grid background */}
                      <line x1="20" y1="15" x2={sparkWidth - 20} y2="15" stroke="rgba(255,255,255,0.05)" />
                      <line x1="20" y1={sparkHeight / 2} x2={sparkWidth - 20} y2={sparkHeight / 2} stroke="rgba(255,255,255,0.03)" />
                      <line x1="20" y1={sparkHeight - 15} x2={sparkWidth - 20} y2={sparkHeight - 15} stroke="rgba(255,255,255,0.1)" />
                      
                      {/* Lines for each participant */}
                      {engineStatus.participants.map((p) => {
                        const path = getSparklinePath(p.id);
                        if (!path) return null;
                        const isCand = p.id === engineStatus.candidate_id;
                        return (
                          <path 
                            key={p.id}
                            d={path}
                            fill="none"
                            stroke={isCand ? "var(--accent-purple)" : "rgba(255,255,255,0.2)"}
                            strokeWidth={isCand ? 2.5 : 1}
                            strokeDasharray={isCand ? "0" : "3,3"}
                          />
                        );
                      })}
                      
                      {/* Axis label */}
                      <text x="20" y={sparkHeight - 2} fontSize="9px" fill="var(--text-muted)">0s</text>
                      <text x={sparkWidth - 30} y={sparkHeight - 2} fontSize="9px" fill="var(--text-muted)">{currentTime}s</text>
                    </svg>
                  ) : (
                    <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>Timeline updates dynamically...</div>
                  )}
                </div>
              </div>

            </div>
          </div>

          {/* TRANSCRIPT DIALOGUE FEED */}
          <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", flex: 1 }}>
            <h2 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
              <MessageSquare size={16} /> LIVE MEET TRANSCRIPT
            </h2>
            <p style={{ fontSize: "11.5px", color: "var(--text-muted)", marginBottom: "12px", lineHeight: "1.3" }}>
              The real-time speech-to-text transcript from the meeting stream, highlighting key applicant-indicative words.
            </p>

            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "10px", maxHeight: "250px" }}>
              {transcripts.length > 0 ? (
                transcripts.map((t, idx) => (
                  <div key={idx} style={{ fontSize: "12.5px", padding: "10px", borderRadius: "6px", backgroundColor: "rgba(0,0,0,0.1)", border: "1px solid var(--border-subtle)" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontWeight: "700", color: t.role === "candidate" ? "var(--accent-purple)" : t.role === "interviewer" ? "var(--accent-amber)" : "var(--text-primary)" }}>
                        {t.speaker}
                      </span>
                      {t.role !== "neutral" && (
                        <span style={{ 
                          fontSize: "9px", 
                          padding: "1px 5px", 
                          borderRadius: "4px", 
                          fontWeight: "700",
                          backgroundColor: t.role === "candidate" ? "rgba(139, 92, 246, 0.15)" : "rgba(245, 158, 11, 0.15)",
                          color: t.role === "candidate" ? "var(--accent-purple)" : "var(--accent-amber)"
                        }}>
                          {t.role.toUpperCase()} TARGET
                        </span>
                      )}
                    </div>
                    <p style={{ color: "var(--text-secondary)", lineHeight: "1.4" }}>
                      {/* Highlight keywords */}
                      {t.text.split(" ").map((word, wIdx) => {
                        const cleanWord = word.toLowerCase().replace(/[^a-z]/g, "");
                        const isMatch = ["resume", "experience", "work", "worked", "built", "previous", "background", "explain", "describe", "handle"].includes(cleanWord);
                        return (
                          <span key={wIdx} style={{ color: isMatch ? "var(--text-primary)" : "inherit", fontWeight: isMatch ? "700" : "normal" }}>
                            {word}{" "}
                          </span>
                        );
                      })}
                    </p>
                  </div>
                ))
              ) : (
                <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", color: "var(--text-muted)", fontSize: "12px" }}>
                  Awaiting transcript stream...
                </div>
              )}
              <div ref={transcriptEndRef} />
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
