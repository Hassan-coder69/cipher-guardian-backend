# api/crypto.py
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64

# This must be the same key used in your React app's encryption function
# For now, it's hardcoded. Later, you'll manage this securely.
SECRET_KEY = b'your-shared-secret-key-must-be-16-24-or-32-bytes' 

def decrypt_message(encrypted_text, key_salt):
    try:
        # We're using a placeholder secret key for now. 
        # A more secure implementation would derive the key from the key_salt (chat_id).
        key = SECRET_KEY 
        
        # Decode from Base64
        decoded_data = base64.b64decode(encrypted_text)
        
        # The IV is the first 16 bytes of the decoded data
        iv = decoded_data[:16]
        # The actual encrypted text is the rest
        encrypted_data = decoded_data[16:]
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Decrypt and unpad the data
        decrypted_padded_data = cipher.decrypt(encrypted_data)
        decrypted_data = unpad(decrypted_padded_data, AES.block_size)
        
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        # Return a placeholder or the original text if decryption fails
        return "[Decryption Failed]"