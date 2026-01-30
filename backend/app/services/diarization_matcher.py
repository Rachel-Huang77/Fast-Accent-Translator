# backend/app/services/diarization_matcher.py
"""
Diarization Matcher Service

Core features:
1. Align GPT-formatted sentences with Whisper timestamps
2. Assign speakers to each sentence using Diarization (based on time overlap)
3. Preserve GPT's sentence segmentation, unaffected by diarization fragmentation
"""

from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """
    Normalize text for matching (remove punctuation, case, extra spaces)
    """
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts (0.0 - 1.0)
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def align_sentences_with_whisper(
    gpt_sentences: List[Dict],  # [{"text": "...", "speaker": "A"}]
    whisper_segments: List[Dict]  # [{"start": 0.0, "end": 2.5, "text": "..."}]
) -> List[Dict]:
    """
    Align GPT-formatted sentences with Whisper timestamps
    
    Strategy:
    1. Match GPT sentences and Whisper segments in order
    2. Use text similarity to find best match
    3. Each GPT sentence may span multiple Whisper segments
    
    Returns: [{"start": 0.0, "end": 2.5, "text": "...", "gpt_speaker": "A"}]
    """
    if not gpt_sentences or not whisper_segments:
        return []
    
    aligned = []
    whisper_idx = 0
    
    for gpt_sent in gpt_sentences:
        gpt_text = gpt_sent.get("text", "")
        gpt_speaker = gpt_sent.get("speaker", "UNKNOWN")
        
        if not gpt_text.strip():
            continue
        
        # Collect potentially matching Whisper segments
        matched_segments = []
        best_start_idx = whisper_idx
        accumulated_text = ""
        
        # Search forward for matching segments
        for i in range(whisper_idx, len(whisper_segments)):
            seg = whisper_segments[i]
            seg_text = seg.get("text", "")
            accumulated_text += " " + seg_text
            
            similarity = text_similarity(gpt_text, accumulated_text)
            
            # If similarity is high, or enough content has been covered
            if similarity > 0.7 or len(normalize_text(accumulated_text)) >= len(normalize_text(gpt_text)):
                matched_segments.append(seg)
                whisper_idx = i + 1
                break
            elif similarity > 0.3:  # Partial match, continue accumulating
                matched_segments.append(seg)
        
        # If no good match found, use current segment
        if not matched_segments and whisper_idx < len(whisper_segments):
            matched_segments = [whisper_segments[whisper_idx]]
            whisper_idx += 1
        
        # Calculate time range
        if matched_segments:
            start_time = matched_segments[0].get("start", 0.0)
            end_time = matched_segments[-1].get("end", start_time + 2.0)
        else:
            # Fallback: Estimate time (0.1 seconds per character)
            if aligned:
                start_time = aligned[-1]["end"]
            else:
                start_time = 0.0
            duration = len(gpt_text) * 0.1
            end_time = start_time + duration
        
        aligned.append({
            "start": start_time,
            "end": end_time,
            "text": gpt_text,
            "gpt_speaker": gpt_speaker
        })
    
    return aligned


