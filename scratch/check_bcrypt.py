import bcrypt
hash = b'$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'
print("Matches?", bcrypt.checkpw(b'password', hash))
