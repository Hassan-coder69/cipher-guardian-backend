from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
import os
import logging
import json

logger = logging.getLogger(__name__)

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        "status": "healthy", 
        "message": "Cipher Guardian API is running.",
        "ai_enabled": os.environ.get('USE_AI_CLASSIFICATION', 'false') == 'true'
    })

class ClassifyTextView(APIView):
    """
    NEW: Classify plain text BEFORE encryption
    This endpoint doesn't need chatId/messageId since it's called before saving to Firestore
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
                logger.info(f"Classifying text with AI: {plain_text[:50]}...")
                flag = self.classify_with_ai(plain_text)
            else:
                logger.info(f"Classifying text with keywords: {plain_text[:50]}...")
                flag = self.classify_with_keywords(plain_text)
            
            logger.info(f"Text classified as: {flag}")
            
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
        """Classify using OpenAI GPT-4o-mini"""
        try:
            from openai import OpenAI
            
            api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_API_KEY')
            
            if not api_key:
                logger.error("No OpenAI API key found")
                return self.classify_with_keywords(text)
            
            client = OpenAI(api_key=api_key)
            
            system_prompt = """You are a strict content moderation assistant for a secure messaging app.

Classify messages into three categories:

🔴 RED (Dangerous/Harmful) - FLAG IMMEDIATELY:
- ANY insults or aggressive language directed at someone
- Examples: "fuck you", "you're stupid", "bitch", "asshole", "idiot" 
- Threats of violence or harm
- Harassment or bullying
- Hate speech or slurs
- Discriminatory language

🟡 YELLOW (Suspicious) - INVESTIGATE:
- Scam attempts ("you won", "claim prize")
- Phishing or fraud indicators
- Requests for sensitive information
- Spam or commercial content

🟢 GREEN (Safe) - ALLOW:
- Normal conversation ("hello", "hi", "how are you")
- Non-directed exclamations ("oh shit!", "damn")
- Friendly chat

RULES:
1. "fuck you" = RED | "oh fuck" = GREEN
2. Insults directed at person = RED
3. Simple words like "gay", "hello", "hi" = GREEN
4. When unsure, default to GREEN unless clearly hostile

RESPOND WITH ONLY: RED, YELLOW, or GREEN."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify: {text}"}
                ],
                max_tokens=10,
                temperature=0.1,
            )
            
            classification = response.choices[0].message.content.strip().upper()
            logger.info(f"GPT result: {classification}")
            
            if classification == "RED":
                return "red"
            elif classification == "YELLOW":
                return "yellow"
            else:
                return "green"
                
        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            return self.classify_with_keywords(text)

    def classify_with_keywords(self, text):
        """Fallback keyword classification"""
        text_lower = text.lower() if text else ""
        
        red_keywords = [
            "fuck you", "kill you", "bitch", "asshole", "cunt",
            "idiot", "stupid", "hate you", "kill", "murder", "attack"
        ]
        
        yellow_keywords = [
            "prize", "winner", "won", "congratulations",
            "claim", "free money", "verify account"
        ]
        
        for keyword in red_keywords:
            if keyword in text_lower:
                return "red"
        
        for keyword in yellow_keywords:
            if keyword in text_lower:
                return "yellow"
        
        return "green"


class ClassifyMessageView(APIView):
    """
    LEGACY: For Cloud Function to classify already-saved messages
    This is kept for backward compatibility but won't work well with encrypted text
    """
    def post(self, request, *args, **kwargs):
        data = request.data
        chat_id = data.get('chatId')
        message_id = data.get('messageId')
        encrypted_text = data.get('encryptedText')

        if not all([chat_id, message_id, encrypted_text]):
            return Response(
                {"error": "Missing required data"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Note: This will classify encrypted text (won't work well)
            logger.warning("Classifying encrypted text - consider using /classify-text/ endpoint instead")
            flag = self.classify_with_keywords(encrypted_text)
            
            logger.info(f"Message {message_id} classified as: {flag}")

            # Update Firestore
            db = firestore.client()
            message_ref = db.collection('chats').document(chat_id).collection('messages').document(message_id)
            message_ref.update({'flag': flag})
            
            return Response({
                "status": "success", 
                "flag": flag,
                "messageId": message_id,
                "method": "keywords (encrypted text)"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def classify_with_keywords(self, text):
        """Fallback keyword classification"""
        text_lower = text.lower() if text else ""
        
        red_keywords = [
            "fuck you", "kill you", "bitch", "asshole",
            "kill", "murder", "attack", "threat"
        ]
        
        yellow_keywords = [
            "prize", "winner", "congratulations you won"
        ]
        
        for keyword in red_keywords:
            if keyword in text_lower:
                return "red"
        
        for keyword in yellow_keywords:
            if keyword in text_lower:
                return "yellow"
        
        return "green"