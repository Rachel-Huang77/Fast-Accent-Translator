import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Dashboard.module.css";
import MessageBox from "../../components/MessageBox";
import { validatePasswordComplexity, validateEmailFormat } from "../../utils/validators";

import { verifyUpgradeKey } from "../../api/dashboard";
import {
  listConversations,
  createConversation,
  loadConversation,
  renameConversation,
  appendSegment,
  deleteConversation,
} from "../../api/conversations";
import { createStreamClient } from "../../api/streamClient";
import { changePassword } from "../../api/auth";
import { apiRequest } from "../../config/api";

/** ===== Constants ===== */
const ACCENTS = [
  "American English",
  "Australia English",
  "British English",
  "Chinese English",
  "India English",
];
const USE_LOCAL_SPEECH = (import.meta.env.VITE_USE_LOCAL_SPEECH || "0") === "1";

// Speaker color mapping
const SPEAKER_COLORS = {
  "SPEAKER_00": "#FF6B6B",  // Red
  "SPEAKER_01": "#4ECDC4",  // Cyan
  "SPEAKER_02": "#FFD93D",  // Yellow
};

const SPEAKER_NAMES = {
  "SPEAKER_00": "Speaker 1",
  "SPEAKER_01": "Speaker 2",
  "SPEAKER_02": "Speaker 3",
};

