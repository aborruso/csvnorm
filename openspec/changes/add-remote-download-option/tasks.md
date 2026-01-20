## 1. Implementation
- [x] 1.1 Add CLI flag for remote download fallback
- [x] 1.2 Implement fallback download path when remote range unsupported
- [x] 1.3 Ensure temp file cleanup for downloaded remote
- [x] 1.4 Add tests for range-unsupported URL with/without flag
- [x] 1.5 Update LOG.md entry
- [x] 1.6 Add SSL/TLS handshake fallback for `--download-remote`
- [x] 1.7 Add tests covering handshake failure fallback

## 2. Validation
- [x] 2.1 Run pytest
- [x] 2.2 Run targeted smoke test for remote URL fallback (if feasible)
