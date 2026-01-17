import requests
import socket
import qrcode
import sys
import os

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
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii()

if __name__ == '__main__':
    # 配置参数
    CURRENT_VERSION = "0.0.1"
    GITHUB_REPO = "ChaserSu/DBInputNote"  # GitHub 用户名/仓库名
    port = 5001
    
    # 获取本地IP和访问URL
    local_ip = get_local_ip()
    access_url = f"http://{local_ip}:{port}"
    
    # 生成并输出终端二维码
    generate_cli_qrcode(access_url)
    
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
                print(f"\n🎉 发现新版本！当前版本 v{CURRENT_VERSION} → 最新版本 v{latest_version}")
                print(f"📥 下载地址：{latest_data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases')}")
                print(f"📝 更新日志：{latest_data.get('body', '请前往 GitHub 查看详细更新日志')[:200]}...\n")
            else:
                print("✅ 当前已是最新版本！\n")
        else:
            print("⚠️  更新检查失败：无法获取最新版本信息\n")
    except requests.exceptions.RequestException as e:
        # 网络错误/超时，不影响主程序
        print(f"⚠️  更新检查失败：{str(e)}（忽略，继续运行）\n")
    
    # 输出启动信息
    print(f"\n服务器已启动！")
    print(f"访问地址（或扫描上面的二维码）：{access_url}")
    print(f"注意，跨设备访问需在同一局域网下")
    print(f"当前版本 v{CURRENT_VERSION}，项目地址：https://github.com/{GITHUB_REPO}")
