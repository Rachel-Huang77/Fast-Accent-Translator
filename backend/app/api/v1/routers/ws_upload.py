import json
import tempfile
import os
import sys
import asyncio
from typing import Dict, Optional, List
from io import BytesIO

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.pubsub import channel
from app.services.asr_openai import webm_to_wav_16k_mono
from app.services import transcribe_audio  # ✅ Use new ASR interface (supports local Whisper)
from app.services.tts_elevenlabs import synth_and_stream_free, synth_and_stream_paid

router = APIRouter()

# ✅ Use in-memory buffer (BytesIO) instead of temporary files
_sessions: Dict[str, dict] = {}  # conv_id -> {"audio_buffer": BytesIO, "accent": str, "model": str, "start_seq": int}

@router.websocket("/ws/upload-audio")
async def ws_upload(ws: WebSocket):
    """
    WebSocket endpoint for uploading audio and receiving real-time transcription.
    
    This endpoint handles the complete audio upload and processing workflow:
    1. Receives audio chunks in real-time
    2. Buffers audio in memory (BytesIO)
    3. On stop message, triggers ASR transcription
    4. Asynchronously processes diarization and GPT formatting
    
    Message flow:
    1. Client sends: {"type": "start", "conversationId": "...", "accent": "...", "model": "..."}
    2. Client sends: binary audio chunks (WebM/Opus format)
    3. Client sends: {"type": "stop", "webspeech_text": "..."} (optional Web Speech text)
    4. Server processes audio and closes connection
    
    Args:
        ws: WebSocket connection object
    
    Note:
        - Audio is buffered in memory for efficient processing
        - Web Speech text (if provided) is used for comparison with Whisper results
        - Diarization and GPT formatting run asynchronously after connection closes
        - The connection is closed after receiving the stop message
    """
    await ws.accept()
    print("[ws_upload] connected")
    conv_id: Optional[str] = None
    audio_buffer: Optional[BytesIO] = None
    
    try:
        # 1. Receive start message
        start_msg = await ws.receive_text()
        meta = json.loads(start_msg)
        assert meta.get("type") == "start"
        conv_id = meta.get("conversationId")
        accent = meta.get("accent") or "American English"
        model = (meta.get("model") or "free").lower()
        print(f"[ws_upload] start conv_id={conv_id}, accent={accent}, model={model}")

        # ✅ Record current conversation's transcript count (for rebuild to only process current recording)
        from app.models.transcript import Transcript
        start_seq = await Transcript.filter(conversation_id=conv_id).count()
        print(f"[ws_upload] current transcript count: {start_seq}")

        # ✅ Use BytesIO to buffer audio in memory
        audio_buffer = BytesIO()
        _sessions[conv_id] = {
            "audio_buffer": audio_buffer,
            "accent": accent,
            "model": model,
            "start_seq": start_seq  # Record starting seq for rebuild
        }

        # 2. Loop to receive audio chunks
        while True:
            pkt = await ws.receive()
            
            # 2.1 Receive binary audio data
            if "bytes" in pkt and pkt["bytes"]:
                # ✅ Write to memory (non-blocking, very fast)
                audio_buffer.write(pkt["bytes"])
                continue
            
            # 2.2 Receive text control messages
            if "text" in pkt and pkt["text"]:
                try:
                    j = json.loads(pkt["text"])
                except Exception:
                    continue
                
                # 2.3 Received stop, enter conversation end flow
                if j.get("type") == "stop":
                    print(f"[ws_upload] ========== RECEIVED STOP MESSAGE conv_id={conv_id} ==========")
                    sys.stdout.flush()
                    
                    # ✨ Receive Web Speech text (optional)
                    webspeech_text = j.get("webspeech_text", "").strip()
                    if webspeech_text:
                        print(f"[ws_upload] Received Web Speech text: {len(webspeech_text)} chars")
                        sys.stdout.flush()
                        # Save to session
                        _sessions[conv_id]["webspeech_text"] = webspeech_text
                    
                    # ⚠️ Copy audio_buffer content to avoid interference between two functions
                    audio_buffer.seek(0)
                    audio_data_copy = audio_buffer.read()
                    audio_buffer.seek(0)  # Reset pointer for on_stop_and_publish
                    
                    # ✅ Path 1: Real-time feedback (ASR + TTS, keep original logic)
                    await on_stop_and_publish(conv_id, audio_buffer)
                    
                    # ✅ Path 2: Offline analysis (Diarization, async execution, non-blocking)
                    # Create new BytesIO object to avoid conflict with path 1
                    diarization_buffer = BytesIO(audio_data_copy)
                    asyncio.create_task(
                        on_conversation_end_diarization(conv_id, diarization_buffer)
                    )
                    
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    break
    except WebSocketDisconnect:
        print(f"[ws_upload] disconnect conv_id={conv_id or 'unknown'}")
    except Exception as e:
        print(f"[ws_upload] error: {repr(e)}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        # ✅ Clean up memory (note: diarization may still be executing asynchronously, so don't close buffer immediately)
        # Actual cleanup will be executed after diarization completes
        print(f"[ws_upload] closed conv_id={conv_id or 'unknown'}")

async def on_stop_and_publish(conv_id: str, audio_buffer: BytesIO):
    """
    Real-time feedback: ASR + TTS (keep original logic)
    This function handles results that users see immediately
    """
    print(f"[on_stop] ========== ENTERING on_stop_and_publish conv_id={conv_id} ==========")
    sys.stdout.flush()
    
    ses = _sessions.get(conv_id, {})
    accent = ses.get("accent", "American English")
    model = (ses.get("model") or "free").lower()

    # ✅ Get audio size first (before seek)
    audio_buffer.seek(0, 2)  # Move to end
    audio_size = audio_buffer.tell()
    audio_buffer.seek(0)  # Return to beginning
    
    print(f"[on_stop] begin conv_id={conv_id}, audio_size={audio_size} bytes")
    sys.stdout.flush()
    
    if audio_size == 0:
        print(f"[on_stop] ❌ No audio data for conv_id={conv_id}")
        sys.stdout.flush()
        return
    
    # Prepare temporary file (for ffmpeg transcoding)
    webm_bytes = audio_buffer.read()
    
    if len(webm_bytes) != audio_size:
        print(f"[on_stop] ⚠️ Warning: Expected {audio_size} bytes, got {len(webm_bytes)} bytes")
        sys.stdout.flush()
    
    if len(webm_bytes) == 0:
        print(f"[on_stop] ❌ No audio data for conv_id={conv_id}")
        sys.stdout.flush()
        return
    
    # ✅ Verify audio file header (WebM should start with 0x1A 0x45 0xDF 0xA3, or at least not all zeros)
    if len(webm_bytes) < 4:
        print(f"[on_stop] ❌ Audio file too small: {len(webm_bytes)} bytes")
        sys.stdout.flush()
        return
    
    # Check if it's a valid WebM/Opus file
    webm_header = webm_bytes[:4]
    if webm_header == b'\x00' * 4:
        print(f"[on_stop] ⚠️ Warning: Audio file appears to be all zeros (possibly incomplete)")
        sys.stdout.flush()
    else:
        print(f"[on_stop] ✅ Audio file header looks valid: {webm_header.hex()}")
        sys.stdout.flush()
    
    print(f"[on_stop] Creating temp webm file...")
    sys.stdout.flush()
    tmp_webm = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tmp_webm.write(webm_bytes)
    tmp_webm.flush()
    tmp_webm.close()
    print(f"[on_stop] Temp file created: {tmp_webm.name}")
    sys.stdout.flush()
    
    wav_path = None
    text = ""
    try:
        print(f"[on_stop] Starting ASR processing...")
        sys.stdout.flush()
        
        # ✅ Verify temporary WebM file size
        webm_file_size = os.path.getsize(tmp_webm.name)
        if webm_file_size != len(webm_bytes):
            print(f"[on_stop] ⚠️ Warning: Written file size ({webm_file_size}) != buffer size ({len(webm_bytes)})")
            sys.stdout.flush()
        
        # ASR transcription (✅ Force use OpenAI API for accuracy)
        wav_path = webm_to_wav_16k_mono(tmp_webm.name)
        
        # ✅ Verify WAV file size
        wav_file_size = os.path.getsize(wav_path)
        print(f"[on_stop] WAV file size: {wav_file_size} bytes")
        sys.stdout.flush()
        
        asr_result = await transcribe_audio(
            wav_path,
            language="en",          # ✅ Explicitly specify English (improve accuracy)
            word_timestamps=False   # Real-time ASR doesn't need word-level timestamps
        )
        text = asr_result.full_text
        print(f"[on_stop] ASR done, text_len={len(text)}, segments={len(asr_result.segments)}, using {asr_result.language or 'auto'}")
        
        # ✅ Check if transcription result is abnormally short
        if len(text) < 10 and audio_size > 10000:  # Large audio but short text
            print(f"[on_stop] ⚠️ Warning: Large audio ({audio_size} bytes) but short transcript ({len(text)} chars)")
            sys.stdout.flush()
        
        # ❌ Hallucination detection removed: Whisper is only transitional text, GPT ensures final quality
    except Exception as e:
        text = f"[ASR error] {e}"
        print(f"[on_stop] ASR error: {e}")
        import traceback
        traceback.print_exc()  # Print full error stack
        sys.stdout.flush()  # Force flush output
    finally:
        # Clean up temporary files
        try:
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception:
            pass
        try:
            if os.path.exists(tmp_webm.name):
                os.remove(tmp_webm.name)
        except Exception:
            pass

    # 1) ❌ No longer push Whisper text to frontend (keep Web Speech real-time text)
    # Whisper is only used as GPT input, GPT will push via transcripts_updated after formatting completes
    print(f"[on_stop] Whisper transcription completed (text_len={len(text)}), not pushing to frontend")
    print(f"[on_stop] Frontend will keep showing Web Speech text until GPT formatting completes")
    sys.stdout.flush()

    # 2) TTS synthesis and push audio - ❌ Disabled (already playing in real-time streaming translation, no need to repeat)
    # try:
    #     print(f"[on_stop] TTS begin model={model}, accent={accent}")
    #     if model == "free":
    #         await synth_and_stream_free(conv_id, text, accent)
    #     else:
    #         await synth_and_stream_paid(conv_id, text, accent)
    #     print(f"[on_stop] TTS done")
    # except Exception as e:
    #     print(f"[on_stop] TTS error: {e}")
    
    print(f"[on_stop] Skipping TTS (streaming translation is active)")


async def on_conversation_end_diarization(conv_id: str, audio_buffer: BytesIO):
    """
    Offline analysis: Diarization + Re-split Transcripts (async execution, non-blocking)
    
    Improved flow:
    1. Read complete audio from memory
    2. Transcode to WAV
    3. Use new ASR interface to get timestamped segments (better after local Whisper)
    4. Execute diarization analysis
    5. Merge ASR and Diarization results
    6. Delete old Transcripts, create new ones (split by speaker)
    7. Clean up memory
    """
    ses = _sessions.get(conv_id, {})
    
    try:
        print(f"[rebuild] ========== START DIARIZATION for conv_id={conv_id} ==========")
        sys.stdout.flush()
        
        # 1. Prepare audio data
        # Get audio size first (before seek)
        audio_buffer.seek(0, 2)  # Move to end
        audio_size = audio_buffer.tell()
        audio_buffer.seek(0)  # Return to beginning
        
        if audio_size == 0:
            print(f"[rebuild] ❌ no audio data, skipping")
            sys.stdout.flush()
            return
        
        webm_bytes = audio_buffer.read()
        
        if len(webm_bytes) != audio_size:
            print(f"[rebuild] ⚠️ Warning: Expected {audio_size} bytes, got {len(webm_bytes)} bytes")
            sys.stdout.flush()
        
        if len(webm_bytes) == 0:
            print(f"[rebuild] ❌ no audio data, skipping")
            sys.stdout.flush()
            return
        
        # Verify audio file integrity
        if len(webm_bytes) < 4:
            print(f"[rebuild] ❌ Audio file too small: {len(webm_bytes)} bytes")
            sys.stdout.flush()
            return
        
        webm_header = webm_bytes[:4]
        if webm_header == b'\x00' * 4:
            print(f"[rebuild] ⚠️ Warning: Audio file appears to be all zeros (possibly incomplete)")
            sys.stdout.flush()
        else:
            print(f"[rebuild] ✅ Audio file header looks valid: {webm_header.hex()}")
            sys.stdout.flush()
        
        print(f"[rebuild] audio size: {len(webm_bytes)} bytes")
        sys.stdout.flush()
        
        # 2. Write to temporary file (for ffmpeg transcoding)
        tmp_webm = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        tmp_webm.write(webm_bytes)
        tmp_webm.flush()
        tmp_webm.close()
        
        # 3. Transcode to WAV
        # Verify temporary WebM file size
        webm_file_size = os.path.getsize(tmp_webm.name)
        if webm_file_size != len(webm_bytes):
            print(f"[rebuild] ⚠️ Warning: Written file size ({webm_file_size}) != buffer size ({len(webm_bytes)})")
            sys.stdout.flush()
        
        wav_path = webm_to_wav_16k_mono(tmp_webm.name)
        
        # Verify WAV file size
        wav_file_size = os.path.getsize(wav_path)
        print(f"[rebuild] converted to WAV: {wav_path} ({wav_file_size} bytes)")
        sys.stdout.flush()
        
        # 4. Use new ASR interface to get timestamped segments
        from app.services import transcribe_audio
        from app.services.diarization import diarization_service
        from app.models.transcript import Transcript
        from app.models.conversation import Conversation
        
        try:
            print(f"[rebuild] Calling ASR service (OpenAI API)...")
            sys.stdout.flush()
            asr_result = await transcribe_audio(
                wav_path,
                language="en",        # Explicitly specify English (improve accuracy)
                word_timestamps=True  # Enable word-level timestamps
            )
            duration_str = f"{asr_result.duration_sec:.2f}s" if asr_result.duration_sec else "unknown"
            print(f"[rebuild] ✅ ASR done: {len(asr_result.segments)} segments, duration={duration_str}, text_len={len(asr_result.full_text)}")
            print(f"[rebuild]    Full text: {asr_result.full_text[:100]}...")
            
            # ✅ Check if transcription result is abnormally short
            if len(asr_result.full_text) < 10 and audio_size > 10000:
                print(f"[rebuild] ⚠️ Warning: Large audio ({audio_size} bytes) but short transcript ({len(asr_result.full_text)} chars)")
                sys.stdout.flush()
            
            sys.stdout.flush()
            
            # Hallucination detection removed: Whisper is only transitional text, GPT will rewrite and ensure quality
        except Exception as e:
            print(f"[rebuild] ASR failed: {e}")
            return
        
        # Choose processing method: GPT formatting > Diarization > Simple sentence splitting
        from app.config import settings
        from app.services.gpt_formatter import gpt_formatter
        
        # 5a. Prioritize GPT formatting (recommended)
        if settings.enable_gpt_formatting and gpt_formatter.is_available():
            # Check if Web Speech text exists, if so use comparison mode
            webspeech_text = ses.get("webspeech_text", "").strip()
            
            if webspeech_text:
                print(f"[rebuild] Using GPT to compare and merge Web Speech + Whisper...")
                print(f"[rebuild] Web Speech: {len(webspeech_text)} chars, Whisper: {len(asr_result.full_text)} chars")
                sys.stdout.flush()
                
                try:
                    result = await gpt_formatter.format_conversation_with_comparison(
                        webspeech_text=webspeech_text,
                        whisper_text=asr_result.full_text,
                        language=asr_result.language or "en"
                    )
                    formatted_sentences = result["sentences"]
                    print(f"[rebuild] ✅ GPT merged into {len(formatted_sentences)} sentences")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"[rebuild] ⚠️ Comparison failed: {e}, falling back to Whisper only")
                    import traceback
                    traceback.print_exc()
                    formatted_sentences = await gpt_formatter.format_conversation(
                        raw_text=asr_result.full_text,
                        language=asr_result.language or "en"
                    )
                    comparisons = []
            else:
                print(f"[rebuild] Using GPT to format conversation (Whisper only, no Web Speech)...")
                sys.stdout.flush()
                
                try:
                    formatted_sentences = await gpt_formatter.format_conversation(
                        raw_text=asr_result.full_text,
                        language=asr_result.language or "en"
                    )
                    
                    print(f"[rebuild] ✅ GPT formatted into {len(formatted_sentences)} sentences")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"[rebuild] ⚠️ GPT formatting failed: {e}")
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()
                    return
            
            # If diarization is enabled, use new matching algorithm (both modes supported)
            if settings.enable_diarization:
                print(f"[rebuild] Diarization enabled, using time-based speaker matching...")
                sys.stdout.flush()
                
                from app.services.diarization_matcher import (
                    align_sentences_with_whisper,
                    assign_speakers_to_sentences,
                    analyze_speaker_changes
                )
                
                try:
                    # Step 1: Convert Whisper segments to dictionary format
                    whisper_segments_dict = [
                        {
                            "start": seg.start_sec,
                            "end": seg.end_sec,
                            "text": seg.text
                        }
                        for seg in asr_result.segments
                    ]
                    print(f"[rebuild] Converted {len(whisper_segments_dict)} Whisper segments to dict format")
                    
                    # Step 2: Align GPT sentences with Whisper timestamps
                    aligned_sentences = align_sentences_with_whisper(
                        formatted_sentences,
                        whisper_segments_dict
                    )
                    print(f"[rebuild] ✅ Aligned {len(aligned_sentences)} sentences with Whisper timestamps")
                    
                    # Step 3: Execute diarization
                    print(f"[rebuild] Calling diarization service...")
                    sys.stdout.flush()
                    
                    if not diarization_service.is_available():
                        print(f"[rebuild] ⚠️ Diarization service NOT available, using GPT speaker labels")
                        final_sentences = aligned_sentences
                    else:
                        try:
                            diar_segments = await diarization_service.analyze_speakers(
                                wav_path,
                                num_speakers=None
                            )
                            print(f"[rebuild] ✅ Diarization done: {len(diar_segments)} segments")
                            
                            # Convert diarization timestamp format (milliseconds → seconds)
                            diar_segments_sec = [
                                {
                                    "start": seg["start_ms"] / 1000.0,
                                    "end": seg["end_ms"] / 1000.0,
                                    "speaker_id": seg["speaker_id"]
                                }
                                for seg in diar_segments
                            ]
                            print(f"[rebuild] Converted diarization timestamps to seconds")
                            
                            # Step 4: Use new algorithm to assign speakers to each sentence
                            final_sentences = assign_speakers_to_sentences(
                                aligned_sentences,
                                diar_segments_sec
                            )
                            print(f"[rebuild] ✅ Assigned speakers to {len(final_sentences)} sentences")
                            
                            # Analyze speaker change patterns
                            analysis = analyze_speaker_changes(final_sentences)
                            print(f"[rebuild] 📊 Speaker analysis: {analysis['speaker_changes']} changes, "
                                  f"{len(analysis['speakers'])} speakers, "
                                  f"{analysis['avg_sentences_per_turn']:.1f} sentences/turn")
                            
                        except Exception as diar_error:
                            print(f"[rebuild] ⚠️ Diarization failed: {diar_error}, using GPT speaker labels")
                            import traceback
                            traceback.print_exc()
                            final_sentences = aligned_sentences
                    
                    # Save final results (with timestamps and accurate speaker labels)
                    await save_formatted_sentences(conv_id, final_sentences, ses)
                    print(f"[rebuild] ✅ Successfully saved {len(final_sentences)} sentences with speakers")
                    
                except Exception as match_error:
                    print(f"[rebuild] ⚠️ Speaker matching failed: {match_error}, saving without diarization")
                    import traceback
                    traceback.print_exc()
                    await save_formatted_sentences(conv_id, formatted_sentences, ses)
            else:
                # Only use GPT speaker identification
                print(f"[rebuild] Diarization disabled, using GPT speaker labels only")
                await save_formatted_sentences(conv_id, formatted_sentences, ses)
            
            print(f"[rebuild] ✅ Successfully saved formatted sentences")
            sys.stdout.flush()
            
            # Push update notification to frontend (auto-refresh Dashboard)
            await channel.pub_text(conv_id, {
                "type": "transcripts_updated",
                "count": len(formatted_sentences)
            })
            print(f"[rebuild] 📤 Pushed update notification to frontend")
            sys.stdout.flush()
            
            # GPT formatting completed (may include diarization)
            return
        
        # 5b. Diarization (disabled, code retained)
        if settings.enable_diarization:
            print(f"[rebuild] Calling diarization service...")
            sys.stdout.flush()
            
            # Check if diarization service is available
            if not diarization_service.is_available():
                print(f"[rebuild] ❌ Diarization service NOT available!")
                sys.stdout.flush()
                return
            
            try:
                diar_segments = await diarization_service.analyze_speakers(
                    wav_path,
                    num_speakers=None
                )
            except Exception as e:
                print(f"[rebuild] ❌ Diarization error: {e}")
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
                return
            
            if not diar_segments:
                print(f"[rebuild] ❌ No diarization segments returned")
                sys.stdout.flush()
                return
            
            print(f"[rebuild] ✅ Diarization done: {len(diar_segments)} segments")
            sys.stdout.flush()
            
            # 6. Merge ASR and Diarization results
            merged = merge_asr_and_diarization(asr_result.segments, diar_segments)
            print(f"[rebuild] Merged: {len(merged)} segments")
            
            if not merged:
                print(f"[rebuild] merge failed, using diarization only")
                # Fallback: use full text + diarization segments
                merged = fallback_merge_with_full_text(asr_result.full_text, diar_segments)
                if not merged:
                    print(f"[rebuild] fallback also failed, keeping original transcripts")
                    return
            
            # 6.5 Merge consecutive segments from same speaker (solve sentence splitting issues)
            merged = merge_consecutive_same_speaker(merged)
            print(f"[rebuild] After merging consecutive: {len(merged)} segments")
            
            # 7. Only delete transcripts from current recording
            start_seq = ses.get("start_seq", 0)
            old_transcripts = await Transcript.filter(
                conversation_id=conv_id,
                seq__gt=start_seq  # Only delete seq > start_seq (current recording)
            ).all()
            old_count = len(old_transcripts)
            print(f"[rebuild] Deleting {old_count} transcripts (seq > {start_seq})")
            await Transcript.filter(conversation_id=conv_id, seq__gt=start_seq).delete()
            
            # 8. Create new Transcripts (split by speaker, starting from start_seq+1)
            conv = await Conversation.get(id=conv_id)
            conv_start_time = int(conv.started_at.timestamp() * 1000)  # Unix milliseconds
            
            # Note: Calculate time offset for current recording
            # If this is the second recording, need to add total duration of previous recordings
            existing_transcripts = await Transcript.filter(conversation_id=conv_id).order_by("-end_ms").first()
            time_offset = 0
            if existing_transcripts and existing_transcripts.end_ms:
                # Calculate offset relative to conversation start
                time_offset = existing_transcripts.end_ms - conv_start_time
                print(f"[rebuild] time_offset from previous recordings: {time_offset}ms")
            
            for i, seg in enumerate(merged, start=start_seq + 1):
                # Relative time + offset → absolute time
                absolute_start_ms = conv_start_time + time_offset + seg["start_ms"]
                absolute_end_ms = conv_start_time + time_offset + seg["end_ms"]
                
                await Transcript.create(
                    conversation_id=conv_id,
                    seq=i,
                    is_final=True,
                    start_ms=absolute_start_ms,
                    end_ms=absolute_end_ms,
                    text=seg["text"],
                    audio_url=None,
                    speaker_id=seg["speaker_id"]
                )
                print(f"[rebuild] Created transcript #{i}: {seg['speaker_id']}, {seg['text'][:50]}")
            
            print(f"[rebuild] ✅ Successfully rebuilt {len(merged)} transcripts (seq {start_seq+1} to {start_seq+len(merged)})")
        else:
            # 5c. Neither GPT nor Diarization enabled
            print(f"[rebuild] ⚠️ No formatting enabled, skipping post-processing")
            sys.stdout.flush()
        
        # 9. Clean up temporary files
        try:
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except Exception:
            pass
        try:
            if os.path.exists(tmp_webm.name):
                os.remove(tmp_webm.name)
        except Exception:
            pass
        
        print(f"[rebuild] completed for conv_id={conv_id}")
        
    except Exception as e:
        print(f"[rebuild] error for conv_id={conv_id}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 10. Clean up memory and session
        try:
            audio_buffer.close()
        except Exception:
            pass
        
        _sessions.pop(conv_id, None)
        print(f"[rebuild] cleaned up memory for conv_id={conv_id}")


def merge_asr_and_diarization(asr_segments: List, diar_segments: List[Dict]) -> List[Dict]:
    """
    Merge ASR and Diarization results (improved version, avoid text loss)
    
    Strategy:
    1. Iterate through each diarization segment (speaker segment)
    2. Find all ASR segments that overlap with it
    3. Merge text from these ASR segments to form a new transcript
    4. For ASR segments with low overlap, lower threshold or assign to closest speaker
    
    Parameters:
    - asr_segments: List[TranscriptSegment] from ASR service
    - diar_segments: [{"speaker_id": "SPEAKER_00", "start_ms": 0, "end_ms": 1000}, ...]
    
    Returns:
    [
        {"speaker_id": "SPEAKER_00", "start_ms": 0, "end_ms": 2000, "text": "Hello world"},
        {"speaker_id": "SPEAKER_01", "start_ms": 2000, "end_ms": 5000, "text": "Hi there"},
        ...
    ]
    """
    if not asr_segments or not diar_segments:
        return []
    
    merged = []
    used_asr_indices = set()  # Track used ASR segments
    
    # Strategy: Match ASR segments with high overlap
    # Use 40% threshold (balance accuracy and completeness)
    OVERLAP_THRESHOLD = 0.45  # Can adjust: 0.3 (loose) to 0.6 (strict)
    
    for diar_seg in diar_segments:
        diar_start = diar_seg["start_ms"]
        diar_end = diar_seg["end_ms"]
        speaker_id = diar_seg["speaker_id"]
        
        overlapping_texts = []
        
        for idx, asr_seg in enumerate(asr_segments):
            if idx in used_asr_indices:
                continue
                
            asr_start = asr_seg.start_ms
            asr_end = asr_seg.end_ms
            
            # Calculate overlap ratio
            overlap_start = max(diar_start, asr_start)
            overlap_end = min(diar_end, asr_end)
            overlap = overlap_end - overlap_start
            
            asr_duration = asr_end - asr_start
            if asr_duration > 0 and overlap > 0:
                overlap_ratio = overlap / asr_duration
                
                # Primary match: overlap >= 40%
                if overlap_ratio >= OVERLAP_THRESHOLD:
                    overlapping_texts.append(asr_seg.text.strip())
                    used_asr_indices.add(idx)
                    print(f"[merge] Matched ASR seg (overlap={overlap_ratio:.1%}): {asr_seg.text[:30]}")
        
        if overlapping_texts:
            merged.append({
                "speaker_id": speaker_id,
                "start_ms": diar_start,
                "end_ms": diar_end,
                "text": " ".join(overlapping_texts).strip()
            })
    
    # Handle unmatched ASR segments
    unmatched_asr = [(idx, seg) for idx, seg in enumerate(asr_segments) if idx not in used_asr_indices]
    
    if unmatched_asr:
        print(f"[merge] Warning: {len(unmatched_asr)} ASR segments not matched (may lose some text)")
        # Don't automatically assign unmatched text to ensure speaker identification accuracy
        # If higher text completeness is needed, can lower OVERLAP_THRESHOLD
        for idx, seg in unmatched_asr:
            print(f"[merge]   Unmatched: {seg.text[:50]}")
    
    # Sort by time
    merged.sort(key=lambda x: x["start_ms"])
    
    return merged


def merge_consecutive_same_speaker(segments: List[Dict]) -> List[Dict]:
    """
    Merge consecutive segments from same speaker (solve sentence splitting issues)
    
    Problem: Diarization may split one sentence from the same person into multiple segments
    Example: "I'm happy" and "on wednesday" are both SPEAKER_00, but split into two records
    
    Solution:
    1. Iterate through all segments
    2. If current segment and previous segment are same speaker, and time gap is short (< 2 seconds)
    3. Merge their text and time ranges
    
    Parameters:
    - segments: [{"speaker_id": "SPEAKER_00", "start_ms": 0, "end_ms": 2000, "text": "Hello"}, ...]
    
    Returns:
    - List[Dict]: Merged segments
    """
    if not segments:
        return []
    
    # Sort by time first
    segments = sorted(segments, key=lambda x: x["start_ms"])
    
    merged = []
    current = None
    
    # Time gap threshold (milliseconds): if gap between two segments is less than this, consider them consecutive
    MAX_GAP_MS = 2000  # 2 seconds
    
    for seg in segments:
        if current is None:
            # First segment
            current = {
                "speaker_id": seg["speaker_id"],
                "start_ms": seg["start_ms"],
                "end_ms": seg["end_ms"],
                "text": seg["text"]
            }
        elif (seg["speaker_id"] == current["speaker_id"] and 
              seg["start_ms"] - current["end_ms"] <= MAX_GAP_MS):
            # Same speaker, and time gap is short → merge
            current["end_ms"] = seg["end_ms"]
            # Merge text (preserve spaces)
            if current["text"] and seg["text"]:
                current["text"] = current["text"].strip() + " " + seg["text"].strip()
            elif seg["text"]:
                current["text"] = seg["text"]
            
            print(f"[merge_consecutive] Merged: '{seg['text'][:30]}...' into previous segment")
        else:
            # Different speaker, or time gap too long → save current segment, start new segment
            merged.append(current)
            current = {
                "speaker_id": seg["speaker_id"],
                "start_ms": seg["start_ms"],
                "end_ms": seg["end_ms"],
                "text": seg["text"]
            }
    
    # Add last segment
    if current:
        merged.append(current)
    
    print(f"[merge_consecutive] Reduced from {len(segments)} to {len(merged)} segments")
    return merged


def fallback_merge_with_full_text(full_text: str, diar_segments: List[Dict]) -> List[Dict]:
    """
    Fallback: Use full text + diarization time segments
    
    When ASR segments are unavailable or matching fails, distribute full text evenly by diarization segment count
    
    Parameters:
    - full_text: Complete transcription text
    - diar_segments: Diarization results
    
    Returns:
    - List[Dict]: merged segments
    """
    if not full_text.strip() or not diar_segments:
        return []
    
    # Simple strategy: distribute text by character count ratio
    words = full_text.split()
    if not words:
        return []
    
    total_duration = sum(d["end_ms"] - d["start_ms"] for d in diar_segments)
    if total_duration == 0:
        return []
    
    merged = []
    word_idx = 0
    
    for diar_seg in diar_segments:
        seg_duration = diar_seg["end_ms"] - diar_seg["start_ms"]
        seg_word_count = max(1, int(len(words) * (seg_duration / total_duration)))
        
        seg_words = words[word_idx:word_idx + seg_word_count]
        word_idx += seg_word_count
        
        if seg_words:
            merged.append({
                "speaker_id": diar_seg["speaker_id"],
                "start_ms": diar_seg["start_ms"],
                "end_ms": diar_seg["end_ms"],
                "text": " ".join(seg_words)
            })
    
    # If there are remaining words, add to last segment
    if word_idx < len(words) and merged:
        merged[-1]["text"] += " " + " ".join(words[word_idx:])
    
    print(f"[fallback_merge] Created {len(merged)} segments from full text")
    return merged


async def save_formatted_sentences(conv_id: str, sentences: List[Dict], ses: Dict):
    """
    Save GPT-formatted sentences to database
    
    Parameters:
        conv_id: Conversation ID
        sentences: List of sentences, supports two formats:
                  1. GPT only: [{"text": "...", "speaker": "A"}]
                  2. With diarization: [{"text": "...", "speaker_id": "SPEAKER_00", "start": 0.0, "end": 2.5}]
        ses: Session information
    """
    from app.models.transcript import Transcript
    from app.models.conversation import Conversation
    
    # 1. Delete old transcripts from current recording
    start_seq = ses.get("start_seq", 0)
    old_transcripts = await Transcript.filter(
        conversation_id=conv_id,
        seq__gt=start_seq
    ).all()
    old_count = len(old_transcripts)
    print(f"[save_formatted] Deleting {old_count} transcripts (seq > {start_seq})")
    await Transcript.filter(conversation_id=conv_id, seq__gt=start_seq).delete()
    
    # 2. Calculate time offset (if multiple recordings)
    conv = await Conversation.get(id=conv_id)
    conv_start_time = int(conv.started_at.timestamp() * 1000)  # Unix milliseconds
    
    existing_transcripts = await Transcript.filter(conversation_id=conv_id).order_by("-end_ms").first()
    time_offset = 0
    if existing_transcripts and existing_transcripts.end_ms:
        time_offset = existing_transcripts.end_ms - conv_start_time
        print(f"[save_formatted] time_offset from previous recordings: {time_offset}ms")
    
    # 3. Detect sentence format (whether has diarization timestamps)
    has_timestamps = sentences and "start" in sentences[0]
    
    if has_timestamps:
        print(f"[save_formatted] Using diarization timestamps")
    else:
        print(f"[save_formatted] Using estimated timestamps (no diarization)")
    
    # 4. Create new Transcripts
    for i, sent in enumerate(sentences, start=start_seq + 1):
        text = sent.get("text", "").strip()
        
        if not text:
            continue
        
        # Get speaker (supports two formats)
        if "speaker_id" in sent:
            # Diarization format: speaker_id = "SPEAKER_00"
            speaker_id = sent.get("speaker_id", "SPEAKER_00")
        elif "speaker" in sent:
            # GPT format: speaker = "A" → "SPEAKER_A"
            speaker_label = sent.get("speaker", "UNKNOWN")
            speaker_id = f"SPEAKER_{speaker_label}"
        else:
            speaker_id = "SPEAKER_00"
        
        # Get timestamps
        if has_timestamps:
            # Use real diarization timestamps (seconds → milliseconds)
            relative_start_ms = int(sent.get("start", 0.0) * 1000)
            relative_end_ms = int(sent.get("end", 0.0) * 1000)
        else:
            # Estimate timestamps (approximately 3 seconds per sentence)
            estimated_duration_per_sentence = 3000
            relative_start_ms = (i - start_seq - 1) * estimated_duration_per_sentence
            relative_end_ms = relative_start_ms + estimated_duration_per_sentence
        
        # Convert to absolute timestamps
        absolute_start_ms = conv_start_time + time_offset + relative_start_ms
        absolute_end_ms = conv_start_time + time_offset + relative_end_ms
        
        await Transcript.create(
            conversation_id=conv_id,
            seq=i,
            is_final=True,
            start_ms=absolute_start_ms,
            end_ms=absolute_end_ms,
            text=text,
            audio_url=None,
            speaker_id=speaker_id
        )
        
        # Show detailed logs
        if has_timestamps:
            confidence = sent.get("confidence", 0.0)
            gpt_speaker = sent.get("gpt_speaker", "")
            print(f"[save_formatted] #{i}: {speaker_id} (GPT:{gpt_speaker}, conf:{confidence:.2f}), "
                  f"{relative_start_ms/1000:.1f}s-{relative_end_ms/1000:.1f}s, '{text[:50]}'")
        else:
            print(f"[save_formatted] #{i}: {speaker_id}, '{text[:50]}'")


async def assign_speakers_to_transcripts(conv_id: str, diar_segments: List[Dict]):
    """
    Assign diarization results to existing transcripts (old method, as fallback)
    
    Strategy (fixed timestamp mismatch issue):
    1. If only 1 speaker → mark all transcripts as same
    2. If multiple speakers → assign by sequence rotation (simplified)
    
    Parameters:
    - conv_id: Conversation ID
    - diar_segments: [{"start_ms": 0, "end_ms": 3000, "speaker_id": "SPEAKER_00"}, ...]
    """
    from app.models.transcript import Transcript
    
    # 1. Get all transcripts for this conversation
    transcripts = await Transcript.filter(conversation_id=conv_id).order_by("seq")
    
    if not transcripts:
        print(f"[assign_speakers] no transcripts found for conv_id={conv_id}")
        return
    
    if not diar_segments:
        print(f"[assign_speakers] no diarization segments")
        return
    
    print(f"[assign_speakers] processing {len(transcripts)} transcripts")
    
    # 2. Extract all unique speaker_ids
    unique_speakers = sorted(set(seg["speaker_id"] for seg in diar_segments))
    print(f"[assign_speakers] detected {len(unique_speakers)} unique speakers: {unique_speakers}")
    
    # 3. Assignment strategy
    updated_count = 0
    
    if len(unique_speakers) == 1:
        # Strategy A: Only 1 speaker → mark all as same
        speaker_id = unique_speakers[0]
        for t in transcripts:
            t.speaker_id = speaker_id
            await t.save()
            updated_count += 1
        print(f"[assign_speakers] single speaker mode: all transcripts → {speaker_id}")
    
    else:
        # Strategy B: Multiple speakers → match by diarization time segments
        # Find closest speaker for each transcript
        for t in transcripts:
            # Since timestamps are Unix timestamps, cannot directly match
            # Use simplified strategy: assign by sequence rotation (assume alternating speakers)
            speaker_index = (t.seq - 1) % len(unique_speakers)
            t.speaker_id = unique_speakers[speaker_index]
            await t.save()
            updated_count += 1
    
    print(f"[assign_speakers] updated {updated_count}/{len(transcripts)} transcripts")
