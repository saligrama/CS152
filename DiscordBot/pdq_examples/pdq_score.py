#!/usr/bin/env python
from typing import Optional
import cv2
import pdqhash
import numpy as np
import sys

PDQ_BLACKLIST = [
    "90457290b72f220c6ad248565b23bbdccc698356bb63c97952cab4d769a6f963", #img 1
    "ab1127cbf1a5329583cee5ca3cc44663b0f3a87903c095e33d8d9eae665e525a", #img 2
    "c32d343e4ed6705e2ecaec36db17724926566d8d9c1fe30d0f2e532191cb85d0"  #img 3
]
PDQ_HASH_LENGTH = 256

PDQ_BLACKLIST = [
    np.unpackbits(np.frombuffer(bytes.fromhex(s), dtype=np.uint8))
    for s in PDQ_BLACKLIST
]

def pdq_singlehash_min_dist(badList, hash) -> int:
    mindist = PDQ_HASH_LENGTH + 1
    for badhash in badList:
        # PDQ is hamming distance based
        mindist = min(mindist, (badhash != hash).sum())
    return mindist


def pdq_eval_max_similarity(badList, cv2image) -> Optional[float]:
    image = cv2.cvtColor(cv2image, cv2.COLOR_BGR2RGB)

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
    hash_vectors, _ = pdqhash.compute_dihedral(image)
    max_sim = max((
        (PDQ_HASH_LENGTH - pdq_singlehash_min_dist(badList, h)) / PDQ_HASH_LENGTH
        for h in hash_vectors
    ))
    # print(hash_vectors)
    # print(max_sim)
    # print(quality)
    return max_sim

image = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)

print(f"Just 1: {pdq_eval_max_similarity(PDQ_BLACKLIST[0:1], image)}")
print(f"Just 2: {pdq_eval_max_similarity(PDQ_BLACKLIST[1:2], image)}")
print(f"Just 3: {pdq_eval_max_similarity(PDQ_BLACKLIST[2:3], image)}")
print(f"1,2: {pdq_eval_max_similarity(PDQ_BLACKLIST[0:2], image)}")
print(f"2,3: {pdq_eval_max_similarity(PDQ_BLACKLIST[1:3], image)}")
print(f"1,3: {pdq_eval_max_similarity(PDQ_BLACKLIST[0:1] + PDQ_BLACKLIST[2:3], image)}")
print(f"ALL: {pdq_eval_max_similarity(PDQ_BLACKLIST, image)}")
