"""
EnterpriseOne System Constants.
Defines system-wide enums, codes, and operational thresholds.
"""

# Platform Metadata
PLATFORM_NAME = "EnterpriseOne"
PLATFORM_VERSION = "1.0.0"
PLATFORM_TAGLINE = "Next-Generation Modular Enterprise Management"

# Account Status
class AccountStatus:
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"

    CHOICES = [
        (PENDING_VERIFICATION, "Pending Verification"),
        (ACTIVE, "Active"),
        (LOCKED, "Locked"),
        (SUSPENDED, "Suspended"),
        (DEACTIVATED, "Deactivated"),
    ]

# Login Result / History Status
class LoginStatus:
    SUCCESS = "SUCCESS"
    FAILED_INVALID_CREDENTIALS = "FAILED_INVALID_CREDENTIALS"
    FAILED_ACCOUNT_LOCKED = "FAILED_ACCOUNT_LOCKED"
    FAILED_ACCOUNT_INACTIVE = "FAILED_ACCOUNT_INACTIVE"
    FAILED_PASSWORD_EXPIRED = "FAILED_PASSWORD_EXPIRED"
    LOGOUT = "LOGOUT"

    CHOICES = [
        (SUCCESS, "Successful Login"),
        (FAILED_INVALID_CREDENTIALS, "Invalid Credentials"),
        (FAILED_ACCOUNT_LOCKED, "Account Locked"),
        (FAILED_ACCOUNT_INACTIVE, "Account Inactive"),
        (FAILED_PASSWORD_EXPIRED, "Password Expired"),
        (LOGOUT, "Logout"),
    ]

# Audit Action Types
class AuditAction:
    USER_REGISTER = "USER_REGISTER"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_LOCKOUT = "USER_LOCKOUT"
    USER_PASSWORD_CHANGE = "USER_PASSWORD_CHANGE"
    USER_PASSWORD_RESET_REQUEST = "USER_PASSWORD_RESET_REQUEST"
    USER_PASSWORD_RESET_COMPLETE = "USER_PASSWORD_RESET_COMPLETE"
    ROLE_ASSIGNED = "ROLE_ASSIGNED"
    ROLE_REVOKED = "ROLE_REVOKED"
    PROFILE_UPDATED = "PROFILE_UPDATED"

# Theme Preferences
class ThemePreference:
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    CHOICES = [
        (LIGHT, "Light"),
        (DARK, "Dark"),
        (SYSTEM, "System Default"),
    ]
