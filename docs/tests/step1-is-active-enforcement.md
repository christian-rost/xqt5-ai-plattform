# Schritt 1 Test: `is_active` Enforcement

## Ziel
Pruefen, dass inaktive Benutzer keine API-Aufrufe und kein Token-Refresh mehr ausfuehren koennen.

## Vorbereitung
1. Backend lokal starten.
2. Zwei Accounts vorhanden:
   - `admin_user` (is_admin=true)
   - `normal_user` (is_admin=false)

## Testablauf
1. Als `normal_user` einloggen und Access-/Refresh-Token speichern.
2. Mit dem Access-Token `GET /api/auth/me` aufrufen.
   - Erwartung: HTTP 200.
3. Als `admin_user` einloggen und `normal_user` deaktivieren:
   - `PATCH /api/admin/users/{normal_user_id}` mit Body `{"is_active": false}`.
   - Erwartung: HTTP 200.
4. Erneut `GET /api/auth/me` mit dem alten Access-Token von `normal_user` aufrufen.
   - Erwartung: HTTP 401.
5. `POST /api/auth/refresh` mit dem alten Refresh-Token von `normal_user` aufrufen.
   - Erwartung: HTTP 401.

## Beispiel-cURL (Schritt 4/5)
```bash
curl -i "$API_BASE/api/auth/me" \
  -H "Authorization: Bearer $NORMAL_ACCESS_TOKEN"

curl -i "$API_BASE/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$NORMAL_REFRESH_TOKEN\"}"
```
