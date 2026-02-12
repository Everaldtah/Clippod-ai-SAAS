"""AI analysis service for highlight detection."""
import re
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


class AnalysisService:
    """AI analysis service for video content analysis."""
    
    def __init__(self):
        self.embedding_model = None
        self.embedding_model_name = settings.EMBEDDING_MODEL
    
    def _load_embedding_model(self):
        """Lazy load the embedding model."""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
        return self.embedding_model
    
    async def analyze_video(
        self,
        transcription: Dict[str, Any],
        duration: float
    ) -> Dict[str, Any]:
        """Analyze video content and detect highlights."""
        segments = transcription.get("segments", [])
        full_text = transcription.get("text", "")
        
        if not segments:
            return {"highlights": [], "topics": [], "keywords": [], "sentiment": {}}
        
        # Analyze segments
        analyzed_segments = []
        for segment in segments:
            analysis = self._analyze_segment(segment, full_text)
            analyzed_segments.append({**segment, **analysis})
        
        # Detect highlights
        highlights = self._detect_highlights(analyzed_segments, duration)
        
        # Extract topics
        topics = self._extract_topics(full_text)
        
        # Extract keywords
        keywords = self._extract_keywords(full_text, segments)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(analyzed_segments)
        
        return {
            "highlights": highlights,
            "topics": topics,
            "keywords": keywords,
            "sentiment": sentiment,
            "segment_analysis": analyzed_segments
        }
    
    def _analyze_segment(
        self,
        segment: Dict[str, Any],
        full_text: str
    ) -> Dict[str, Any]:
        """Analyze a single segment."""
        text = segment.get("text", "")
        
        # Calculate hook probability
        hook_score = self._calculate_hook_score(text, segment.get("start", 0))
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(text)
        
        # Calculate viral score
        viral_score = self._calculate_viral_score(text, hook_score, engagement_score)
        
        # Detect emotions
        emotions = self._detect_emotions(text)
        
        # Detect topic shifts
        topic_shift = self._detect_topic_shift(text, full_text)
        
        return {
            "hook_score": hook_score,
            "engagement_score": engagement_score,
            "viral_score": viral_score,
            "emotions": emotions,
            "topic_shift": topic_shift
        }
    
    def _calculate_hook_score(self, text: str, start_time: float) -> float:
        """Calculate hook probability score (0-100)."""
        score = 50.0  # Base score
        
        # Hooks at the beginning are more valuable
        if start_time < 30:
            score += 15
        elif start_time < 60:
            score += 10
        
        # Question hooks
        if "?" in text:
            score += 10
        
        # Bold statements
        bold_indicators = ["fact", "truth", "secret", "never", "always", "everyone", "nobody"]
        for indicator in bold_indicators:
            if indicator in text.lower():
                score += 5
                break
        
        # Numbers and statistics
        if re.search(r'\d+', text):
            score += 5
        
        # Story hooks
        story_starters = ["when i", "i remember", "one day", "last year", "recently"]
        for starter in story_starters:
            if text.lower().startswith(starter):
                score += 10
                break
        
        return min(100, max(0, score))
    
    def _calculate_engagement_score(self, text: str) -> float:
        """Calculate engagement score (0-100)."""
        score = 50.0
        
        # Emotional words
        emotional_words = [
            "amazing", "incredible", "shocking", "surprising", "unbelievable",
            "love", "hate", "angry", "happy", "sad", "excited", "worried",
            "perfect", "terrible", "awesome", "awful", "fantastic"
        ]
        for word in emotional_words:
            if word in text.lower():
                score += 3
        
        # Call to action
        cta_words = ["subscribe", "follow", "like", "comment", "share", "check out"]
        for word in cta_words:
            if word in text.lower():
                score += 5
        
        # Controversial topics
        controversial = ["controversial", "debate", "argue", "wrong", "right", "truth"]
        for word in controversial:
            if word in text.lower():
                score += 5
        
        return min(100, max(0, score))
    
    def _calculate_viral_score(
        self,
        text: str,
        hook_score: float,
        engagement_score: float
    ) -> float:
        """Calculate viral likelihood score (0-100)."""
        # Combine scores with weights
        viral_score = (hook_score * 0.4) + (engagement_score * 0.4) + 20
        
        # Trending topics boost
        trending = ["ai", "crypto", "bitcoin", "money", "success", "motivation"]
        for topic in trending:
            if topic in text.lower():
                viral_score += 5
        
        return min(100, max(0, viral_score))
    
    def _detect_emotions(self, text: str) -> Dict[str, float]:
        """Detect emotions in text."""
        emotions = {
            "joy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
            "fear": 0.0,
            "surprise": 0.0,
            "neutral": 1.0
        }
        
        text_lower = text.lower()
        
        # Joy
        joy_words = ["happy", "joy", "excited", "amazing", "great", "awesome", "love", "perfect"]
        for word in joy_words:
            if word in text_lower:
                emotions["joy"] += 0.2
                emotions["neutral"] -= 0.1
        
        # Anger
        anger_words = ["angry", "hate", "terrible", "awful", "worst", "annoying"]
        for word in anger_words:
            if word in text_lower:
                emotions["anger"] += 0.2
                emotions["neutral"] -= 0.1
        
        # Surprise
        surprise_words = ["wow", "unbelievable", "shocking", "surprising", "incredible"]
        for word in surprise_words:
            if word in text_lower:
                emotions["surprise"] += 0.2
                emotions["neutral"] -= 0.1
        
        # Normalize
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v/total for k, v in emotions.items()}
        
        return emotions
    
    def _detect_topic_shift(self, text: str, context: str) -> bool:
        """Detect if segment represents a topic shift."""
        shift_indicators = [
            "but", "however", "on the other hand", "speaking of",
            "moving on", "let's talk about", "another thing"
        ]
        for indicator in shift_indicators:
            if indicator in text.lower():
                return True
        return False
    
    def _detect_highlights(
        self,
        segments: List[Dict[str, Any]],
        duration: float
    ) -> List[Dict[str, Any]]:
        """Detect highlight moments from analyzed segments."""
        highlights = []
        
        # Score each potential clip window
        window_size = 30  # 30 seconds
        stride = 5  # 5 second stride
        
        for start in range(0, int(duration) - window_size + 1, stride):
            end = start + window_size
            
            # Get segments in this window
            window_segments = [
                s for s in segments
                if s.get("start", 0) >= start and s.get("end", 0) <= end
            ]
            
            if not window_segments:
                continue
            
            # Calculate aggregate scores
            avg_viral = np.mean([s.get("viral_score", 0) for s in window_segments])
            avg_hook = np.mean([s.get("hook_score", 0) for s in window_segments])
            avg_engagement = np.mean([s.get("engagement_score", 0) for s in window_segments])
            
            # Combine transcript
            transcript = " ".join([s.get("text", "") for s in window_segments])
            
            # Get keywords
            keywords = self._extract_keywords(transcript, window_segments)[:5]
            
            highlights.append({
                "start": start,
                "end": end,
                "title": self._generate_title(transcript),
                "description": transcript[:200] + "..." if len(transcript) > 200 else transcript,
                "viral_score": round(avg_viral, 1),
                "hook_score": round(avg_hook, 1),
                "engagement_score": round(avg_engagement, 1),
                "keywords": keywords,
                "transcript": transcript
            })
        
        # Sort by viral score and return top highlights
        highlights.sort(key=lambda x: x["viral_score"], reverse=True)
        return highlights[:10]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text."""
        # Simple topic extraction based on frequency
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        
        # Filter common words
        stop_words = {
            "this", "that", "with", "from", "they", "have", "were",
            "been", "their", "would", "there", "could", "should"
        }
        
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top topics
        sorted_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, _ in sorted_topics[:5]]
    
    def _extract_keywords(
        self,
        text: str,
        segments: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract keywords from text."""
        # Combine topic extraction with segment-based keywords
        topics = self._extract_topics(text)
        
        # Add emphasis words
        emphasis_words = []
        for segment in segments:
            seg_text = segment.get("text", "")
            # Words in caps or with emphasis
            caps_words = re.findall(r'\b[A-Z]{3,}\b', seg_text)
            emphasis_words.extend(caps_words)
        
        # Combine and deduplicate
        keywords = list(dict.fromkeys(topics + emphasis_words))
        return keywords[:10]
    
    def _analyze_sentiment(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall sentiment."""
        if not segments:
            return {"overall": "neutral", "score": 0.0}
        
        # Aggregate emotions
        all_emotions = {"joy": 0, "anger": 0, "sadness": 0, "fear": 0, "surprise": 0, "neutral": 0}
        
        for segment in segments:
            emotions = segment.get("emotions", {})
            for emotion, score in emotions.items():
                all_emotions[emotion] = all_emotions.get(emotion, 0) + score
        
        # Normalize
        total = sum(all_emotions.values())
        if total > 0:
            all_emotions = {k: round(v/total, 3) for k, v in all_emotions.items()}
        
        # Determine overall sentiment
        dominant_emotion = max(all_emotions, key=all_emotions.get)
        
        return {
            "overall": dominant_emotion,
            "distribution": all_emotions,
            "positive": all_emotions.get("joy", 0) + all_emotions.get("surprise", 0) * 0.5,
            "negative": all_emotions.get("anger", 0) + all_emotions.get("sadness", 0) + all_emotions.get("fear", 0)
        }
    
    def _generate_title(self, text: str) -> str:
        """Generate a title from text."""
        # Use first sentence or first 50 chars
        sentences = text.split(".")
        if sentences:
            title = sentences[0].strip()
            if len(title) > 60:
                title = title[:57] + "..."
            return title
        return "Untitled Clip"
