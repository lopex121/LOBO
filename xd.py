# auth/utils.py
import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# correr una vez:
print(hash_password("Love200671$"))
