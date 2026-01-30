# backend/app/services/hallucination_detector.py
"""
Hallucination Detection Service (for ASR transcription result validation)

Features:
1. Whisper confidence analysis
2. Repetition detection
3. Semantic coherence checking
"""
import re
from typing import List, Dict, Optional


class HallucinationDetector:
    """
    ASR Hallucination Detector
    
    Uses multiple strategies to detect and filter hallucinated content in ASR transcriptions
    """
    
    def __init__(self):
        self.history_texts = []  # Store recent transcription texts (for coherence checking)
        self.max_history = 5
    
    def detect_from_whisper(
        self, 
        text: str, 
        segments: List[Dict] = None
    ) -> Dict:
        """
        Comprehensive detection function (integrates all detection strategies)
        
        Parameters:
            text: Complete transcription text
            segments: Whisper segment results (containing timestamps and confidence)
                     Format: [{"text": "...", "start": 0.0, "end": 2.0, "avg_logprob": -0.3}, ...]
        
        Returns:
            {
                "is_hallucination": bool,
                "reason": str,
                "confidence": float,
                "details": dict
            }
        """
        if not text or not text.strip():
            return {
                "is_hallucination": True,
                "reason": "empty_text",
                "confidence": 0.0,
                "details": {}
            }
        
        # 1. Whisper confidence analysis
        confidence_check = self._check_whisper_confidence(text, segments)
        if confidence_check["is_hallucination"]:
            return confidence_check
        
        # 2. Repetition detection
        repetition_check = self._check_repetition(text)
        if repetition_check["is_hallucination"]:
            return repetition_check
        
        # 3. Semantic coherence checking
        coherence_check = self._check_semantic_coherence(text)
        if coherence_check["is_hallucination"]:
            return coherence_check
        
        # 4. Suspicious pattern detection
        pattern_check = self._check_suspicious_patterns(text)
        if pattern_check["is_hallucination"]:
            return pattern_check
        
        # Passed all checks
        return {
            "is_hallucination": False,
            "reason": "valid",
            "confidence": confidence_check.get("confidence", 0.8),
            "details": {
                "text_length": len(text),
                "word_count": len(text.split())
            }
        }
    
    def _check_whisper_confidence(
        self, 
        text: str, 
        segments: List[Dict] = None
    ) -> Dict:
        """
        Detection 1: Whisper confidence analysis
        
        Checks:
        1. Average log probability
        2. Ratio of low-confidence segments
        3. Abnormal speech rate (too fast/too slow)
        """
        if not segments:
            # No segment information, use default confidence
            return {
                "is_hallucination": False,
                "reason": "no_segments",
                "confidence": 0.7
            }
        
        # Extract confidence metrics
        confidences = []
        durations = []
        
        for seg in segments:
            # avg_logprob: close to 0 = high confidence, close to -1 or lower = low confidence
            # Support both dict and object formats
            if isinstance(seg, dict):
                avg_logprob = seg.get('avg_logprob', seg.get('avg_log_prob', -0.5))
                start = seg.get('start', 0)
                end = seg.get('end', 0)
            else:
                # Whisper object format
                avg_logprob = getattr(seg, 'avg_logprob', getattr(seg, 'avg_log_prob', -0.5))
                start = getattr(seg, 'start', 0)
                end = getattr(seg, 'end', 0)
            
            # Convert to 0-1 confidence score
            # Whisper's avg_logprob is usually between -1.0 and 0.0
            confidence = max(0, min(1, (avg_logprob + 1.0)))
            confidences.append(confidence)
            
            # Calculate duration
            duration = end - start
            if duration > 0:
                durations.append(duration)
        
        if not confidences:
            return {
                "is_hallucination": False,
                "reason": "no_confidence_data",
                "confidence": 0.7
            }
        
        # 1. Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences)
        
        # 2. Calculate low confidence ratio
        low_confidence_count = sum(1 for c in confidences if c < 0.5)
        low_confidence_ratio = low_confidence_count / len(confidences)
        
        # 3. Check speech rate (words/second)
        if durations:
            total_duration = sum(durations)
            words = text.split()
            words_per_second = len(words) / max(total_duration, 0.1)
            
            # Normal speech rate: 1.5-4.5 words/second (English)
            speed_abnormal = words_per_second < 0.5 or words_per_second > 6.0
        else:
            speed_abnormal = False
            words_per_second = 0
        
        # Determine if hallucination (✅ Relaxed thresholds to reduce false positives)
        if avg_confidence < 0.3:  # Reduced from 0.4 to 0.3
            return {
                "is_hallucination": True,
                "reason": f"low_avg_confidence: {avg_confidence:.2f}",
                "confidence": avg_confidence,
                "details": {
                    "avg_confidence": avg_confidence,
                    "low_confidence_ratio": low_confidence_ratio
                }
            }
        
        if low_confidence_ratio > 0.7:  # Increased from 0.6 to 0.7
            return {
                "is_hallucination": True,
                "reason": f"high_low_confidence_ratio: {low_confidence_ratio:.2f}",
                "confidence": avg_confidence,
                "details": {
                    "low_confidence_ratio": low_confidence_ratio,
                    "low_segments": low_confidence_count
                }
            }
        
        if speed_abnormal:
            return {
                "is_hallucination": True,
                "reason": f"abnormal_speech_rate: {words_per_second:.2f} words/sec",
                "confidence": avg_confidence,
                "details": {
                    "words_per_second": words_per_second
                }
            }
        
        # Passed check
        return {
            "is_hallucination": False,
            "reason": "valid_confidence",
            "confidence": avg_confidence,
            "details": {
                "avg_confidence": avg_confidence,
                "low_confidence_ratio": low_confidence_ratio
            }
        }
    
    def _check_repetition(self, text: str) -> Dict:
        """
        Detection 2: Repetition detection
        
        Checks:
        1. Consecutive repeated words
        2. Phrase-level repetition
        3. Full sentence repetition
        """
        words = text.lower().split()
        
        if len(words) < 2:
            return {"is_hallucination": False, "reason": "too_short", "confidence": 0.7}
        
        # 1. Detect consecutive repeated words
        max_word_repeat = 0
        current_repeat = 1
        
        for i in range(1, len(words)):
            if words[i] == words[i-1]:
                current_repeat += 1
                max_word_repeat = max(max_word_repeat, current_repeat)
            else:
                current_repeat = 1
        
        # Consecutive repetition 4+ times → hallucination (✅ Increased from 3 to 4 to reduce false positives)
        if max_word_repeat >= 4:
            return {
                "is_hallucination": True,
                "reason": f"repeated_word: {max_word_repeat} times",
                "confidence": 0.3,
                "details": {"max_repeat": max_word_repeat}
            }
        
        # 2. Detect phrase repetition (2-5 word combinations)
        for phrase_len in [2, 3, 4, 5]:
            if len(words) < phrase_len * 2:
                continue
            
            for i in range(len(words) - phrase_len * 2 + 1):
                phrase = ' '.join(words[i:i+phrase_len])
                rest_text = ' '.join(words[i+phrase_len:])
                
                # Check if phrase repeats later
                if phrase in rest_text:
                    # Calculate repetition count
                    repeat_count = text.lower().count(phrase)
                    if repeat_count >= 3:
                        return {
                            "is_hallucination": True,
                            "reason": f"repeated_phrase: '{phrase}' ({repeat_count} times)",
                            "confidence": 0.4,
                            "details": {
                                "phrase": phrase,
                                "repeat_count": repeat_count
                            }
                        }
        
        # 3. Detect sentence-level repetition (split by punctuation)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip().lower() for s in sentences if s.strip()]
        
        if len(sentences) >= 2:
            seen = set()
            for sent in sentences:
                if sent in seen and len(sent) > 10:  # At least 10 characters
                    return {
                        "is_hallucination": True,
                        "reason": f"repeated_sentence: '{sent[:30]}...'",
                        "confidence": 0.4,
                        "details": {"sentence": sent}
                    }
                seen.add(sent)
        
        # Passed check
        return {
            "is_hallucination": False,
            "reason": "no_repetition",
            "confidence": 0.8
        }
    
    def _check_semantic_coherence(self, text: str) -> Dict:
        """
        Detection 3: Semantic coherence checking
        
        Checks:
        1. Topic relevance with historical texts (keyword overlap)
        2. Sudden topic shifts
        3. Cross-text repetition
        """
        if not self.history_texts:
            # First transcription, no history
            self.history_texts.append(text)
            return {
                "is_hallucination": False,
                "reason": "no_history",
                "confidence": 0.7
            }
        
        # Extract keywords (simplified: remove stopwords)
        def extract_keywords(t: str) -> set:
            # English stopwords
            stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
                'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their', 'this',
                'that', 'these', 'those', 'have', 'has', 'had', 'do', 'does', 'did'
            }
            words = re.findall(r'\w+', t.lower())
            return set(w for w in words if w not in stopwords and len(w) > 2)
        
        current_keywords = extract_keywords(text)
        
        # Calculate keyword overlap with recent transcriptions
        recent_texts = self.history_texts[-3:]  # Only look at last 3
        overlaps = []
        
        for hist_text in recent_texts:
            hist_keywords = extract_keywords(hist_text)
            if hist_keywords:
                overlap = len(current_keywords & hist_keywords)
                overlap_ratio = overlap / max(len(current_keywords), 1)
                overlaps.append(overlap_ratio)
        
        # If overlap with all historical texts is very low → possible topic shift
        if overlaps:
            max_overlap = max(overlaps)
            
            # Only alert if there's enough history (>= 2) and overlap is extremely low
            if len(self.history_texts) >= 2 and max_overlap < 0.05:
                return {
                    "is_hallucination": True,
                    "reason": f"topic_shift: overlap={max_overlap:.2%}",
                    "confidence": 0.5,
                    "details": {
                        "overlap_ratio": max_overlap,
                        "current_keywords": list(current_keywords)[:10]
                    }
                }
        
        # Detect cross-text repetition (same sentence appearing in different transcriptions)
        normalized_text = text.lower().strip()
        for hist_text in recent_texts:
            if normalized_text == hist_text.lower().strip() and len(normalized_text) > 20:
                return {
                    "is_hallucination": True,
                    "reason": "duplicate_across_transcripts",
                    "confidence": 0.4,
                    "details": {"text": normalized_text[:50]}
                }
        
        # Passed check, update history
        self.history_texts.append(text)
        if len(self.history_texts) > self.max_history:
            self.history_texts.pop(0)
        
        return {
            "is_hallucination": False,
            "reason": "coherent",
            "confidence": 0.8,
            "details": {
                "overlap_ratio": max(overlaps) if overlaps else 0
            }
        }
    
    def _check_suspicious_patterns(self, text: str) -> Dict:
        """
        Detection 4: Suspicious text patterns
        
        Checks:
        1. Pure punctuation
        2. Repeated character patterns
        3. Abnormal length
        """
        # 1. Pure punctuation or whitespace
        if re.match(r'^[\s\.\,\!\?\;\:]+$', text):
            return {
                "is_hallucination": True,
                "reason": "only_punctuation",
                "confidence": 0.0
            }
        
        # 2. Repeated character patterns (e.g., "aaaaaaa")
        if re.search(r'(.)\1{6,}', text):
            return {
                "is_hallucination": True,
                "reason": "repeated_characters",
                "confidence": 0.2
            }
        
        # 3. Too short (< 3 characters)
        if len(text.strip()) < 3:
            return {
                "is_hallucination": True,
                "reason": "text_too_short",
                "confidence": 0.3
            }
        
        # 4. Too many special characters (> 30%)
        special_char_count = len(re.findall(r'[^\w\s]', text))
        char_count = len(text.replace(' ', ''))
        if char_count > 0:
            special_ratio = special_char_count / char_count
            if special_ratio > 0.3:
                return {
                    "is_hallucination": True,
                    "reason": f"too_many_special_chars: {special_ratio:.1%}",
                    "confidence": 0.4,
                    "details": {"special_ratio": special_ratio}
                }
        
        # Passed check
        return {
            "is_hallucination": False,
            "reason": "normal_pattern",
            "confidence": 0.8
        }
    
    def reset_history(self):
        """Reset history (called when new session starts)"""
        self.history_texts.clear()


# Global singleton
hallucination_detector = HallucinationDetector()

