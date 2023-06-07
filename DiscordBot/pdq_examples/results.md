## PDQ Evaluation

We evaluate PDQ against light-adversarial editing of a few simulated NCII images.
Qualitatively, PDQ performs excellently against uploads of identical images, even after conversions and compressions (e.g. by the Discord media proxy).

## Image 1

| Image        | Similarity 1 | Similarity 2 | Similarity 3 |
| ------------ | ------------ | ------------ | ------------ |
| ColorPerturb | 0.953125     | 0.53125      | 0.515625     |
| CropAndBorder| 0.546875     | 0.5703125    | 0.5703125    |
| Rotate       | 0.55446875   | 0.5625       | 0.5234375    |
| Shifted      | 0.578125     | 0.53125      | 0.59375      |

## Image 2
| Image        | Similarity 1 | Similarity 2 | Similarity 3 |
| ------------ | ------------ | ------------ | ------------ |
| ColorPerturb | 0.5390625    | 0.96875      | 0.515625     |
| CropAndBorder| 0.5546875    | 0.5625       | 0.546875     |
| Rotate       | 0.5703125    | 0.703125     | 0.50         |
| Shifted      | 0.546875     | 0.6484375    | 0.5625       |

## Image 3
| Image        | Similarity 1 | Similarity 2 | Similarity 3 |
| ------------ | ------------ | ------------ | ------------ |
| ColorPerturb | 0.515625     | 0.53125      | 0.9765625    |
| CropAndBorder| 0.546875     | 0.539062     | 0.5390625    |
| Rotate       | 0.546875     | 0.546875     | 0.5703125    |
| Shifted      | 0.53125      | 0.5625       | 0.7578125    |

## Conclusion

The TMK+PDQF paper points out that "[s]yntactic hashers [like PDQ] excel in finding media which are shared with minimum adversariality – image quality is reduced, JPEG is converted to PNG, etc. They are unsuitable for detecting intentional attack/obfuscation, including deeper crops. Detection of more adversarial image transformations lies within the domain of semantic/machine-learning
methods."

This is reflected in our observations: adversarial edits, including crops, do not match well. Furthermore, NCII is a difficult domain to apply generic classification or recognition algorithms because a qualitatively identical image with only a different subject and recipient could be bad in one case and okay in another.

Syntactic hashing is still important to include in an abuse detection setting: known near-verbatim images, such as those collected in the StopNCII database, can be detected and preemptively stopped with high confidence, and accounts which trigger such detections even once can be flagged for further investigation.