import ssl, socket, sys
host = 'runfit.wenhh.top'
ips = ['104.21.12.29', '172.67.131.234']
for ip in ips:
    for tlsver in [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.minimum_version = tlsver
            ctx.maximum_version = tlsver
        except Exception as e:
            print('setver err', e); continue
        try:
            with socket.create_connection((ip, 443), timeout=15) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    print(f'{ip} {tlsver.name}: OK cipher={ssock.cipher()[0]} cert_len={len(cert)}')
        except Exception as e:
            print(f'{ip} {tlsver.name}: FAIL {type(e).__name__}: {e}')