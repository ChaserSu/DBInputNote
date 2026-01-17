import subprocess
import sys

# 使用pyinstaller的完整路径
pyinstaller_path = r"C:\Users\ME_Sever\AppData\Roaming\Python\Python313\Scripts\pyinstaller.exe"

# 使用subprocess运行pyinstaller命令（单文件模式）
cmd = [
    pyinstaller_path,
    '-F',  # 单文件模式
    'main.py',
    '--name', 'DBInputNote',
    '--add-data', 'templates;templates',
    '--add-data', 'update.py;.',
    '--add-data', 'requirements.txt;.'
]

print(f"正在执行打包命令：{' '.join(cmd)}")
subprocess.run(cmd, check=True)
print("\n✅ 打包完成！")