import ssl
import os
import datetime
import socket
import ipaddress

# 获取本地IP地址
def get_local_ip():
    try:
        # 创建一个UDP套接字，不实际连接任何服务器
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个公共DNS服务器，这样操作系统会自动选择一个合适的网卡
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        # 如果获取失败，返回127.0.0.1
        return '127.0.0.1'

# 生成自签名证书
def generate_self_signed_cert():
    cert_file = 'localhost.crt'
    key_file = 'localhost.key'
    
    print("正在生成自签名证书...")
    
    # 获取当前的内网IP地址
    local_ip = get_local_ip()
    
    # 使用ssl模块生成自签名证书
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    # 生成私钥
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # 生成证书请求
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Guangdong"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Shenzhen"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DBInputNote"),
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
    ])
    
    # 创建Subject Alternative Names，包含localhost和当前内网IP
    san_entries = [
        x509.DNSName("localhost"),
        x509.DNSName("127.0.0.1"),
        x509.IPAddress(ipaddress.IPv4Address(local_ip))
    ]
    
    # 生成证书
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.UTC)
    ).not_valid_after(
        # 证书有效期为1天，每次启动都生成新证书
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
    ).add_extension(
        x509.SubjectAlternativeName(san_entries),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # 保存证书和私钥
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    
    print(f"自签名证书已生成：{cert_file} 和 {key_file}")
    print(f"证书包含地址：localhost, 127.0.0.1, {local_ip}")
    return cert_file, key_file

if __name__ == '__main__':
    generate_self_signed_cert()