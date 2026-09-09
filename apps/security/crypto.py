"""Small cryptographic utilities for identifiers, checksums and safe audit payloads."""
import base64,hashlib,hmac,secrets

class Checksum:
    @staticmethod
    def sha256(value):
        if isinstance(value,str): value=value.encode();
        return hashlib.sha256(value).hexdigest()
    @staticmethod
    def sha512(value):
        if isinstance(value,str): value=value.encode()
        return hashlib.sha512(value).hexdigest()
    @staticmethod
    def verify(value,digest,algorithm="sha256"):
        actual=getattr(hashlib,algorithm)(value.encode() if isinstance(value,str) else value).hexdigest(); return hmac.compare_digest(actual,digest)

class TokenService:
    @staticmethod
    def opaque(length=32): return secrets.token_urlsafe(length)
    @staticmethod
    def short_code(length=8): return secrets.token_hex(max(1,length//2)).upper()[:length]
    @staticmethod
    def fingerprint(*parts): return Checksum.sha256("|".join(str(x) for x in parts))
    @staticmethod
    def signed_value(value,secret):
        raw=value.encode(); sig=hmac.new(secret.encode(),raw,hashlib.sha256).digest(); return base64.urlsafe_b64encode(raw+b"."+sig).decode()
    @staticmethod
    def verify_signed_value(token,secret):
        try:
            decoded=base64.urlsafe_b64decode(token.encode()); raw,sig=decoded.rsplit(b".",1); expected=hmac.new(secret.encode(),raw,hashlib.sha256).digest(); return raw.decode() if hmac.compare_digest(sig,expected) else None
        except (ValueError,TypeError,base64.binascii.Error): return None
