#!/usr/bin/env python
import pdqhash
import sys
import numpy as np
import cv2

image = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Get all the rotations and flips in one pass.
# hash_vectors is a list of vectors in the following order
# - Original
# - Rotated 90 degrees
# - Rotated 180 degrees
# - Rotated 270 degrees
# - Flipped vertically
# - Flipped horizontally
# - Rotated 90 degrees and flipped vertically
# - Rotated 90 degrees and flipped horizontally
hash_vectors, quality = pdqhash.compute_dihedral(image)
print(f'Quality: {quality}')
for hash in hash_vectors:
    hash = np.packbits(hash)
    print(hash.tobytes().hex())
    # To unpack:
    #np.unpackbits(np.frombuffer(bytes.fromhex(hash.tobytes().hex()), dtype=np.uint8))