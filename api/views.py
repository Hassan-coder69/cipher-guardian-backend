# views.py - ENHANCED AI CLASSIFICATION + USER SAFETY PROFILES
# Updated with CORS support, profile tracking, and AI overview generation

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
import os
import logging
import json
import re

logger = logging.getLogger(__name__)
db = firestore.client()


class ClassifyTextView(APIView):
    """
    Classify plain text BEFORE encryption with enhanced AI and fallback
    NOW ALSO UPDATES USER SAFETY PROFILE
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        plain_text = data.get('text')
        user_id = data.get('userId')  # NEW: Get sender's user ID

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
            
            # NEW: Update user's safety profile if userId provided
            if user_id:
                try:
                    update_user_safety_profile(user_id, flag)
                    logger.info(f"Updated safety profile for user {user_id}")
                except Exception as profile_error:
                    logger.error(f"Failed to update user profile: {profile_error}")
                    # Don't fail the classification if profile update fails
            
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

RESPOND WITH ONLY ONE WORD: RED, YELLOW, or GREEN"""

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
        Enhanced keyword detection with pattern matching
        """
        if not text:
            return "green"
            
        text_lower = text.lower().strip()
        
        # ========== RED PATTERNS (Threats & Harassment) ==========
        
        violence_patterns = [
            r'\b(kill|murder|stab|shoot|beat|hurt|attack)\s+(you|him|her|them)\b',
            r'\b(i\'ll|ima|imma|gonna)\s+(kill|hurt|beat|fuck\s+up)\s+you\b',
            r'\byou(\'re|r)\s+(dead|gonna die)\b',
            r'\bwatch your back\b',
        ]
        
        insult_patterns = [
            r'\bfuck\s+you\b',
            r'\bfuk\s+u\b', 
            r'\byou(\'re|r)\s+(stupid|dumb|idiot|retard|worthless|pathetic)\b',
            r'\b(stupid|dumb|idiot)\s+(bitch|fuck|ass)\b',
            r'\bkill yourself\b',
            r'\bkys\b',
        ]
        
        hate_speech = [
            "nigger", "nigga", "faggot", "fag", "tranny", 
            "kike", "chink", "wetback", "raghead",
        ]
        
        for pattern in violence_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🔴 Violence pattern matched: {pattern}")
                return "red"
        
        for pattern in insult_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🔴 Insult pattern matched: {pattern}")
                return "red"
        
        for slur in hate_speech:
            if slur in text_lower:
                logger.info(f"🔴 Hate speech detected: {slur}")
                return "red"
        
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
        
        scam_patterns = [
            r'\b(you won|you(\'ve| have) won|congratulations you)\b.*\$([\d,]+)',
            r'\b(claim|collect|redeem)\s+(your|the)\s+(prize|reward|money)\b',
            r'\b(bitcoin|btc|crypto|cryptocurrency)\s+(investment|opportunity)\b',
            r'\b(wire transfer|western union|gift card)\b',
            r'\bnigerian prince\b',
        ]
        
        phishing_patterns = [
            r'\bverify\s+(your|the)\s+account\b',
            r'\baccount\s+(suspended|locked|frozen)\b',
            r'\bunusual\s+activity\s+(detected|found)\b',
            r'\bconfirm\s+(your|the)\s+password\b',
            r'\b(urgent|immediate)\s+action\s+required\b',
            r'\bclick\s+here\s+(now|immediately|urgently)\b',
        ]
        
        for pattern in scam_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🟡 Scam pattern matched: {pattern}")
                return "yellow"
        
        for pattern in phishing_patterns:
            if re.search(pattern, text_lower):
                logger.info(f"🟡 Phishing pattern matched: {pattern}")
                return "yellow"
        
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
        
        logger.info("🟢 No threats or scams detected")
        return "green"


# ========== NEW: USER SAFETY PROFILE FUNCTIONS ==========

def update_user_safety_profile(user_id, flag):
    """
    Update user's public safety profile after message classification
    This maintains overall reputation visible to all users
    """
    flag = flag.lower()
    
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            logger.warning(f"User {user_id} not found, skipping profile update")
            return
        
        # Get current profile or initialize
        user_data = user_doc.to_dict()
        current_profile = user_data.get('safetyProfile', {
            'totalMessages': 0,
            'greenCount': 0,
            'yellowCount': 0,
            'redCount': 0,
        })
        
        # Update counts
        updated_profile = {
            'totalMessages': current_profile.get('totalMessages', 0) + 1,
            'greenCount': current_profile.get('greenCount', 0) + (1 if flag == 'green' else 0),
            'yellowCount': current_profile.get('yellowCount', 0) + (1 if flag == 'yellow' else 0),
            'redCount': current_profile.get('redCount', 0) + (1 if flag == 'red' else 0),
            'lastUpdated': firestore.SERVER_TIMESTAMP
        }
        
        # Calculate scores
        total = updated_profile['totalMessages']
        if total > 0:
            updated_profile['greenPercentage'] = round((updated_profile['greenCount'] / total) * 100, 1)
            updated_profile['yellowPercentage'] = round((updated_profile['yellowCount'] / total) * 100, 1)
            updated_profile['redPercentage'] = round((updated_profile['redCount'] / total) * 100, 1)
            updated_profile['safetyScore'] = round((updated_profile['greenCount'] / total) * 100)
            updated_profile['riskScore'] = round(
                (updated_profile['redCount'] * 10 + updated_profile['yellowCount'] * 3) / total, 1
            )
        else:
            updated_profile['greenPercentage'] = 100.0
            updated_profile['yellowPercentage'] = 0.0
            updated_profile['redPercentage'] = 0.0
            updated_profile['safetyScore'] = 100
            updated_profile['riskScore'] = 0.0
        
        # Update Firestore
        user_ref.update({'safetyProfile': updated_profile})
        logger.info(f"✅ Updated safety profile for user {user_id}: Score={updated_profile['safetyScore']}")
        
    except Exception as e:
        logger.error(f"❌ Error updating user safety profile: {str(e)}")
        raise


@csrf_exempt
@require_http_methods(["POST"])
def generate_overview(request):
    """
    Generate AI overview of user's safety profile
    Called from frontend ComprehensiveUserSafetyProfile component
    """
    try:
        data = json.loads(request.body)
        user_data = data.get('userData', {})
        
        if not user_data:
            return JsonResponse({'error': 'Missing userData'}, status=400)
        
        from openai import OpenAI
        
        api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_API_KEY')
        
        if not api_key:
            return JsonResponse({
                'overview': 'AI overview unavailable - API key not configured.'
            })
        
        client = OpenAI(api_key=api_key)
        
        # Build contextual prompt
        user_name = user_data.get('userName', 'This user')
        total_messages = user_data.get('totalMessages', 0)
        green_pct = user_data.get('greenPercentage', 0)
        yellow_pct = user_data.get('yellowPercentage', 0)
        red_pct = user_data.get('redPercentage', 0)
        risk_score = user_data.get('riskScore', 0)
        safety_score = user_data.get('safetyScore', 100)
        is_public = user_data.get('isPublicProfile', False)
        
        prompt = f"""Provide a brief, professional 2-3 sentence safety assessment for this messaging platform user:

User: {user_name}
Data Source: {"Overall reputation across all conversations" if is_public else "Direct conversations with requester"}
Total Messages Analyzed: {total_messages}
Classification Results:
- Safe (Green): {green_pct}%
- Suspicious (Yellow): {yellow_pct}%
- Dangerous (Red): {red_pct}%
Overall Safety Score: {safety_score}/100
Risk Score: {risk_score}/10

Provide an objective assessment helping others decide whether to trust this person. Be concise and balanced."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional safety analyst providing brief, objective assessments of user behavior for a secure messaging platform. Be concise, factual, and balanced."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        overview = response.choices[0].message.content.strip()
        logger.info(f"Generated AI overview for user with {total_messages} messages")
        
        return JsonResponse({'overview': overview})
        
    except Exception as e:
        logger.error(f"Error generating overview: {str(e)}")
        return JsonResponse({
            'error': 'Failed to generate AI overview',
            'details': str(e)
        }, status=500)


def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        "status": "healthy", 
        "message": "Cipher Guardian API is running.",
        "ai_enabled": os.environ.get('USE_AI_CLASSIFICATION', 'false') == 'true',
        "features": {
            "classification": True,
            "user_profiles": True,
            "ai_overview": True
        }
    })