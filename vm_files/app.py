# Sample application
import os, hashlib

f = 'file_100MB.bin'
if not os.path.exists(f): open(f, 'wb').write(os.urandom(100*1024*1024))
print(hashlib.sha256(open(f, 'rb').read()).hexdigest())
