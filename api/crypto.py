from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import hashlib

def decrypt_message(encrypted_text, chat_id):
    """
    Decrypts a Base64 encoded AES message.
    The encryption key is derived from the chat_id to ensure it's always 32 bytes.
    """
    try:
        # Use SHA-256 to hash the chat_id into a secure, 32-byte key.
        # This ensures the key is always the correct length for AES-256.
        key = hashlib.sha256(chat_id.encode()).digest()
        
        # Decode the Base64 encoded message
        decoded_data = base64.b64decode(encrypted_text)
        
        # The first 16 bytes are the initialization vector (IV)
        iv = decoded_data[:16]
        # The rest of the data is the encrypted ciphertext
        encrypted_data = decoded_data[16:]
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Decrypt and unpad the data to get the original message
        decrypted_padded_data = cipher.decrypt(encrypted_data)
        decrypted_data = unpad(decrypted_padded_data, AES.block_size)
        
        return decrypted_data.decode('utf-8')

    except Exception as e:
        print(f"Decryption error: {e}")
        # If decryption fails, return a placeholder string
        return "[Decryption Failed]"
