# Authentication & Session Security Architecture

## Authentication Pipeline
1. **User Identifier**: Case-insensitive email is required for user lookup via `EmailAuthBackend`.
2. **Brute-Force Guard**:
   - `AUTH_MAX_LOGIN_ATTEMPTS` defaults to 5.
   - Upon exceeding threshold, `locked_until` is set to `now + AUTH_LOCKOUT_DURATION_MINUTES` (default 15 mins).
   - An `AccountLockoutAudit` record is created.
   - Subsequent login attempts with either correct or incorrect passwords are automatically rejected with remaining lockout duration.
3. **Session Integrity**:
   - `SessionSecurityMiddleware` verifies `user.is_active` and `user.is_locked` on every incoming request.
   - If an active user's status is toggled or locked in the database, their session is immediately revoked and redirected to the login view with an informative notification.
4. **Token Life Cycle**:
   - Account Activation: Timestamp-signed HMAC token valid for 48 hours.
   - Password Reset: Timestamp-signed HMAC token cryptographically bound to a SHA256 digest of the user's password hash, valid for 24 hours. If the user changes their password, any existing token is immediately invalidated.
