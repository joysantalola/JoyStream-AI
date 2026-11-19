# Input format

CSV: one row per stream. JSON: an array of objects, or an object with a `streams` array.

Required: `date` (ISO YYYY-MM-DD), `game`, `duration_hours`, `avg_viewers`, `peak_viewers`. Optional: `followers_gained`, `title`.

Numeric fields must be nonnegative. Dates must be valid. Each row represents a stream; avg_viewers is a per-stream average, not a unique viewer count. Data must be provided by the user with permission to analyze. Avoid including personal identifiers or tokens.
