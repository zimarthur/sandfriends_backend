from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad, unpad
import base64

# AES encryption function
def encrypt_aes(data, password):
    salt = get_random_bytes(16)
    kdf = PBKDF2(password, salt, dkLen=32, count=1000000)  # Derive a 256-bit key
    key = kdf[:32]  # 32 bytes key for AES-256

    cipher = AES.new(key, AES.MODE_CBC)
    cipher_text = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))

    # Combine salt, cipher IV, and cipher text for storage or transmission
    encrypted_data = base64.b64encode(salt + cipher.iv + cipher_text).decode('utf-8')
    return encrypted_data

# AES decryption function
def decrypt_aes(encrypted_data, password):
    encrypted_data = base64.b64decode(encrypted_data)
    salt = encrypted_data[:16]
    iv = encrypted_data[16:32]
    cipher_text = encrypted_data[32:]

    kdf = PBKDF2(password, salt, dkLen=32, count=1000000)
    key = kdf[:32]

    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    decrypted_data = unpad(cipher.decrypt(cipher_text), AES.block_size)
    return decrypted_data.decode('utf-8')

# # Example usage
# if __name__ == "__main__":
#     password = "YourSecretPassword"
#     data_to_encrypt = input("O que vai ser criptografado:")

#     encrypted_data = encrypt_aes(data_to_encrypt, password)
#     print(f"Encrypted: {encrypted_data}")

#     decrypted_data = decrypt_aes(encrypted_data, password)
#     print(f"Decrypted: {decrypted_data}")
