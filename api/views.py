from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import firestore
from .classifier import classify_text
from .crypto import decrypt_message

def health_check(request):
    """A simple view that returns a 200 OK status for Render's health check."""
    return JsonResponse({"status": "healthy", "message": "Cipher Guardian API is running."})

class ClassifyMessageView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        chat_id = data.get('chatId')
        message_id = data.get('messageId')
        encrypted_text = data.get('encryptedText')

        if not all([chat_id, message_id, encrypted_text]):
            return Response({"error": "Missing required data"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decrypted_text = decrypt_message(encrypted_text, chat_id)
            flag = classify_text(decrypted_text)
            
            print(f"Processing message {message_id}. Decrypted: '{decrypted_text}', Flagged as: {flag}")

            db = firestore.client()
            message_ref = db.collection('chats').document(chat_id).collection('messages').document(message_id)
            message_ref.update({'flag': flag})
            
            return Response({"status": "success", "flag": flag}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"An error occurred: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
