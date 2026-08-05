import bcrypt
salt = bcrypt.gensalt(12)
hash = bcrypt.hashpw(b"password", salt)
print(hash.decode())
