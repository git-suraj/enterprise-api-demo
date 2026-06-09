# Keycloak Manual Setup

This is the manual setup for the `Identity: Keycloak Authorization` scene.

## Target behavior

- `consumer-1` gets a client-credentials token that includes the `api-access` role
- `consumer-2` gets a client-credentials token without that role
- Kong validates the bearer token with the `openid-connect` plugin
- Kong authorizes access based on the role claim

## Runtime

The local demo uses Keycloak on `http://localhost:8081`.

Admin login:

- username: `admin`
- password: `admin`

## 1. Create the realm

1. Open `http://localhost:8081`
2. Log in to the admin console
3. Create a new realm named `kong-demo`

## 2. Create the realm role

1. Open the `kong-demo` realm
2. Go to `Realm roles`
3. Create a role named `api-access`

## 3. Create the protected API client

1. Go to `Clients`
2. Create a client:
   - Client ID: `protected-api`
   - Client type / protocol: `OpenID Connect`
3. Set:
   - `Client authentication`: `On`
   - `Authorization`: `Off`
   - `Standard flow`: `Off`
   - `Direct access grants`: `Off`
   - `Service accounts roles`: `Off`
4. Save

This client exists to model the protected API in the demo. Kong still fronts the actual local API.

## 4. Create consumer-1

1. Create a client:
   - Client ID: `consumer-1`
2. Set:
   - `Client authentication`: `On`
   - `Standard flow`: `Off`
   - `Direct access grants`: `Off`
   - `Service accounts roles`: `On`
3. Save
4. Go to `Credentials`
5. Set or copy the client secret
   - expected demo secret: `consumer-1-secret`

## 5. Create consumer-2

1. Create a client:
   - Client ID: `consumer-2`
2. Set:
   - `Client authentication`: `On`
   - `Standard flow`: `Off`
   - `Direct access grants`: `Off`
   - `Service accounts roles`: `On`
3. Save
4. Go to `Credentials`
5. Set or copy the client secret
   - expected demo secret: `consumer-2-secret`

## 6. Assign roles

### consumer-1

1. Open `Clients -> consumer-1`
2. Open `Service account roles`
3. Assign the realm role `api-access`

### consumer-2

Do not assign `api-access` to `consumer-2`.

## 7. Generate tokens manually

### consumer-1

```bash
curl -X POST \
  "http://localhost:8081/realms/kong-demo/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=consumer-1" \
  -d "client_secret=consumer-1-secret" \
  -d "grant_type=client_credentials"
```

### consumer-2

```bash
curl -X POST \
  "http://localhost:8081/realms/kong-demo/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=consumer-2" \
  -d "client_secret=consumer-2-secret" \
  -d "grant_type=client_credentials"
```

## 8. What to verify in the token

Decode the JWT and confirm:

- `iss` points to the `kong-demo` realm
- `azp` or client identity matches `consumer-1` or `consumer-2`
- `realm_access.roles` contains `api-access` for `consumer-1`
- `realm_access.roles` does not contain `api-access` for `consumer-2`

## 9. Kong plugin expectations

For this demo, Kong should be configured to:

- validate bearer tokens against the Keycloak issuer
- use the `openid-connect` plugin
- authorize on the `realm_access.roles` claim
- require the `api-access` role for the protected route

## 10. Demo result

- `consumer-1` token -> request should succeed through Kong
- `consumer-2` token -> request should be denied by Kong
