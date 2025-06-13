import os
import ssl

def create_ssl_context():
    """Create enhanced SSL context for secure connections"""
    # Try to get cert paths from config if available
    try:
        from config import get_config
        config_class = get_config()
        cert_paths = config_class.get_cert_paths()
        cert_path = cert_paths['cert_path']
        key_path = cert_paths['key_path']
    except (ImportError, AttributeError):
        # Fallback to environment variables
        cert_path = os.getenv('CERT_PATH', './certs/entity/entity.crt')
        key_path = os.getenv('KEY_PATH', './certs/entity/entity.key')

    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Private key file not found: {key_path}")

    # Create SSL context with maximum security
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)

    # Enhanced security settings
    context.set_ciphers(
        'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS:!3DES:!RC4'
    )

    # Use only TLS 1.2 and 1.3
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    # Security options
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    context.options |= ssl.OP_SINGLE_DH_USE
    context.options |= ssl.OP_SINGLE_ECDH_USE
    context.options |= ssl.OP_NO_COMPRESSION

    # Set ECDH curve
    context.set_ecdh_curve('prime256v1')

    return context