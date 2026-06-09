Yes — but from scratch, for client credentials, I strongly recommend App Roles, not delegated scopes.

Reason: Microsoft says .default is required for client credentials, and app-only tokens may be issued without roles unless the API enforces/uses app roles. Delegated scopes are mainly for user-delegated access.  ￼

Step-by-step Azure AD setup

1. Create protected API app

Go to:

Microsoft Entra admin center
→ App registrations
→ New registration

Create:

Name: kong-protected-api
Supported account types: Single tenant
Redirect URI: blank

Copy:

Application client ID
Directory tenant ID

2. Set Application ID URI

Open:

kong-protected-api
→ Expose an API
→ Set Application ID URI

Use:

api://<kong-protected-api-client-id>

Example:

api://11111111-2222-3333-4444-555555555555

3. Create app role

Open:

kong-protected-api
→ App roles
→ Create app role

Fill:

Display name: API.Access
Allowed member types: Applications
Value: API.Access
Description: Allows client app to call Kong-protected API
Enable: Yes

Save.

4. Create consumer1

Go to:

App registrations
→ New registration

Create:

Name: consumer1
Redirect URI: blank

Copy consumer1 client ID.

Then:

consumer1
→ Certificates & secrets
→ New client secret

Copy the secret value.

5. Grant API.Access to consumer1

Open:

consumer1
→ API permissions
→ Add a permission
→ My APIs
→ kong-protected-api
→ Application permissions
→ API.Access
→ Add permissions

At this point it will show:

Not granted for <tenant>

This is expected unless you have admin rights.

6. Ask admin to grant consent

Since your button is disabled, send this to your Azure admin:

Please grant admin consent for this Azure AD application permission:

Client app: consumer1
Protected API app: kong-protected-api
Permission: API.Access
Permission type: Application permission

Path:
App registrations → consumer1 → API permissions → Grant admin consent

7. Create consumer2

Create another app registration:

Name: consumer2
Redirect URI: blank

Create a client secret.

Do not add API.Access permission to consumer2.

8. Generate token for consumer1

After admin consent is granted:

curl -X POST \
"https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "client_id=<consumer1-client-id>" \
-d "client_secret=<consumer1-secret>" \
-d "scope=api://<kong-protected-api-client-id>/.default" \
-d "grant_type=client_credentials"

Decoded token should contain:

"aud": "api://<kong-protected-api-client-id>",
"roles": ["API.Access"]

9. Generate token for consumer2

Use consumer2 client ID and secret:

curl -X POST \
"https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "client_id=<consumer2-client-id>" \
-d "client_secret=<consumer2-secret>" \
-d "scope=api://<kong-protected-api-client-id>/.default" \
-d "grant_type=client_credentials"

Expected:

No roles claim