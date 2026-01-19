import os
import sys
import requests
import socket
import qrcode
import subprocess
import signal

# 存储所有子进程
child_processes = []

# 信号处理函数，用于处理Ctrl+C

def signal_handler(sig, frame):
    print("\n正在关闭所有子进程...")
    # 终止所有子进程
    for process in child_processes:
        try:
            process.terminate()
            process.wait(timeout=5)  # 等待进程终止，最多5秒
        except subprocess.TimeoutExpired:
            # 如果进程在5秒内没有终止，强制杀死
            process.kill()
    print("所有子进程已关闭，程序退出。")
    sys.exit(0)

# 注册信号处理函数
signal.signal(signal.SIGINT, signal_handler)

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

# 生成终端二维码
def generate_cli_qrcode(data):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr.print_ascii()
    except UnicodeEncodeError:
        # 如果遇到编码错误，跳过QR码生成，只打印URL
        print("无法生成终端二维码，HTTPS访问地址：", data)

if __name__ == '__main__':
    # 配置参数
    CURRENT_VERSION = "0.0.2"
    GITHUB_REPO = "ChaserSu/DBInputNote"  # GitHub 用户名/仓库名
    port = 5001
    
    print("正在启动DBInputNote...")
    
    # 每次启动都生成新证书，防止IP内网变动
    from generate_cert import generate_self_signed_cert
    generate_self_signed_cert()
    
    # 获取本地IP和访问URL
    local_ip = get_local_ip()
    https_url = f"https://{local_ip}:{port}"
    
    # 生成并输出终端二维码（使用HTTPS）
    generate_cli_qrcode(https_url)
    
    # 检查更新
    print("正在检查更新...")
    try:
        # 调用 GitHub API 获取最新发布版本
        response = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            timeout=3,
            headers={"User-Agent": "DBInputNote-Client"}
        )
        if response.status_code == 200:
            latest_data = response.json()
            latest_version = latest_data.get("tag_name", "").lstrip('v')  # 去除版本号前缀的 'v'
            
            # 版本号对比（简单数字对比，适用于 x.y.z 格式）
            def version_to_tuple(version_str):
                return tuple(map(int, version_str.split('.')))
            
            current_tuple = version_to_tuple(CURRENT_VERSION)
            latest_tuple = version_to_tuple(latest_version)
            
            if latest_tuple > current_tuple:
                print(f"发现新版本！当前版本 v{CURRENT_VERSION} → 最新版本 v{latest_version}")
                print(f"下载地址：{latest_data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases')}")
                print(f"更新日志：{latest_data.get('body', '请前往 GitHub 查看详细更新日志')[:200]}...\n")
            else:
                print("当前已是最新版本！\n")
        else:
            print("更新检查失败：无法获取最新版本信息\n")
    except requests.exceptions.RequestException as e:
        # 网络错误/超时，不影响主程序
        print(f"更新检查失败：{str(e)}（忽略，继续运行）\n")
    
    # 输出启动信息
    print(f"服务器已启动！")
    print(f"HTTPS访问地址：{https_url}")
    print(f"注意，跨设备访问需在同一局域网下")
    print(f"当前版本 v{CURRENT_VERSION}，项目地址：https://github.com/{GITHUB_REPO}")
    print(f"首次访问HTTPS会提示证书不安全，点击'高级'->'继续访问'即可")
    
    # 使用新生成的证书文件
    cert_file = 'localhost.crt'
    key_file = 'localhost.key'
    
    # 直接使用新生成的证书，无需检查存在性，因为我们已经生成了
    print(f"使用新生成的证书文件：{cert_file} 和 {key_file}")
    
    # 启动CW/start_server.exe子进程
    try:
        cw_server_path = os.path.join('CW', 'start_server.exe')
        print(f"正在启动CW服务器：{cw_server_path}")
        cw_process = subprocess.Popen(
            [cw_server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        child_processes.append(cw_process)
        print("CW服务器已启动")
    except Exception as e:
        print(f"启动CW服务器失败：{str(e)}")
    
    try:
        # 直接导入app.py中的Flask应用
        import app
        
        # 设置app的配置
        app.app.config['SSL_CERT'] = cert_file
        app.app.config['SSL_KEY'] = key_file
        
        print(f"正在启动HTTPS服务器...")
        
        # 直接运行Flask应用，使用HTTPS
        try:
            import ssl
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_file, key_file)
            print(f"\napp.py HTTPS运行模式")
            print(f"HTTPS访问地址：https://0.0.0.0:{port}")
            print(f"使用证书：{cert_file} 和 {key_file}")
            app.app.run(debug=False, host='0.0.0.0', port=port, ssl_context=ssl_context)
        except Exception as e:
            print(f"HTTPS启动失败：{str(e)}")
            print("正在尝试回退到HTTP模式...")
            # 回退到HTTP模式
            print(f"HTTP访问地址：http://0.0.0.0:{port}")
            app.app.run(debug=False, host='0.0.0.0', port=port)
        
    except Exception as e:
        print(f"启动应用失败：{str(e)}")
        print("程序启动失败，即将退出...")
        sys.exit(1)
