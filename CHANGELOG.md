# Changelog

## 0.19.0 (unreleased)

- **`encoding-bench`**: offline (no model, no API key), deterministic. For each encoding,
  the share of corpus attacks (and of benign rows) that agentbastion and bastionsupply flag.
  The baseline in `bench/BASELINE-2026-10-01.md` was taken before any decode-and-rescan
  detector existed:
  - unencoded attacks: 74% caught by agentbastion, 88% by bastionsupply;
  - encoded attacks: 0 to 3%, whatever the encoding.
- **`run --encode NAMES|all`**: fires every payload again in each encoding (base64,
  base64url, base32, hex, binary, ascii85, base85, morse, percent, escape, tags, rot13, leet,
  reversed, spaced), plus bastioncorpus's own `enc-*` rows. The canary is filled in before
  encoding, and results are tagged `<tactic>+enc-<name>`.
- Encoded corpus rows (`enc-*`, bastioncorpus 0.5.0) are opt-in: a default `run`, `matrix`
  or `coevolve` does not fire them, so existing runs keep the same payload set.
- Requires bastioncorpus >= 0.5.0.
