# views.py - ENHANCED AI CLASSIFICATION
# Corrected version with proper Python syntax

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
import os
import logging
import json
import re

logger = logging.getLogger(__name__)

class ClassifyTextView(APIView):
    """
    Classify plain text BEFORE encryption with enhanced AI and fallback
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        plain_text = data.get('text')

        if not plain_text:
            return Response(
                {"error": "Missing text"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            use_ai = os.environ.get('USE_AI_CLASSIFICATION', 'false').lower() == 'true'
            
            if use_ai:
                logger.info(f"Classifying with AI: {plain_text[:50]}...")
                flag = self.classify_with_ai(plain_text)
            else:
                logger.info(f"Classifying with keywords: {plain_text[:50]}...")
                flag = self.classify_with_enhanced_keywords(plain_text)
            
            logger.info(f"Classification result: {flag}")
            
            return Response({
                "status": "success", 
                "flag": flag,
                "method": "ai" if use_ai else "keywords"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def classify_with_ai(self, text):
        """
        Enhanced AI classification with smarter prompts
        """
        try:
            from openai import OpenAI
            
            api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_API_KEY')
            
            if not api_key:
                logger.error("No OpenAI API key found")
                return self.classify_with_enhanced_keywords(text)
            
            client = OpenAI(api_key=api_key)
            
            # ✅ ENHANCED: More sophisticated system prompt
            system_prompt = """You are an advanced content moderation AI for a secure messaging platform.

Your task: Analyze messages and classify them into THREE categories based on INTENT and CONTEXT.

🔴 RED (Immediate Threat) - Dangerous, harmful, or illegal content:
├─ Direct threats: "I'll kill you", "I'm gonna hurt you", "You're dead"
├─ Explicit harassment: "fuck you", "you stupid bitch", "kill yourself"  
├─ Hate speech: slurs, discriminatory attacks on protected groups
├─ Violence: threats of physical harm, murder, assault
├─ Self-harm: encouraging suicide or self-injury
├─ Illegal activity: drug deals, weapon sales, explicit crimes
└─ Child exploitation: ANY content sexualizing minors

🟡 YELLOW (Suspicious) - Scams, phishing, or manipulation:
├─ Financial scams: "you won $1000", "claim your prize"
├─ Phishing: "verify your account", "click here urgent"
├─ Fraud attempts: "send money now", "wire transfer needed"
├─ Suspicious links: bit.ly with urgent language
├─ Identity theft: "confirm your password", "account suspended"
├─ Romance scams: rapid intimacy + money requests
└─ Job scams: "work from home", "easy money", unrealistic promises

🟢 GREEN (Safe) - Normal conversation:
├─ Friendly chat: "hello", "how are you", "what's up"
├─ Casual profanity NOT directed at person: "oh shit!", "that's fucking cool"
├─ Venting/expressing frustration: "I hate Mondays", "this sucks"
├─ Questions & normal discussion
├─ Sharing information, plans, opinions
└─ Jokes, memes, pop culture references (unless harmful)

CRITICAL RULES:
1. Context matters: "fuck" alone ≠ threat | "fuck you" = threat
2. Direction matters: "you're stupid" = RED | "this is stupid" = GREEN
3. Intent over words: Analyze if genuine threat vs casual expression
4. Default to GREEN unless clear hostile intent or scam pattern
5. Friends can curse together: "dude that's sick!" = GREEN
6. Venting ≠ threatening: "I hate my boss" = GREEN

RESPOND WITH ONLY ONE WORD: RED, YELLOW, or GREEN

