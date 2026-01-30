// Import WebSocket URLs from unified API configuration
import { WS_UPLOAD_URL, WS_TEXT_URL, WS_TTS_URL } from '../config/api.js';

export function createStreamClient({
  conversationId,
  model = "free",
  accent = "American English",
  onText,
  onTtsStart,
  onTtsBlob,
  onTtsEnded,
  outputVolume = 1,
}) {
  let uploadWS = null;
  let textWS = null;
  let ttsWS = null;

  let mediaStream = null;
  let mediaRecorder = null;

  // ====== (New) Capture-side noise reduction processing ======
  let procAudioCtx = null;      // AudioContext dedicated to microphone noise reduction (separate from TTS playback)
  let procDest = null;          // MediaStreamDestination, output to MediaRecorder

  // ===== TTS playback related =====
  let ttsMime = "audio/mpeg";
  let ttsChunks = []; // Collect all binary chunks, finally combine into Blob

  // -- MSE player --
  let audioEl = null;
  let mediaSource = null;
  let sourceBuffer = null;
  let mseQueue = [];         // Uint8Array queue, waiting to append
  let mseReady = false;
  let mseEnded = false;

  // -- WebAudio fallback player (only enabled when MSE is unavailable) --
  let audioContext = null;   // Note: This audioContext is only used for TTS playback fallback
  let decodeQueue = [];      // ArrayBuffer queue
  let decodePlaying = false;

  let currentVolume = Math.max(0, Math.min(1, outputVolume));

  // ========== Utilities ==========
  function sendJSON(ws, obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  function ensureAudioElement() {
    if (audioEl) return audioEl;
    audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    audioEl.controls = false;
    audioEl.style.display = "none"; // Don't occupy space
    audioEl.volume = currentVolume;
    document.body.appendChild(audioEl);
    return audioEl;
  }

  // ========== MSE implementation ==========
  function mseInit() {
    const el = ensureAudioElement();
    if (!("MediaSource" in window)) return false;

    mediaSource = new MediaSource();
    el.src = URL.createObjectURL(mediaSource);
    mseQueue = [];
    mseReady = false;
    mseEnded = false;

    mediaSource.addEventListener("sourceopen", () => {
      try {
        if (!MediaSource.isTypeSupported(ttsMime)) {
          ttsMime = "audio/mpeg";
        }
        sourceBuffer = mediaSource.addSourceBuffer(ttsMime);
        sourceBuffer.mode = "sequence";
        sourceBuffer.addEventListener("updateend", mseFeed);
        mseReady = true;
        mseFeed();
      } catch (e) {
        console.warn("[MSE] sourceopen error, fallback to WebAudio:", e);
        mseTearDown();
      }
    });

    mediaSource.addEventListener("error", (e) => {
      console.warn("[MSE] mediaSource error:", e);
    });

    return true;
  }

  function mseAppend(u8) {
    if (!mseReady || !sourceBuffer) {
      mseQueue.push(u8);
      return;
    }
    mseQueue.push(u8);
    mseFeed();
  }

  function mseFeed() {
    if (!sourceBuffer || sourceBuffer.updating) return;
    if (mseQueue.length === 0) {
      if (mseEnded && mediaSource && mediaSource.readyState === "open") {
        try { mediaSource.endOfStream(); } catch { /* Ignore if already ended */ }
      }
      return;
    }
    const chunk = mseQueue.shift();
    try {
      sourceBuffer.appendBuffer(chunk);
    } catch (e) {
      console.warn("[MSE] append error, dropping chunk:", e);
    }
  }

  function mseEnd() {
    mseEnded = true;
    mseFeed();
  }

  function mseTearDown() {
    try {
      if (sourceBuffer) sourceBuffer.abort();
    } catch { /* Ignore if already aborted */ }
    try {
      if (mediaSource && mediaSource.readyState === "open") {
        mediaSource.endOfStream();
      }
    } catch { /* Ignore if already ended */ }
    sourceBuffer = null;
    mediaSource = null;
    mseQueue = [];
    mseReady = false;
    mseEnded = false;
  }

  // ========== WebAudio fallback implementation (decode after buffering) ==========
  const MIN_CHUNK_BYTES = 24 * 1024; // Accumulate to 24KB before decoding
  const MAX_BUFFER_BYTES = 1024 * 1024; // Upper limit 1MB

  async function waPlayNext() {
    if (decodePlaying) return;
    decodePlaying = true;

    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      const el = ensureAudioElement();
      el.volume = currentVolume;

      while (decodeQueue.length > 0) {
        let total = 0;
        for (const ab of decodeQueue) total += ab.byteLength;
        if (total < MIN_CHUNK_BYTES) break;

        const big = new Uint8Array(total);
        let offset = 0;
        while (decodeQueue.length) {
          const ab = decodeQueue.shift();
          const u8 = new Uint8Array(ab);
          big.set(u8, offset);
          offset += u8.byteLength;
        }

        try {
          const buf = big.buffer;
          const decoded = await audioContext.decodeAudioData(buf.slice(0));
          const src = audioContext.createBufferSource();
          const gain = audioContext.createGain();
          gain.gain.value = currentVolume;
          src.buffer = decoded;
          src.connect(gain);
          gain.connect(audioContext.destination);

          await new Promise((resolve) => {
            src.onended = resolve;
            src.start(0);
          });
        } catch (e) {
          console.warn("[WebAudio] decode failed once, keep buffering:", e);
          decodeQueue.unshift(big.buffer);
          if (big.byteLength > MAX_BUFFER_BYTES) {
            console.warn("[WebAudio] buffer too large, dropping");
            decodeQueue = [];
          }
          break;
        }
      }
    } finally {
      decodePlaying = false;
    }
  }

  // ========== External API ==========
  async function open() {
    console.log("[client] createStreamClient.open() called");

    // 1) Text channel
    await new Promise((resolve, reject) => {
      textWS = new WebSocket(WS_TEXT_URL);
      textWS.onopen = () => {
        console.log("[client] textWS open, subscribe", conversationId);
        sendJSON(textWS, { type: "subscribe", conversationId });
        resolve();
      };
      textWS.onerror = (e) => { console.error("[client] textWS error", e); reject(e); };
      textWS.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.type === "ready" || msg?.type === "pong") return;
          if (msg.type === "interim") {
            onText?.({ interim: msg.text, ts: msg.ts, confidence: msg.confidence });
          } else if (msg.type === "final") {
            onText?.({ final: msg.text, ts: msg.ts, confidence: msg.confidence });
          } else if (msg.type === "transcripts_updated") {
            // ✨ Received backend GPT formatting completion notification
            onText?.({ type: "transcripts_updated", count: msg.count });
          } else {
            console.warn("[client] textWS unknown msg:", msg);
          }
        } catch {
          if (typeof ev.data === "string") onText?.(ev.data);
        }
      };
    });

    // 2) TTS channel
    if (WS_TTS_URL) {
      try {
        await new Promise((resolve, reject) => {
          ttsWS = new WebSocket(WS_TTS_URL);
          ttsWS.binaryType = "arraybuffer";

          ttsWS.onopen = () => {
            console.log("[client] ttsWS open, subscribe", conversationId);
            sendJSON(ttsWS, { type: "start", conversationId });
            resolve();
          };

          ttsWS.onerror = (e) => { console.warn("[client] ttsWS error", e); reject(e); };

          ttsWS.onmessage = (ev) => {
            if (typeof ev.data === "string") {
              try {
                const msg = JSON.parse(ev.data);
                if (msg.type === "start") {
                  console.log("[client] 🎵 TTS stream starting");
                  ttsMime = msg.mime || "audio/mpeg";
                  ttsChunks = [];

                  const ok = mseInit();
                  if (!ok) {
                    console.warn("[client] MSE not available, fallback to WebAudio buffering");
                    decodeQueue = [];
                    decodePlaying = false;
                  }
                  onTtsStart?.();
                } else if (msg.type === "stop") {
                  console.log("[client] 🎵 TTS stream stopped");
                  if (mediaSource) mseEnd();

                  setTimeout(() => {
                    const blob = new Blob(ttsChunks, { type: ttsMime });
                    onTtsBlob?.(blob);
                    onTtsEnded?.();
                  }, 300);
                }
              } catch {
                // ignore
              }
            } else if (ev.data instanceof ArrayBuffer) {
              const ab = ev.data.slice(0);
              const u8 = new Uint8Array(ab);
              ttsChunks.push(u8);

              if (mediaSource && sourceBuffer) {
                mseAppend(u8);
              } else {
                decodeQueue.push(ab);
                if (!decodePlaying) waPlayNext();
              }
            }
          };
        });
      } catch (e) {
        console.error("[client] ttsWS connection failed:", e);
        ttsWS = null;
      }
    }

    // 3) Upload channel
    await new Promise((resolve, reject) => {
      uploadWS = new WebSocket(WS_UPLOAD_URL);
      uploadWS.onopen = () => {
        console.log("[client] uploadWS open");
        sendJSON(uploadWS, {
          type: "start",
          conversationId,
          model,
          accent,
          sampleRate: 48000,
          format: "audio/webm;codecs=opus",
          asrProvider: "whisper",
        });
        resolve();
      };
      uploadWS.onerror = (e) => { console.error("[client] uploadWS error", e); reject(e); };
    });
  }

  async function startSegment() {
    // noop
  }

  async function stopSegment(webspeechText = "") {
    if (uploadWS?.readyState === WebSocket.OPEN) {
      console.log("[client] send stop with Web Speech text");
      sendJSON(uploadWS, { 
        type: "stop",
        webspeech_text: webspeechText || ""
      });
    }
  }

  // ====== (Modified) Capture + noise reduction + send ======
  async function startMic() {
    console.log("[client] requesting mic");
    try {
      // Enable browser built-in noise suppression/echo cancellation/auto gain, low latency and cross-platform
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          noiseSuppression: true,
          echoCancellation: true,
          autoGainControl: true,
          sampleRate: 48000,
          channelCount: 1
        }
      });
      console.log("[client] mic granted");
    } catch (e) {
      console.error("[client] getUserMedia failed:", e.name, e.message);
      throw e;
    }

    // Lightweight WebAudio processing chain (highpass → lowpass → compression), output to MediaStreamDestination
    try {
      procAudioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
      const src = procAudioCtx.createMediaStreamSource(mediaStream);

      const highpass = procAudioCtx.createBiquadFilter();
      highpass.type = "highpass";
      highpass.frequency.value = 90; // Adjustable 80~120

      const lowpass = procAudioCtx.createBiquadFilter();
      lowpass.type = "lowpass";
      lowpass.frequency.value = 6500; // Adjustable 6~8 kHz

      const comp = procAudioCtx.createDynamicsCompressor();
      comp.threshold.setValueAtTime(-50, procAudioCtx.currentTime);
      comp.knee.setValueAtTime(30, procAudioCtx.currentTime);
      comp.ratio.setValueAtTime(8, procAudioCtx.currentTime);
      comp.attack.setValueAtTime(0.003, procAudioCtx.currentTime);
      comp.release.setValueAtTime(0.25, procAudioCtx.currentTime);

      procDest = procAudioCtx.createMediaStreamDestination();

      // mic -> HP -> LP -> Comp -> procDest
      src.connect(highpass);
      highpass.connect(lowpass);
      lowpass.connect(comp);
      comp.connect(procDest);
      // No local monitoring: If monitoring is needed, can additionally comp.connect(procAudioCtx.destination);
    } catch (e) {
      console.warn("[client] WebAudio pipeline failed, fallback to raw stream:", e);
      procDest = null;
    }

    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    // Record "processed stream", fallback to raw stream if failed
    const streamForRecorder = procDest?.stream || mediaStream;
    mediaRecorder = new MediaRecorder(streamForRecorder, {
      mimeType: mime,
      audioBitsPerSecond: 128000,
    });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0 && uploadWS?.readyState === WebSocket.OPEN) {
        e.data.arrayBuffer().then((buf) => uploadWS.send(buf));
      }
    };

    mediaRecorder.start(40); // One chunk every 40ms
  }

  async function stopMic() {
    try { mediaRecorder?.stop(); } catch { /* Ignore if already stopped */ }
    mediaStream?.getTracks().forEach((t) => t.stop());
    mediaRecorder = null;
    mediaStream = null;

    // Clean up capture-side processing resources
    procDest = null;
    if (procAudioCtx) {
      try { await procAudioCtx.close(); } catch { /* Ignore if already closed */ }
      procAudioCtx = null;
    }
  }

  async function close() {
    try { textWS?.close(); } catch { /* Ignore if already closed */ }
    try { ttsWS?.close(); } catch { /* Ignore if already closed */ }
    try { uploadWS?.close(); } catch { /* Ignore if already closed */ }

    // Release MSE
    try { mseTearDown(); } catch { /* Ignore teardown errors */ }

    // Release AudioContext used for TTS fallback playback (different from capture side)
    if (audioContext) {
      try { await audioContext.close(); } catch { /* Ignore if already closed */ }
      audioContext = null;
    }

    // Release capture-side processing resources (prevent case where close is called without stopMic)
    procDest = null;
    if (procAudioCtx) {
      try { await procAudioCtx.close(); } catch { /* Ignore if already closed */ }
      procAudioCtx = null;
    }
  }

  function setOutputVolume(v) {
    currentVolume = Math.max(0, Math.min(1, v));
    if (audioEl) audioEl.volume = currentVolume;
    console.log("[streamClient] Volume set to:", currentVolume);
  }

  return { open, startSegment, stopSegment, startMic, stopMic, close, setOutputVolume };
}
