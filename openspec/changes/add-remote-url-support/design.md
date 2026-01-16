## Context

DuckDB has native support for reading files from HTTP/HTTPS URLs via its httpfs extension, which is enabled by default. This allows reading remote CSV files without manual download. The user wants to add this capability to csvnorm while keeping the implementation simple.

User preferences (from clarification):
- No authentication support (only public URLs)
- No caching mechanism
- Fixed timeout (30 seconds recommended)
- DuckDB should read URLs directly (not download-then-process)

## Goals / Non-Goals

**Goals:**
- Allow users to process remote CSV files without manual download
- Leverage DuckDB's built-in httpfs capability
- Maintain all existing validation/normalization features for remote files
- Minimal code changes - reuse existing pipeline where possible

**Non-Goals:**
- Authentication support (basic auth, bearer tokens, custom headers)
- Local caching of downloaded files
- Configurable timeout (use fixed 30s)
- Support for non-HTTP protocols (ftp, s3, etc.)
- Resume/retry logic for failed downloads

## Decisions

### Decision: Pass URLs directly to DuckDB

**Rationale:** DuckDB's `read_csv()` function accepts URLs directly and handles HTTP requests, encoding detection, and streaming. This is simpler than downloading files ourselves.

**Alternatives considered:**
- Download file to temp location first: More control but adds complexity, requires managing temp files, and loses DuckDB's streaming capability
- Use requests library: Redundant with DuckDB's httpfs, adds dependency

### Decision: Skip encoding detection for URLs

**Rationale:** DuckDB handles encoding internally for remote files. Running charset_normalizer on remote files would require downloading them first, defeating the purpose of direct URL support.

**Implementation:** Add `is_remote` flag to pipeline, skip steps 1-2 (encoding detection/conversion) when True.

### Decision: Derive filename from URL path

**Rationale:** Users expect output files named after the source. URL's last path segment provides a reasonable default.

**Implementation:** 
- Extract last segment from URL path (before query string)
- Apply existing `to_snake_case()` normalization
- Append `.csv` if no extension present
- Example: `https://data.gov/files/My_Data.csv?v=2` → `my_data.csv`

### Decision: Fixed 30-second timeout

**Rationale:** Balances waiting for slow connections vs failing fast. Standard HTTP timeout range is 15-60s; 30s is reasonable middle ground.

**Implementation:** Set DuckDB's `http_timeout` option to 30000ms before reading URLs.

### Decision: Minimal error handling for auth/404

**Rationale:** DuckDB will raise appropriate errors for HTTP failures (401, 403, 404, timeout). We add user-friendly error messages by catching DuckDB exceptions and checking error text.

**Implementation:** Wrap DuckDB calls in try/catch, inspect exception message for HTTP status codes, show appropriate panel with explanation.

## Risks / Trade-offs

### Risk: Large remote files may cause memory issues
**Mitigation:** DuckDB streams data, so memory usage should be similar to local files. Document that very large files (>1GB) may require more memory or may timeout.

### Risk: Network failures appear as cryptic DuckDB errors
**Mitigation:** Add error message detection and user-friendly explanations for common HTTP errors (401, 403, 404, timeout).

### Trade-off: No progress indicator for download
DuckDB handles the HTTP request internally, so we can't show download progress. The progress spinner will pause during download.
**Accepted:** This is acceptable for v1. Most CSV files are <100MB and download quickly.

### Trade-off: No authentication support
Users with private data sources must download manually first.
**Accepted:** Keeps implementation simple. Can add in future if needed.

## Migration Plan

No migration needed - this is a pure addition. Existing local file functionality is unchanged. Users can continue using file paths as before.

## Open Questions

None - all clarifications received from user.
