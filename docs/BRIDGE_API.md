# Bridge API

Base: `http://127.0.0.1:8765` (loopback only). JSON bodies.
Protected routes require `Authorization: Bearer <token>`.

| Method | Path | Auth | Body | Response |
|---|---|---|---|---|
| GET | `/api/health` | no | — | status/version/uptime |
| POST | `/api/pair` | no | `{code, client}` | `{token, expires_in, scopes}` |
| GET | `/api/session` | yes | — | session metadata |
| POST | `/api/session/revoke` | yes | — | `{revoked:true}` |
| GET | `/api/hardware` | yes | — | profile + decision + probes |
| GET | `/api/models` | yes | — | catalog + installed |
| POST | `/api/models/{id}/accept` | yes | `{accepted_by}` | `{accepted:id}` |
| GET | `/api/engine/status` | yes | — | loaded/sessions/errors |
| POST | `/api/source` | yes | `{image, name}` | `{name, thumbnail, sources}` |
| GET | `/api/sources` | yes | — | `{sources:[{name,thumbnail,primary}]}` |
| POST | `/api/map` | yes | `{track_id, source_name}` | mapping echo |
| POST | `/api/frame` | yes | `{image, swap, strength}` | `{image, metrics, faces, error}` |
| GET | `/api/diagnostics` | yes | — | sessions/models/errors |

`image` is base64 without the data-URL prefix (prefix is tolerated). Maximum
decoded size is 12 MB. Frames are returned as base64 JPEG (quality 90).

## Pairing

1. Desktop displays a 6-digit code (valid 180s, one use).
2. Web posts it to `/api/pair`.
3. Token is kept in `sessionStorage`; every call sends it as Bearer.
4. Six failed attempts per minute per IP → HTTP 429.
5. Unknown `Origin` → HTTP 403 before any handler.

## Example

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8765/api/pair \
  -H 'Content-Type: application/json' \
  -d '{"code":"123456","client":"cli"}' | jq -r .token)

curl -s http://127.0.0.1:8765/api/engine/status \
  -H "Authorization: Bearer $TOKEN" | jq .
```
