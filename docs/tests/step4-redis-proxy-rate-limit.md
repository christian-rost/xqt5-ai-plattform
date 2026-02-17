# Schritt 4 Test: Redis-Storage + Proxy-Header

## Ziel
Pruefen, dass Rate-Limits ueber Prozess-Restarts hinweg bestehen bleiben (Redis) und Client-IP ueber Proxy-Header korrekt ausgewertet wird.

## Vorbereitung
1. `RATE_LIMIT_STORAGE_URL` auf Redis setzen, z. B.:
   - `redis://:<password>@<host>:6379/0`
2. Backend neu deployen/starten.

## Test A: Limit bleibt nach Neustart aktiv
1. Fuehre den Login-Rate-Test aus `docs/tests/step3-rate-limits.md` aus, bis `429` kommt.
2. Starte nur den Backend-Service neu.
3. Direkt erneut einen Login-Request senden.
   - Erwartung: Weiterhin `429`, solange das Zeitfenster noch nicht abgelaufen ist.

## Test B: Proxy-Header
1. Request ueber den produktiven Proxy senden.
2. Mehrfach dieselbe Route aufrufen (z. B. Login).
   - Erwartung: Das Limit zaehlt konsistent pro Client (nicht global fuer alle).
