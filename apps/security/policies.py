"""Reusable security decision helpers."""
from ipaddress import ip_address, ip_network
from .services import PolicyEngine

def normalize_ip(value):
    try: return str(ip_address(value))
    except ValueError: return ""

def ip_in_networks(value, networks):
    try: ip=ip_address(value)
    except ValueError: return False
    for network in networks or []:
        try:
            if ip in ip_network(network,strict=False): return True
        except ValueError: continue
    return False

def evaluate_ip_policy(organization,ip):
    normalized=normalize_ip(ip)
    if not normalized:return {"allowed":False,"reason":"invalid_ip"}
    policy=PolicyEngine.active_policy(organization)
    if not policy:return {"allowed":True,"reason":"no_policy"}
    if ip_in_networks(normalized,policy.ip_blocklist): return {"allowed":False,"reason":"blocklist"}
    if policy.ip_allowlist and not ip_in_networks(normalized,policy.ip_allowlist): return {"allowed":False,"reason":"not_allowlisted"}
    return {"allowed":True,"reason":"policy_pass"}

def permission_matrix(user,resource_codes):
    return {code:user.has_enterprise_perm(code) for code in resource_codes}

def security_headers():
    return {"X-Content-Type-Options":"nosniff","Referrer-Policy":"strict-origin-when-cross-origin","Permissions-Policy":"geolocation=(), microphone=(), camera=()","Cache-Control":"no-store"}
