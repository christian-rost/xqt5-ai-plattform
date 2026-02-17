# Schritt 2 Test: Sofortige Session-Invalidierung

## Ziel
Pruefen, dass bestehende Access- und Refresh-Tokens nach Deaktivierung sofort ungueltig sind.

## Voraussetzung
Die Migration `supabase/migrations/20260217_phase_d_token_version_revocation.sql` ist ausgefuehrt.

## Testablauf
1. Als `normal_user` einloggen, `ACCESS_OLD` und `REFRESH_OLD` speichern.
2. Mit `ACCESS_OLD` `GET /api/auth/me` aufrufen.
   - Erwartung: HTTP 200.
3. Als Admin den User deaktivieren:
   - `PATCH /api/admin/users/{normal_user_id}` mit `{"is_active": false}`.
   - Erwartung: HTTP 200.
4. Direkt danach erneut `GET /api/auth/me` mit `ACCESS_OLD`.
   - Erwartung: HTTP 401 (`Token has been revoked` oder inaktiv).
5. `POST /api/auth/refresh` mit `REFRESH_OLD`.
   - Erwartung: HTTP 401.

## Beispiel-cURL
```bash
curl -i "$API_BASE/api/auth/me" \
  -H "Authorization: Bearer $ACCESS_OLD"

curl -i "$API_BASE/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH_OLD\"}"
```
