# Sample application
import os, hashlib

f = '/mnt/encrypted_data/file_100MB.bin'
if not os.path.exists(f):
    print("There isn't a file in the encrypted volume yet")
    open(f, 'wb').write(os.urandom(100*1024*1024))

print("Hash of file in encrypted container:",
      hashlib.sha256(open(f, 'rb').read()).hexdigest())