/** Simple eye icon */
function EyeIcon({ open = false }) {
  return open ? (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" fill="none" stroke="currentColor" strokeWidth="1.8"/>
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.8"/>
    </svg>
  ) : (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 3l18 18" fill="none" stroke="currentColor" strokeWidth="1.8"/>
      <path d="M10.58 10.58a3 3 0 104.24 4.24M9.88 5.09A10.7 10.7 0 0112 5c7 0 11 7 11 7a17.2 17.2 0 01-3.11 3.88M6.11 7.11A17.2 17.2 0 001 12s4 7 11 7a10.7 10.7 0 003.04-.43" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

/** Generate default title for new conversations */
function generateDefaultTitle() {
  const ts = new Date();
  return `New Chat ${ts.toLocaleDateString()}/${ts.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })}`;
}

/** Title helper */
function titleFrom(text) {
  if (!text) {
    return generateDefaultTitle();
  }
  const first = (text.split(/(?<=[.!?])\s+/)[0] || text).slice(0, 60);
  const cleaned = first
    .replace(/\s+/g, " ")
    .replace(/[^\p{L}\p{N}\s'',-]/gu, "")
    .trim();
  if (!cleaned) return generateDefaultTitle();
  const titleCased = cleaned.replace(/\w\S*/g, (w) => w[0].toUpperCase() + w.slice(1));
  return titleCased;
}

export default function Dashboard() {
  const navigate = useNavigate();

  /** ===== user session ===== */
  const userId =
    localStorage.getItem("authUserId") || sessionStorage.getItem("authUserId");
  const username =
    localStorage.getItem("authUsername") ||
    sessionStorage.getItem("authUsername") ||
    "User";

  useEffect(() => {
    if (!userId) navigate("/login", { replace: true });
  }, [userId, navigate]);

  const ACTIVE_KEY = `activeId:${userId || "anon"}`;
  const PAID_UNLOCK_KEY = `paidUnlocked:${userId || "anon"}`;

  /** ===== settings menu ===== */
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  useEffect(() => {
    const onDocClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  /** ===== model / accent ===== */
  const [modelUnlocked, setModelUnlocked] = useState(() => {
    return localStorage.getItem(PAID_UNLOCK_KEY) === "1";
  });
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem(PAID_UNLOCK_KEY) === "1" ? "paid" : "free";
  });
  const [selectedAccent, setSelectedAccent] = useState(ACCENTS[0]);

  useEffect(() => {
    if (!modelUnlocked && selectedModel === "paid") {
      setSelectedModel("free");
    }
  }, [modelUnlocked, selectedModel]);

  /** ===== conversations ===== */
  const [convos, setConvos] = useState([]);
  const [activeId, setActiveId] = useState(() => localStorage.getItem(ACTIVE_KEY));
  const activeConv = convos.find((c) => c.id === activeId) || null;


  /** ===== streaming segment state (NEW) ===== */
  const [pendingFinal, setPendingFinal] = useState(null);
  const [isCommitting, setIsCommitting] = useState(false);

  useEffect(() => {
    if (!userId) return;
    (async () => {
      const list = await listConversations();
      if (list.length) {
        setConvos(list);
        const stored = localStorage.getItem(ACTIVE_KEY);
        const pick = stored && list.some((c) => c.id === stored) ? stored : list[0].id;
        setActiveId(pick);
        localStorage.setItem(ACTIVE_KEY, pick);
      } else {
        const c = await createConversation({ title: generateDefaultTitle() });
        setConvos([c]);
        setActiveId(c.id);
        localStorage.setItem(ACTIVE_KEY, c.id);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  useEffect(() => {
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId);
  }, [activeId, ACTIVE_KEY]);

  // Prevent duplicate clicks on New button
  const creatingRef = useRef(false);
  const handleNewConversation = async () => {
    if (creatingRef.current) return;
    creatingRef.current = true;
    try {
      const c = await createConversation({ title: generateDefaultTitle() });
      setConvos((prev) => (prev.some((x) => x.id === c.id) ? prev : [c, ...prev]));
      setActiveId(c.id);
      localStorage.setItem(ACTIVE_KEY, c.id);
    } finally {
      creatingRef.current = false;
    }
  };

  const activateConversation = async (id) => {
    if (id === activeId) return;
    setActiveId(id);
    const data = await loadConversation(id);
    if (data) setConvos((prev) => prev.map((c) => (c.id === id ? data : c)));
  };

  /** ===== dots + rename/delete ===== */
  const [hoverId, setHoverId] = useState(null);
  const [dotMenuFor, setDotMenuFor] = useState(null);
  const dotMenuRef = useRef(null);
  useEffect(() => {
    const onDocClick = (e) => {
      if (dotMenuRef.current && !dotMenuRef.current.contains(e.target)) setDotMenuFor(null);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [renameId, setRenameId] = useState(null);
  const openRename = (conv) => {
    setRenameId(conv.id);
    setRenameValue(conv.title || "");
    setRenameOpen(true);
    setDotMenuFor(null);
  };
  const commitRename = async () => {
    if (!renameId) return;
    const newTitle = renameValue || generateDefaultTitle();
    await renameConversation(renameId, newTitle);
    setConvos((prev) =>
      prev.map((c) => (c.id === renameId ? { ...c, title: newTitle } : c))
    );
    setRenameOpen(false);
    setRenameId(null);
  };
  const doDelete = async (id) => {
    await deleteConversation(id);
    setConvos((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) {
      const next = await listConversations();
      if (next.length) {
        setActiveId(next[0].id);
        localStorage.setItem(ACTIVE_KEY, next[0].id);
      } else {
        const c = await createConversation({ title: generateDefaultTitle() });
        setConvos([c]);
        setActiveId(c.id);
        localStorage.setItem(ACTIVE_KEY, c.id);
      }
    }
    setDotMenuFor(null);
  };

  /** ===== transcript / stream ===== */
  const [recording, setRecording] = useState(false);
  const [volumeOpen, setVolumeOpen] = useState(false);
  const [volume, setVolume] = useState(1);
  const transcriptBoxRef = useRef(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [interimText, setInterimText] = useState("");
  
  const [previewText, setPreviewText] = useState("");  // ✅ Web Speech API preview text
  const streamingTranslation = true;  // ✅ Streaming translation enabled by default (switch removed)
  const currentSegIdRef = useRef(null);
  const currentConvIdRef = useRef(null);   // Current segment's conversation ID (for cleanup)
  const segAudioUrlRef = useRef(null);
  const streamRef = useRef(null);
  const finishOnceRef = useRef(false);     // Ensure each segment only finishes once
  const speechRecognitionRef = useRef(null);  // ✅ Web Speech Recognition instance
  const ttsQueueRef = useRef([]);  // ✅ TTS audio playback queue
  const ttsPlayingRef = useRef(false);  // ✅ Whether TTS is currently playing
  const ttsDebounceTimerRef = useRef(null);  // ✅ TTS debounce timer
  const lastSpokenTextRef = useRef('');  // ✅ Last played text (for incremental detection)
  const lastTtsTimeRef = useRef(0);  // ✅ Last TTS trigger time (for rate limiting)

  const startSegment = async () => {
    if (!activeConv) return null;
    const segId = "s_" + Date.now();
    currentSegIdRef.current = segId;
    segAudioUrlRef.current = null;
    finishOnceRef.current = false;

    setConvos((prev) =>
      prev.map((c) =>
        c.id !== activeConv.id
          ? c
          : {
              ...c,
              segments: [
                ...(c.segments || []),
                { id: segId, start: Date.now(), end: null, transcript: "", audioUrl: null },
              ],
            }
      )
    );
    setLiveTranscript("");
    setInterimText("");
    setTimeout(() => {
      if (transcriptBoxRef.current)
        transcriptBoxRef.current.scrollTop = transcriptBoxRef.current.scrollHeight;
    }, 0);
    return segId;
  };

  // —— Critical fix: Allow passing "final text" directly to avoid blank state due to timing issues
  const finishSegment = async (finalText) => {
    if (finishOnceRef.current) return;
    finishOnceRef.current = true;

    const segId = currentSegIdRef.current;
    const convId = currentConvIdRef.current || activeId;
    if (!segId || !convId) return;

    const textToSave =
      (typeof finalText === "string" && finalText.length > 0)
        ? finalText
        : (liveTranscript || "");

    if (finalText && finalText !== liveTranscript) {
      setLiveTranscript(finalText);
    }

    // ✨ Update local state first to ensure segment is correctly added to activeConv
    setConvos((prev) => {
      return prev.map((c) => {
        if (c.id !== convId) return c;
        // Check if segment already exists
        const existingSeg = (c.segments || []).find((s) => s.id === segId);
        const segs = existingSeg
          ? (c.segments || []).map((s) =>
              s.id === segId
                ? { ...s, end: Date.now(), transcript: textToSave, audioUrl: segAudioUrlRef.current }
                : s
            )
          : [
              ...(c.segments || []),
              {
                id: segId,
                start: Date.now() - 1,
                end: Date.now(),
                transcript: textToSave,
                audioUrl: segAudioUrlRef.current,
              },
            ];
        const next = { ...c, segments: segs };
        if ((c.segments?.length || 0) >= 1 && c.title?.startsWith("New Chat") && textToSave) {
          next.title = titleFrom(textToSave) || c.title;
        }
        return next;
      });
    });

    try {
      await appendSegment(convId, {
        id: segId,
        start: Date.now() - 1,
        end: Date.now(),
        transcript: textToSave,
        audioUrl: segAudioUrlRef.current,
      });
    } catch {}

    // ✨ Delay clearing liveTranscript to ensure UI has updated to show segment
    setTimeout(() => {
      setLiveTranscript("");
      setInterimText("");
    }, 100);
    currentSegIdRef.current = null;
    // Don't clear currentConvIdRef, keep it as fallback
  };

  const micStart = async () => {
    // ✨ Auto-create new conversation:
    // 1. If there's no conversation list
    // 2. No active conversation
    // 3. Current active conversation has no segments (showing placeholder text)
    let convId = activeId;
    const hasNoSegments = activeConv && (!activeConv.segments || activeConv.segments.length === 0);
    
    if (convos.length === 0 || !activeConv || !activeId || hasNoSegments) {
      console.log(`[Dashboard] Auto-creating new conversation (convos.length=${convos.length}, activeConv=${!!activeConv}, activeId=${activeId}, hasNoSegments=${hasNoSegments})`);
      const c = await createConversation({ title: generateDefaultTitle() });
      // ✨ Update both convos and activeId simultaneously to ensure activeConv can be calculated immediately
      setConvos((prev) => (prev.some((x) => x.id === c.id) ? prev : [c, ...prev]));
      setActiveId(c.id);
      localStorage.setItem(ACTIVE_KEY, c.id);
      convId = c.id;
      console.log(`[Dashboard] ✅ Created new conversation: ${c.id}`);
    } else {
      console.log(`[Dashboard] Using existing conversation: ${convId}`);
    }
    currentConvIdRef.current = convId; // Record this segment's conversation ID
    await startSegment();

    streamRef.current = createStreamClient({
      conversationId: convId,
      model: selectedModel, // "free" | "paid"
      accent: selectedAccent,
      mode: USE_LOCAL_SPEECH ? "local" : "ws",
      onText: async (payload) => {
        if (typeof payload === "string") {
          setInterimText("");
          setLiveTranscript((prev) => (prev ? prev + payload : payload));
        } else if (payload.type === "transcripts_updated") {
          // ✨ Received GPT formatting completion notification, auto-refresh Dashboard
          console.log(`[Dashboard] 📥 Received transcripts_updated, count=${payload.count}`);
          try {
            const data = await loadConversation(convId);
            if (data) {
              setConvos((prev) => prev.map((c) => (c.id === convId ? data : c)));
              console.log(`[Dashboard] ✅ Transcripts refreshed automatically`);
            }
          } catch (e) {
            console.error("[Dashboard] Failed to refresh transcripts:", e);
          }
        } else {
          const { interim, final } = payload;
          if (interim != null) setInterimText(interim);
          if (final) {
            // 1️⃣ UI 显示 final（但不清空）
            setInterimText("");
            setLiveTranscript(final);
            setPendingFinal(final);

            // 2️⃣ 立刻开始 commit（这是唯一入口）
            if (!isCommitting) {
              setIsCommitting(true);

              try {
                const seg = await appendSegment(convId, {
                  transcript: final,
                  audioUrl: segAudioUrlRef.current ?? null,
                });

                // 3️⃣ backend 已确认：现在才清 UI
                setLiveTranscript("");
                setPendingFinal(null);

                // 4️⃣ ✅ 统一的 TTS 触发点（Step 4）
                streamRef.current?.requestTts(final);

              } catch (e) {
                console.error("[Dashboard] appendSegment failed, keep text", e);
                // ❗什么都不做，UI 保留
              } finally {
                setIsCommitting(false);
              }
            }
          }

        }
        if (transcriptBoxRef.current) {
          transcriptBoxRef.current.scrollTop = transcriptBoxRef.current.scrollHeight;
        }
      },
      onTtsStart: () => {
        segAudioUrlRef.current = null;
      },
      onTtsBlob: (blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        segAudioUrlRef.current = url;
      },
      onTtsEnded: () => {
        // Fallback: If not finished, finish once more here
        if (!finishOnceRef.current) {
          setTimeout(() => { finishSegment(); }, 0);
        }
      },
      outputVolume: volume,
    });

    await streamRef.current.open();
    await streamRef.current.startSegment();
    await streamRef.current.startMic?.();
    setRecording(true);
    
    // ✅ Start Web Speech API real-time preview
    startWebSpeechPreview();
  };

  const micStop = async () => {
    setRecording(false);
    
    // ✅ Stop Web Speech API
    stopWebSpeechPreview();
    
    // ✨ Get Web Speech text and send to backend
    const webspeechText = liveTranscript || "";
    
    try { 
      await streamRef.current?.stopMic?.(); 
    } catch {}
    
    try { 
      // ✨ Send Web Speech text to backend (for GPT comparison)
      await streamRef.current?.stopSegment?.(webspeechText);
    } catch {}
    
    // ✨ Use Web Speech text to complete current segment
    // Whisper no longer pushes final text, so we manually trigger finishSegment
    // Even if webspeechText is empty, still finish segment (user may not have spoken)
    setTimeout(() => {
      if (!finishOnceRef.current) {
        console.log(`[Dashboard] Finishing segment with Web Speech text (${webspeechText.length} chars)`);
        finishSegment(webspeechText || "");
      }
    }, 500);  // Delay 500ms to ensure Web Speech final results have accumulated
  };

  const onMicToggle = () => (recording ? micStop() : micStart());

  /** ===== Streaming Translation TTS Request ===== */
  const requestStreamingTts = async (text) => {
    if (!text || !currentConvIdRef.current) return;

    try {
      console.log(
        `[Streaming TTS] Requesting for: "${text.substring(0, 50)}..."`
      );

      // 正确方式：统一走 apiRequest（JWT 自动注入）
      const r = await apiRequest("/tts/synthesize", {
        method: "POST",
        body: {
          text,
          accent: selectedAccent,
          model: selectedModel,
        },
      });

      if (!r.ok) {
        console.error("[Streaming TTS] Request failed:", r.message);
        return;
      }

      // 后端返回 audio blob 的话，apiRequest 不适合
      // 如果你当前后端是直接返回 audio stream / blob，
      // 那么推荐后端改成返回 base64 / url
      // 或单独为 TTS 保留一个 fetch（但必须带 token）

      const audioBlob = r.data;
      enqueueTts(audioBlob);
    } catch (err) {
      console.error("[Streaming TTS] Error:", err);
    }
  };


  /** ===== TTS Audio Queue Playback ===== */
  const playTtsAudio = async (audioBlob) => {
    return new Promise((resolve) => {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.volume = volume;
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        resolve();
      };
      
      audio.onerror = () => {
        console.error('[TTS Queue] Audio playback error');
        URL.revokeObjectURL(audioUrl);
        resolve();
      };
      
      audio.play().catch((err) => {
        console.error('[TTS Queue] Play failed:', err);
        resolve();
      });
    });
  };
  
  const processTtsQueue = async () => {
    if (ttsPlayingRef.current) return;  // Already playing
    if (ttsQueueRef.current.length === 0) return;  // Queue is empty
    
    ttsPlayingRef.current = true;
    
    while (ttsQueueRef.current.length > 0) {
      const audioBlob = ttsQueueRef.current.shift();
      await playTtsAudio(audioBlob);
    }
    
    ttsPlayingRef.current = false;
  };
  
  const enqueueTts = (audioBlob) => {
    ttsQueueRef.current.push(audioBlob);
    processTtsQueue();  // Try to start playback
  };

  /** ===== Web Speech API Real-time Preview ===== */
  const startWebSpeechPreview = () => {
    // Clear old debounce timer
    if (ttsDebounceTimerRef.current) {
      clearTimeout(ttsDebounceTimerRef.current);
      ttsDebounceTimerRef.current = null;
    }
    // Reset played text and trigger time (starting new recording session)
    lastSpokenTextRef.current = '';
    lastTtsTimeRef.current = 0;
    
    // Check browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("[Web Speech] Not supported in this browser");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;  // Continuous recognition
      recognition.interimResults = true;  // Return interim results
      recognition.lang = 'en-US';  // Can be dynamically set based on selectedAccent
      
      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const transcript = result[0].transcript;
          const confidence = result[0].confidence || 1.0;  // Web Speech API confidence
          
          // ✅ Hallucination check 1: Confidence check (0ms delay)
          if (confidence < 0.5) {
            console.warn(`[Hallucination Check] Low confidence (${confidence.toFixed(2)}): "${transcript}"`);
            continue;  // Skip low confidence results
          }
          
          // ✅ Hallucination check 2: Empty text and filler word filtering (< 2ms delay)
          const trimmedText = transcript.trim();
          
          // Detect empty text
          if (!trimmedText || trimmedText.length === 0) {
            continue;
          }
          
          // Detect pure filler words (filter when appearing alone)
          const fillerWords = /^(uh|um|hmm|ah|er|oh|mm|mhm|uh-huh|huh)$/i;
          if (fillerWords.test(trimmedText)) {
            console.warn(`[Hallucination Check] Filler word detected: "${trimmedText}"`);
            continue;
          }
          
          // Detect pure punctuation or special characters
          if (/^[^\w\s]+$/.test(trimmedText)) {
            console.warn(`[Hallucination Check] Only punctuation: "${trimmedText}"`);
            continue;
          }
          
          // ✅ Passed checks, process normally
          if (result.isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }
        
        // ✅ Display preview text (light color, italic)
        if (interimTranscript) {
          setPreviewText(interimTranscript);
          
          // ✅ Streaming translation optimization: Use interim results + debounce to trigger TTS
          if (streamingTranslation) {
            // Clear previous debounce timer
            if (ttsDebounceTimerRef.current) {
              clearTimeout(ttsDebounceTimerRef.current);
            }
            
            // Set new debounce timer (500ms balances response speed and prevents duplicates)
            ttsDebounceTimerRef.current = setTimeout(() => {
              const fullText = interimTranscript.trim();
              
              // ✅ Check text length (at least 8 characters for quick response)
              if (!fullText || fullText.length < 8) return;
              
              // ✅ Rate limiting: At least 1000ms since last trigger
              const now = Date.now();
              if (now - lastTtsTimeRef.current < 1000) {
                console.log(`[Streaming TTS] Rate limited, waiting...`);
                return;
              }
              
              // ✅ Incremental detection: Only play new parts
              const lastSpoken = lastSpokenTextRef.current;
              
              // Text normalization (remove punctuation and extra spaces for comparison)
              const normalize = (text) => text.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
              const normalizedFull = normalize(fullText);
              const normalizedLast = normalize(lastSpoken);
              
              if (normalizedFull.startsWith(normalizedLast) && fullText.length > lastSpoken.length) {
                // New text is continuation of old text
                const newPart = fullText.slice(lastSpoken.length).trim();
                
                // Only play if new part is at least 8 characters (more conservative)
                if (newPart.length >= 8) {
                  console.log(`[Streaming TTS] Incremental: "${newPart.substring(0, 30)}..." (was: "${lastSpoken.substring(0, 20)}...")`);
                  lastSpokenTextRef.current = fullText;
                  lastTtsTimeRef.current = now;
                  requestStreamingTts(newPart);
                } else {
                  console.log(`[Streaming TTS] Incremental too short (${newPart.length} chars), skipping`);
                }
              } else if (normalizedFull !== normalizedLast && fullText.length >= 8) {
                // Completely different text, and long enough
                console.log(`[Streaming TTS] Full: "${fullText.substring(0, 30)}..."`);
                lastSpokenTextRef.current = fullText;
                lastTtsTimeRef.current = now;
                requestStreamingTts(fullText);
              }
            }, 500);  // 500ms debounce delay (balances speed and accuracy)
          }
        }
        
        // ✅ Final recognition results accumulate to liveTranscript
        if (finalTranscript) {
          setPreviewText('');  // Clear preview
          
          // Clear debounce timer (final result has arrived)
          if (ttsDebounceTimerRef.current) {
            clearTimeout(ttsDebounceTimerRef.current);
            ttsDebounceTimerRef.current = null;
          }
          
          setLiveTranscript((prev) => {
            const newText = prev + finalTranscript;
            return newText;
          });
          
          // ✅ Final result: Intelligently handle remaining text
          if (streamingTranslation && finalTranscript.trim()) {
            const fullFinalText = finalTranscript.trim();
            const lastSpoken = lastSpokenTextRef.current;
            const now = Date.now();
            const timeSinceLastTts = now - lastTtsTimeRef.current;
            
            // Text normalization comparison
            const normalize = (text) => text.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
            const normalizedFinal = normalize(fullFinalText);
            const normalizedLast = normalize(lastSpoken);
            
            // Calculate actual unplayed portion
            let remaining = '';
            if (normalizedFinal.startsWith(normalizedLast)) {
              // final is continuation of lastSpoken
              remaining = fullFinalText.slice(lastSpoken.length).trim();
            } else if (normalizedFinal !== normalizedLast) {
              // Completely different, play all
              remaining = fullFinalText;
            }
            
            // ⚠️ If there's unplayed text (even just a few words), it should be played
            if (remaining.length >= 3) {  // Lower threshold to 3 characters (e.g., "me", "you")
              // Check if recently played (within 1 second)
              if (timeSinceLastTts < 1000) {
                console.log(`[Streaming TTS] Final partial playback: "${remaining}" (supplementing missed, triggered ${timeSinceLastTts}ms ago)`);
              } else {
                console.log(`[Streaming TTS] Final playback: "${remaining.substring(0, 30)}..." (${remaining.length} chars)`);
              }
              lastSpokenTextRef.current = fullFinalText;
              lastTtsTimeRef.current = now;
              requestStreamingTts(remaining);
            } else {
              console.log(`[Streaming TTS] Final complete, no new content (last: "${lastSpoken.substring(0, 30)}...", final: "${fullFinalText.substring(0, 30)}...")`);
              lastSpokenTextRef.current = fullFinalText;
            }
          }
        }
      };
      
      recognition.onerror = (event) => {
        console.error('[Web Speech] Error:', event.error);
        if (event.error === 'no-speech') {
          // User didn't speak, ignore
          return;
        }
        // Other errors, try to restart
        setTimeout(() => {
          if (recording && speechRecognitionRef.current) {
            try { recognition.start(); } catch {}
          }
        }, 1000);
      };
      
      recognition.onend = () => {
        // If still recording, auto-restart (continuous recognition)
        if (recording && speechRecognitionRef.current === recognition) {
          try {
            recognition.start();
          } catch (e) {
            console.warn('[Web Speech] Restart failed:', e);
          }
        }
      };
      
      speechRecognitionRef.current = recognition;
      recognition.start();
      console.log('[Web Speech] Started');
    } catch (err) {
      console.error('[Web Speech] Failed to start:', err);
    }
  };
  
  const stopWebSpeechPreview = () => {
    // Clear debounce timer
    if (ttsDebounceTimerRef.current) {
      clearTimeout(ttsDebounceTimerRef.current);
      ttsDebounceTimerRef.current = null;
    }
    
    // Reset played text and trigger time (stop recording, prepare for next new session)
    lastSpokenTextRef.current = '';
    lastTtsTimeRef.current = 0;
    
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
        speechRecognitionRef.current = null;
        setPreviewText('');  // Clear preview text
        console.log('[Web Speech] Stopped');
      } catch (err) {
        console.error('[Web Speech] Failed to stop:', err);
      }
    }
  };

  /** ===== upgrade / logout / change password ===== */
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const upgradeKeyRef = useRef(null);

  const [pwdOpen, setPwdOpen] = useState(false);
  const [newPwd, setNewPwd] = useState("");
  const [showNewPwd, setShowNewPwd] = useState(false);
  const [pwdMsg, setPwdMsg] = useState({ type: "", text: "" });
  const [upgradeMsg, setUpgradeMsg] = useState({ type: "", text: "" });


  const confirmUpgrade = async () => {
  const key = upgradeKeyRef.current?.value?.trim();

  if (!key) {
    setUpgradeMsg({
      type: "error",
      text: "Please enter the upgrade key.",
    });
    return;
  }

  try {
    const r = await verifyUpgradeKey(key);
    if (r?.ok) {
      setModelUnlocked(true);
      localStorage.setItem(PAID_UNLOCK_KEY, "1");

      // Clear input field
      if (upgradeKeyRef.current) {
        upgradeKeyRef.current.value = "";
      }

      // Show success message in modal, user closes modal themselves
      setUpgradeMsg({
        type: "success",
        text: "Upgrade successful! Paid model unlocked.",
      });
    } else {
      setUpgradeMsg({
        type: "error",
        text: "Invalid key. Please check and try again.",
      });
    }
  } catch (e) {
    setUpgradeMsg({
      type: "error",
      text: e?.message || "Unexpected error, please try again.",
    });
  }
};


  const confirmChangePassword = async () => {
  // Clear previous message
  setPwdMsg({ type: "", text: "" });

  if (!newPwd) {
    setPwdMsg({
      type: "error",
      text: "Please enter a new password.",
    });
    return;
  }

  // Use unified password complexity validation (consistent with registration and admin interface)
  const err = validatePasswordComplexity(newPwd);
  if (err) {
    setPwdMsg({
      type: "error",
      text: err,
    });
    return;
  }

  try {
    const res = await changePassword({ newPassword: newPwd });
    if (res?.ok) {
      // Success message shown inside modal
      setPwdMsg({
        type: "success",
        text: "Password updated. It will take effect next login.",
      });

      // Wait a bit before auto-closing modal so user can see success message
      setTimeout(() => {
        setPwdOpen(false);
        setNewPwd("");
        setShowNewPwd(false);
        setPwdMsg({ type: "", text: "" });
      }, 1200);
    } else {
      setPwdMsg({
        type: "error",
        text: res?.message || "Failed to update password.",
      });
    }
  } catch (e) {
    setPwdMsg({
      type: "error",
      text: e?.message || "Unexpected error.",
    });
  }
};




  const confirmLogout = () => {
    if (recording) micStop();
    localStorage.removeItem("authToken");
    localStorage.removeItem("authUserId");
    localStorage.removeItem("authUsername");
    sessionStorage.removeItem("authToken");
    sessionStorage.removeItem("authUserId");
    sessionStorage.removeItem("authUsername");
    navigate("/login", { replace: true });
  };

  return (
    <div className={styles.container}>
      {/* ===== Sidebar ===== */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop} ref={menuRef}>
          <button
            className={styles.settingsButton}
            onClick={() => setMenuOpen((v) => !v)}
            title="Settings"
          >
            ⚙️
          </button>
          <span className={styles.hiText}>Hi, {username}!</span>
          {menuOpen && (
            <div className={styles.dropdown}>
              <button onClick={() => { setMenuOpen(false); setUpgradeOpen(true); }}>
                <span className={styles.icon}>🌐</span> Update Model
              </button>
              <button onClick={() => { setMenuOpen(false); setPwdOpen(true); }}>
                <span className={styles.icon}>🛠️</span> Change Password
              </button>
              <button onClick={() => { setMenuOpen(false); confirmLogout(); }}>
                <span className={styles.icon}>📤</span> Log Out
              </button>
            </div>
          )}
        </div>

        <div className={styles.convoHeader}>
          <span>Conversations</span>
          <button className={styles.newBtn} onClick={handleNewConversation}>New</button>
        </div>

        <ul className={styles.convoList}>
          {convos.map((c) => {
            const lastSeg = (c.segments || [])[ (c.segments || []).length - 1 ];
            const preview = lastSeg?.transcript?.slice(0, 38) || "";
            return (
              <li
                key={c.id}
                onMouseEnter={() => setHoverId(c.id)}
                onMouseLeave={() => setHoverId(null)}
                className={`${styles.convoItem} ${c.id === activeId ? styles.convoActive : ""}`}
                onClick={() => activateConversation(c.id)}
              >
                <div className={styles.convoRow}>
                  <div className={styles.convoTitle}>{c.title || "Untitled"}</div>
                  <button
                    className={`${styles.dotBtn} ${hoverId === c.id ? styles.dotBtnVisible : ""}`}
                    onClick={(e) => { e.stopPropagation(); setDotMenuFor(c.id === dotMenuFor ? null : c.id); }}
                    title="More"
                  >
                    ⋯
                  </button>
                </div>
                {preview ? <div className={styles.convoPreview}>{preview}</div> : null}

                {dotMenuFor === c.id && (
                  <div ref={dotMenuRef} className={styles.dotMenu} onClick={(e) => e.stopPropagation()}>
                    <div className={styles.dotMenuItem} onClick={() => openRename(c)}>✏️ Rename</div>
                    <div className={styles.dotMenuItemDanger} onClick={() => doDelete(c.id)}>🗑️ Delete</div>
                  </div>
                )}
              </li>
            );
          })}
          {!convos.length && <li className={styles.convoEmpty}>No conversations yet</li>}
        </ul>
      </aside>

      {/* ===== Main ===== */}
      <main className={styles.main}>
        <div className={styles.modelBox}>
          <label className={styles.accentLabel}>Model </label>
          <select
            className={styles.select}
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            <option value="free">Free</option>
            <option value="paid" disabled={!modelUnlocked}>Paid</option>
          </select>
        </div>

        <div className={styles.transcript} ref={transcriptBoxRef}>
          {activeConv?.segments?.map((s) => {
            // ✅ Get speaker information
            const speakerId = s.speakerId || null;
            const speakerColor = speakerId ? SPEAKER_COLORS[speakerId] : null;
            const speakerName = speakerId ? SPEAKER_NAMES[speakerId] : null;
            
            return (
              <div 
                key={s.id} 
                className={styles.segment}
                data-speaker={speakerId}
              >
                <div className={styles.segmentMeta}>
                  {/* ✅ Display speaker tag */}
                  {speakerId && (
                    <span 
                      className={styles.speakerTag}
                      style={{ backgroundColor: speakerColor }}
                    >
                      {speakerName}
                    </span>
                  )}
                  <span>
                    {new Date(s.start).toLocaleTimeString()} — {s.end ? new Date(s.end).toLocaleTimeString() : "…"}
                  </span>
                  {s.audioUrl && <audio controls autoPlay src={s.audioUrl} className={styles.segmentAudio} />}
                </div>
                {s.transcript ? <div className={styles.segmentText}>{s.transcript}</div> : null}
              </div>
            );
          })}
          {recording ? (
            <div className={`${styles.segment} ${styles.segmentLive}`}>
              <div className={styles.segmentMeta}>
                <span>Recording…</span>
                {previewText && <span className={styles.previewBadge}>Preview</span>}
              </div>
              <div className={styles.segmentText}>
                {liveTranscript}
                {previewText && <span className={styles.previewText}>{previewText}</span>}
                {interimText && <span style={{ opacity: 0.5 }}>{interimText}</span>}
              </div>
            </div>
          ) : !activeConv?.segments?.length ? (
            <span className={styles.placeholder}>Transcription will appear here…</span>
          ) : null}
        </div>

        <div className={styles.accentBox}>
          <label className={styles.accentLabel}>Accent</label>
          <select className={styles.select} value={selectedAccent} onChange={(e) => setSelectedAccent(e.target.value)}>
            {ACCENTS.map((a) => <option key={a}>{a}</option>)}
          </select>
        </div>

        <div className={styles.centerControls}>
          <button
            className={`${styles.iconBtn} ${styles.micBtn} ${recording ? styles.micActive : ""}`}
            onClick={onMicToggle}
            title={recording ? "Stop" : "Start"}
          >
            🎙️
          </button>
          <div className={styles.volumeWrap}>
            <button className={styles.iconBtn} title="Volume" onClick={() => setVolumeOpen((v) => !v)}>
              🔊
            </button>
            {volumeOpen && (
              <div className={styles.volumePopover} onMouseLeave={() => setVolumeOpen(false)}>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={volume}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value);
                    setVolume(v);
                    streamRef.current?.setOutputVolume?.(v);
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ===== rename modal ===== */}
      {renameOpen && (
        <div className={styles.backdrop} onClick={() => setRenameOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>Rename Conversation</div>
            <div className={styles.modalBody}>
              <input
                className={styles.input}
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && commitRename()}
                autoFocus
                placeholder="Enter a new title"
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnGhost} onClick={() => setRenameOpen(false)}>Cancel</button>
              <button className={styles.btnPrimary} onClick={commitRename}>Save</button>
            </div>
          </div>
        </div>
      )}

      {/* ===== upgrade modal ===== */}
      {upgradeOpen && (
        <div
          className={styles.backdrop}
          onClick={() => {
            setUpgradeOpen(false);
            setUpgradeMsg({ type: "", text: "" });
          }}
        >
          <div
            className={styles.modal}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>Enter upgrade key</div>

            {/* Display MessageBox inside modal (same level as modal) */}
            <MessageBox
              type={upgradeMsg.type || "error"}
              message={upgradeMsg.text}
              onClose={() => setUpgradeMsg({ type: "", text: "" })}
            />

            <div className={styles.modalBody}>
              <input
                className={styles.input}
                ref={upgradeKeyRef}
                placeholder="Enter key (e.g., SECRET123)"
                autoFocus
              />
            </div>

            <div className={styles.modalActions}>
              <button
                className={styles.btnGhost}
                onClick={() => {
                  setUpgradeOpen(false);
                  setUpgradeMsg({ type: "", text: "" });
                }}
              >
                Cancel
              </button>
              <button
                className={styles.btnPrimary}
                onClick={confirmUpgrade}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}


      {/* ===== change password modal ===== */}
      {/* ===== Change Password Modal ===== */}
      {pwdOpen && (
        <div
          className={styles.backdrop}
          onClick={() => {
            // If there's an error message, don't close by clicking outside
            if (!pwdMsg.text) setPwdOpen(false);
          }}
        >
          <div
            className={styles.modal}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>Change Password</div>

            <div className={styles.modalBody}>
              <label className={styles.modalLabel}>New Password</label>

              <div className={styles.field}>
                <input
                  className={`${styles.input} ${styles.inputWithEye}`}
                  type={showNewPwd ? "text" : "password"}
                  placeholder="Enter a new password"
                  value={newPwd}
                  onChange={(e) => {
                    setNewPwd(e.target.value);
                    setPwdMsg({ type: "", text: "" }); // Clear message when typing
                  }}
                />

                <button
                  type="button"
                  className={styles.eyeBtn}
                  onClick={() => setShowNewPwd((v) => !v)}
                  aria-label={showNewPwd ? "Hide password" : "Show password"}
                  title={showNewPwd ? "Hide password" : "Show password"}
                >
                  <EyeIcon open={showNewPwd} />
                </button>
              </div>

              {/* ===== MessageBox: Message area ===== */}
              {pwdMsg.text && (
                <MessageBox 
                  type={pwdMsg.type}
                  onClose={() => setPwdMsg({ type: "", text: "" })}
                >
                  {pwdMsg.text}
                </MessageBox>
              )}
            </div>

            <div className={styles.modalActions}>
              <button
                className={styles.btnGhost}
                onClick={() => {
                  setPwdOpen(false);
                  setNewPwd("");
                  setPwdMsg({ type: "", text: "" });
                }}
              >
                Cancel
              </button>

              <button
                className={styles.btnPrimary}
                onClick={confirmChangePassword}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      
    </div>
  );
}
