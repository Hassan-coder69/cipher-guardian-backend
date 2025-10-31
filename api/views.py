from django.http import JsonResponse
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

class ClassifyMessageView(APIView):
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
            # Check if AI classification is enabled
            use_ai = os.environ.get('USE_AI_CLASSIFICATION', 'false').lower() == 'true'
            
            if use_ai:
                logger.info(f"Using AI classification for message {message_id}")
                # Get conversation context (last 10 messages)
                context = self.get_conversation_context(chat_id, message_id)
                flag = self.classify_with_ai(encrypted_text, context)
            else:
                logger.info(f"Using keyword classification for message {message_id}")
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
                "chatId": chat_id,
                "method": "ai" if use_ai else "keywords"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_conversation_context(self, chat_id, current_message_id):
        """
        Fetch the last 10 messages from the conversation for context
        """
        try:
            db = firestore.client()
            messages_ref = db.collection('chats').document(chat_id).collection('messages')
            
            # Get last 10 messages ordered by creation time
            messages_query = messages_ref.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(10)
            messages = messages_query.stream()
            
            context = []
            for msg in messages:
                msg_data = msg.to_dict()
                # Don't include the current message in context
                if msg.id != current_message_id:
                    context.append({
                        'text': msg_data.get('text', ''),
                        'senderId': msg_data.get('senderId', ''),
                        'timestamp': msg_data.get('createdAt')
                    })
            
            # Reverse to get chronological order (oldest first)
            context.reverse()
            logger.info(f"Retrieved {len(context)} messages for context")
            return context
            
        except Exception as e:
            logger.warning(f"Could not fetch context: {str(e)}")
            return []

    def classify_with_ai(self, text, context=None):
        """Classify using OpenAI GPT-4o-mini with conversation context"""
        try:
            from openai import OpenAI
            
            api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_API_KEY')
            
            if not api_key:
                logger.error("No OpenAI API key found")
                return self.classify_with_keywords(text)
            
            client = OpenAI(api_key=api_key)
            
            # Build context string
            context_str = ""
            if context and len(context) > 0:
                context_str = "\n\nPrevious conversation context (last few messages):\n"
                for i, msg in enumerate(context, 1):
                    # Show only first 50 chars of each message to save tokens
                    preview = msg['text'][:50] + "..." if len(msg['text']) > 50 else msg['text']
                    context_str += f"Message {i}: {preview}\n"
            
            system_prompt = """You are a content moderation assistant for a secure messaging app.

Classify messages into three categories based on INTENT and CONTEXT:

🔴 RED (Dangerous/Harmful) - REAL THREATS:
- Credible threats of violence or harm
- Serious harassment or bullying with intent to harm
- Genuine hate speech with malicious intent
- Self-harm encouragement or suicide promotion
- Doxxing threats with actual information
- Planning illegal activities

🟡 YELLOW (Suspicious/Concerning) - POTENTIAL RISKS:
- Scam attempts or phishing
- Financial fraud indicators
- Requests for sensitive personal information
- Spam or unsolicited commercial content
- Manipulative or coercive language
- Suspicious urgency tactics

🟢 GREEN (Safe) - ACCEPTABLE:
- Normal conversation between friends
- Playful banter or friendly teasing
- Dark humor without malicious intent
- Casual profanity in casual context
- Exaggerated expressions (e.g., "I'm dying" = laughing hard)
- Regular disagreements without threats

CRITICAL RULES:
1. Consider the RELATIONSHIP: Friends joking vs strangers threatening
2. Check for REPEATED patterns: One joke vs persistent harassment
3. Analyze TONE: Playful vs menacing
4. Context matters: "kill it" in gaming vs real life
5. When in doubt between RED and GREEN, choose YELLOW
6. Encrypted messages starting with "U2FsdGVk" should be judged by patterns

Respond with ONLY one word: RED, YELLOW, or GREEN."""

            # Create user prompt with context
            user_prompt = f"Classify this message: {text[:500]}"
            if context_str:
                user_prompt += context_str

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=10,
                temperature=0.1,
            )
            
            classification = response.choices[0].message.content.strip().upper()
            logger.info(f"GPT classification result: {classification} (with {len(context or [])} context messages)")
            
            if classification == "RED":
                return "red"
            elif classification == "YELLOW":
                return "yellow"
            else:
                return "green"
                
        except Exception as e:
            logger.error(f"OpenAI classification error: {str(e)}")
            # Fallback to keyword-based
            return self.classify_with_keywords(text)

    def classify_with_keywords(self, text):
        """Keyword-based classification (fallback)"""
        text_lower = text.lower() if text else ""
        
        red_keywords = [
            "kill", "murder", "attack", "bomb", "weapon", "hurt you", 
            "find you", "watch your back", "expose you", "doxx", 
            "suicide", "kill yourself", "kys", "die", "threat",
            "i will kill", "going to kill", "destroy you"
        ]
        
        yellow_keywords = [
            "prize", "winner", "congratulations you won", "claim reward",
            "verify account", "suspended", "urgent", "click here",
            "password expired", "security alert", "payment error",
            "free money", "investment opportunity"
        ]
        
        for keyword in red_keywords:
            if keyword in text_lower:
                return "red"
        
        for keyword in yellow_keywords:
            if keyword in text_lower:
                return "yellow"
        
        return "green"

@csrf_exempt
def test_classification(request):
    """Test endpoint - doesn't update Firestore"""
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text', '')
        
        # Test AI classification
        use_ai = os.environ.get('USE_AI_CLASSIFICATION', 'false').lower() == 'true'
        
        if use_ai:
            try:
                from openai import OpenAI
                api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_API_KEY')
                
                if not api_key:
                    return JsonResponse({"error": "No API key found"}, status=400)
                
                client = OpenAI(api_key=api_key)
                
                system_prompt = """Classify as RED (dangerous), YELLOW (suspicious), or GREEN (safe).
Respond with ONLY one word: RED, YELLOW, or GREEN."""
                
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
                
                return JsonResponse({
                    "text": text,
                    "classification": classification.lower(),
                    "method": "gpt-4o-mini"
                })
                
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
        else:
            return JsonResponse({"error": "AI not enabled"}, status=400)
    
    return JsonResponse({"message": "Send POST request with 'text' field"})