Examples:
"fuck you asshole" → RED (direct insult)
"oh fuck that's amazing" → GREEN (excitement)
"you won $5000 click here" → YELLOW (scam)
"wanna grab coffee later?" → GREEN (normal)
"I'll beat your ass" → RED (threat)
"I'm so tired of this shit" → GREEN (venting)
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify this message:\n\n\"{text}\""}
                ],
                max_tokens=10,
                temperature=0.1,
            )
            
            classification = response.choices[0].message.content.strip().upper()
            logger.info(f"AI classification: {classification}")
            
            if classification == "RED":
                return "red"
            elif classification == "YELLOW":
                return "yellow"
            else:
                return "green"
                
        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            return self.classify_with_enhanced_keywords(text)

    def classify_with_enhanced_keywords(self, text):
        """
        ✅ ENHANCED: More comprehensive keyword detection with pattern matching
        """
        if not text:
            return "green"
            
        text_lower = text.lower().strip()
        
        # ========== RED PATTERNS (Threats & Harassment) ==========
        
        # Direct threats of violence
        violence_patterns = [
            r'\b(kill|murder|stab|shoot|beat|hurt|attack)\s+(you|him|her|them)\b',
            r'\b(i\'ll|ima|imma|gonna)\s+(kill|hurt|beat|fuck\s+up)\s+you\b',
            r'\byou(\'re|r)\s+(dead|gonna die)\b',
            r'\bwatch your back\b',
        ]
        
        # Direct personal insults (targeted harassment)
        insult_patterns = [
            r'\bfuck\s+you\b',
            r'\bfuk\s+u\b', 
            r'\byou(\'re|r)\s+(stupid|dumb|idiot|retard|worthless|pathetic)\b',
            r'\b(stupid|dumb|idiot)\s+(bitch|fuck|ass)\b',
            r'\bkill yourself\b',
            r'\bkys\b',  # "kill yourself" abbreviation
        ]
        
        # Hate speech and slurs
        hate_speech = [
            "nigger", "nigga", "faggot", "fag", "tranny", 
            "kike", "chink", "wetback", "raghead",
        ]
        
        # Check violence patterns
        for pattern in violence_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🔴 Violence pattern matched: {pattern}")
                return "red"
        
        # Check insult patterns  
        for pattern in insult_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🔴 Insult pattern matched: {pattern}")
                return "red"
        
        # Check hate speech (exact match)
        for slur in hate_speech:
            if slur in text_lower:
                logger.info(f"🔴 Hate speech detected: {slur}")
                return "red"
        
        # Additional direct red keywords
        red_keywords = [
            "i'll kill", "gonna kill", "going to kill",
            "fuck you", "screw you", "hate you",
            "piece of shit", "worthless", "die",
        ]
        
        for keyword in red_keywords:
            if keyword in text_lower:
                logger.info(f"🔴 Red keyword: {keyword}")
                return "red"
        
        # ========== YELLOW PATTERNS (Scams & Phishing) ==========
        
        # Financial scams
        scam_patterns = [
            r'\b(you won|you(\'ve| have) won|congratulations you)\b.*\$([\d,]+)',
            r'\b(claim|collect|redeem)\s+(your|the)\s+(prize|reward|money)\b',
            r'\b(bitcoin|btc|crypto|cryptocurrency)\s+(investment|opportunity)\b',
            r'\b(wire transfer|western union|gift card)\b',
            r'\bnigerian prince\b',
        ]
        
        # Phishing attempts
        phishing_patterns = [
            r'\bverify\s+(your|the)\s+account\b',
            r'\baccount\s+(suspended|locked|frozen)\b',
            r'\bunusual\s+activity\s+(detected|found)\b',
            r'\bconfirm\s+(your|the)\s+password\b',
            r'\b(urgent|immediate)\s+action\s+required\b',
            r'\bclick\s+here\s+(now|immediately|urgently)\b',
        ]
        
        # Check scam patterns
        for pattern in scam_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🟡 Scam pattern matched: {pattern}")
                return "yellow"
        
        # Check phishing patterns
        for pattern in phishing_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🟡 Phishing pattern matched: {pattern}")
                return "yellow"
        
        # Suspicious URL patterns with urgency
        if re.search(r'(bit\.ly|tinyurl|goo\.gl)', text_lower):
            urgency_words = ["urgent", "now", "immediately", "quick", "limited time"]
            if any(word in text_lower for word in urgency_words):
                logger.info("🟡 Suspicious link with urgency")
                return "yellow"
        
        yellow_keywords = [
            "you've won", "you won", "claim prize", "free money",
            "verify account", "send money", "act now", "limited time",
            "congratulations winner", "claim reward",
        ]
        
        for keyword in yellow_keywords:
            if keyword in text_lower:
                logger.info(f"🟡 Yellow keyword: {keyword}")
                return "yellow"
        
        # ========== DEFAULT: GREEN (Safe) ==========
        logger.info("🟢 No threats or scams detected")
        return "green"


def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        "status": "healthy", 
        "message": "Cipher Guardian API is running.",
        "ai_enabled": os.environ.get('USE_AI_CLASSIFICATION', 'false') == 'true'
    })