def assign_speakers_to_sentences(
    sentences: List[Dict],  # [{"start": 0.0, "end": 2.5, "text": "...", "gpt_speaker": "A"}]
    diar_segments: List[Dict]  # [{"start": 0.0, "end": 1.5, "speaker_id": "SPEAKER_00"}]
) -> List[Dict]:
    """
    Assign speaker to each GPT sentence (based on time overlap with diarization segments)
    
    Algorithm:
    1. For each sentence, find all time-overlapping diarization segments
    2. Calculate total overlap duration for each speaker
    3. Select speaker with maximum overlap duration
    
    Returns: [{"start": 0.0, "end": 2.5, "text": "...", "speaker_id": "SPEAKER_00"}]
    """
    labeled = []
    
    for i, sent in enumerate(sentences):
        sent_start = sent.get("start", 0.0)
        sent_end = sent.get("end", sent_start + 1.0)
        sent_text = sent.get("text", "")
        gpt_speaker = sent.get("gpt_speaker", "UNKNOWN")
        
        # Collect all overlapping diarization segments
        overlaps = {}  # {speaker_id: total_overlap_duration}
        
        for diar in diar_segments:
            diar_start = diar.get("start", 0.0)
            diar_end = diar.get("end", diar_start)
            diar_speaker = diar.get("speaker_id", "SPEAKER_00")
            
            # Check time overlap
            if diar_start < sent_end and diar_end > sent_start:
                # Calculate overlap duration
                overlap_start = max(sent_start, diar_start)
                overlap_end = min(sent_end, diar_end)
                overlap_dur = max(0, overlap_end - overlap_start)
                
                # Accumulate overlap duration for this speaker
                overlaps[diar_speaker] = overlaps.get(diar_speaker, 0.0) + overlap_dur
        
        # Select speaker with maximum overlap duration
        if overlaps:
            best_speaker = max(overlaps, key=overlaps.get)
            total_overlap = sum(overlaps.values())
            confidence = overlaps[best_speaker] / total_overlap if total_overlap > 0 else 0.0
            
            # If overlap too small (< 0.1 seconds), use fallback
            if total_overlap < 0.1:
                print(f"[diar_matcher] Warning: Very small overlap ({total_overlap:.2f}s) for sentence: '{sent_text[:30]}...'")
                best_speaker = labeled[-1]["speaker_id"] if labeled else "SPEAKER_00"
                confidence = 0.0
        else:
            # Fallback strategy
            if labeled:
                # Use previous sentence's speaker
                best_speaker = labeled[-1]["speaker_id"]
                print(f"[diar_matcher] No overlap, using previous speaker {best_speaker} for: '{sent_text[:30]}...'")
            else:
                # Use default speaker
                best_speaker = "SPEAKER_00"
                print(f"[diar_matcher] No overlap, using default SPEAKER_00 for: '{sent_text[:30]}...'")
            confidence = 0.0
        
        labeled.append({
            "start": sent_start,
            "end": sent_end,
            "text": sent_text,
            "speaker_id": best_speaker,
            "gpt_speaker": gpt_speaker,  # Keep GPT's recognition result as reference
            "confidence": confidence
        })
    
    return labeled


def merge_consecutive_same_speaker(
    sentences: List[Dict]
) -> List[Dict]:
    """
    Optional: Merge consecutive same-speaker sentences (for UI display)
    
    Note: This changes sentence count, may affect other logic, use with caution
    """
    if not sentences:
        return []
    
    merged = []
    current = sentences[0].copy()
    
    for sent in sentences[1:]:
        if sent["speaker_id"] == current["speaker_id"]:
            # Same speaker, merge
            current["text"] += " " + sent["text"]
            current["end"] = sent["end"]
        else:
            # Different speaker, save current and start new
            merged.append(current)
            current = sent.copy()
    
    # Add last one
    merged.append(current)
    
    return merged


def analyze_speaker_changes(sentences: List[Dict]) -> Dict:
    """
    Analyze speaker change patterns (for debugging and quality assessment)
    """
    if not sentences:
        return {
            "total_sentences": 0,
            "speaker_changes": 0,
            "speakers": []
        }
    
    speakers = set()
    changes = 0
    
    for i, sent in enumerate(sentences):
        speaker = sent.get("speaker_id", "UNKNOWN")
        speakers.add(speaker)
        
        if i > 0 and sent.get("speaker_id") != sentences[i-1].get("speaker_id"):
            changes += 1
    
    return {
        "total_sentences": len(sentences),
        "speaker_changes": changes,
        "speakers": sorted(list(speakers)),
        "avg_sentences_per_turn": len(sentences) / (changes + 1) if changes >= 0 else 0
    }

