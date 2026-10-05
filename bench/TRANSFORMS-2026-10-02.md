# encoding-bench: whole-text transforms (2026-10-02)

Opt-in defender `supply+transforms` = bastionsupply's scan plus `decoded_views(text, transforms=True)` (gate `decode_transforms: true`, mesh `decode_transforms: true`).

```
encoding-bench (offline, deterministic): % flagged
  detection = malicious rows flagged (higher is better); FP = benign rows flagged (lower is better); +shadow = extra rows a shadow detector would block

  encoding           supply det       supply FP supply+transforms det supply+transforms FP
  plain                     88%              0%                   88%                   0%
  base64                    88%              0%                   88%                   0%
  base64url                 88%              0%                   88%                   0%
  base32                    88%              0%                   88%                   0%
  hex                       88%              0%                   88%                   0%
  binary                    88%              0%                   88%                   0%
  ascii85                   88%              0%                   88%                   0%
  base85                    88%              0%                   88%                   0%
  morse                     39%              0%                   39%                   0%
  percent                   88%              0%                   88%                   0%
  escape                    88%              0%                   88%                   0%
  tags                     100%            100%                  100%                 100%
  rot13                      1%              0%                   88%                   0%
  leet                       1%              0%                   76%                   0%
  reversed                   1%              0%                   88%                   0%
  spaced                     1%              0%                    8%                   0%
```

- rot13 1% -> 88%, leet 1% -> 76%, reversed 1% -> 88%, spaced 1% -> 8%; every other encoding unchanged; 0% benign FP on the corpus benign rows.
- Spaced letters stay low: the spaced view only joins 3+ single letters, and most signatures need the word gaps the encoder removes.
