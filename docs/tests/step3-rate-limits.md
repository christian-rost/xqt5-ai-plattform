# Schritt 3 Test: Rate-Limits

## Ziel
Pruefen, dass kritische Endpunkte nach Erreichen des Limits `429 Too Many Requests` liefern.

## Beispiel 1: Login-Limit (`10/minute`)
```bash
for i in $(seq 1 12); do
  echo "Request $i"
  curl -s -o /tmp/login_$i.json -w "%{http_code}\n" \
    -X POST "$API_BASE/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"wrong-user","password":"wrong-pass"}'
done
```

Erwartung: Nach mehreren Requests kommt mindestens einmal HTTP `429`.

## Beispiel 2: Message-Limit (`60/minute`)
```bash
for i in $(seq 1 65); do
  curl -s -o /tmp/msg_$i.json -w "%{http_code}\n" \
    -X POST "$API_BASE/api/conversations/$CONVERSATION_ID/message" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"content":"rate test","stream":false}'
done
```

Erwartung: Nach Erreichen des Limits antwortet der Endpoint mit HTTP `429`.
