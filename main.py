from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import sys
import uuid
import datetime
import requests
import socket
import qrcode

app = Flask(__name__)

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

# 获取应用根目录
if getattr(sys, 'frozen', False):
    # exe 打包运行模式
    app.root_path = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 源码运行模式
    app.root_path = os.path.dirname(os.path.abspath(__file__))

# 设置BOOKS_FOLDER为绝对路径
app.config['BOOKS_FOLDER'] = os.path.join(app.root_path, 'books')

# 确保必要的目录存在
os.makedirs(app.config['BOOKS_FOLDER'], exist_ok=True)

# 全局变量
current_book = None
current_chapter = None

class Chapter:
    def __init__(self, chapter_id, title, book_id):
        self.id = chapter_id
        self.title = title
        self.book_id = book_id
        self.paragraphs = []
        self.chapter_dir = os.path.join(app.config['BOOKS_FOLDER'], book_id, 'chapters', chapter_id)
        self.audio_dir = os.path.join(self.chapter_dir, 'audio')
        
        # 创建章节目录
        os.makedirs(self.chapter_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # 确保有一个结尾段落块
        self.ensure_end_paragraph()
    
    def ensure_end_paragraph(self):
        # 收集所有非结尾段落块，排除任何标记为end_paragraph的段落
        regular_paragraphs = []
        for p in self.paragraphs:
            # 只保留非结尾段落块
            if not p.get('is_end_paragraph') and p['id'] != 'end_paragraph':
                regular_paragraphs.append(p)
        
        # 创建一个全新的结尾段落块
        end_paragraph = {
            'id': 'end_paragraph',
            'text': '',
            'audio': '',
            'created_at': datetime.datetime.now().isoformat(),
            'is_end_paragraph': True
        }
        
        # 重新构建段落列表，确保只有一个结尾段落块且在最后
        self.paragraphs = regular_paragraphs + [end_paragraph]
    
    def add_paragraph(self, text='', after_id=None):
        paragraph = {
            'id': str(uuid.uuid4()),
            'text': text,
            'audio': '',
            'created_at': datetime.datetime.now().isoformat()
        }
        
        if after_id:
            # 查找after_id对应的索引
            insert_index = -1
            for i, p in enumerate(self.paragraphs):
                if p['id'] == after_id:
                    insert_index = i + 1  # 在找到的段落后面插入
                    break
            
            if insert_index != -1:
                # 在找到的位置插入
                self.paragraphs.insert(insert_index, paragraph)
            else:
                # 如果没找到，添加到末尾
                self.paragraphs.append(paragraph)
        else:
            # 没有指定after_id，添加到末尾
            self.paragraphs.append(paragraph)
        
        return paragraph
    
    def update_paragraph(self, paragraph_id, text):
        for paragraph in self.paragraphs:
            if paragraph['id'] == paragraph_id:
                paragraph['text'] = text
                return paragraph
        return None
    
    def delete_paragraph(self, paragraph_id):
        for i, paragraph in enumerate(self.paragraphs):
            if paragraph['id'] == paragraph_id:
                # 删除关联的音频文件
                if paragraph['audio']:
                    audio_path = os.path.join(self.audio_dir, paragraph['audio'])
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                # 删除段落
                del self.paragraphs[i]
                return True
        return False
    
    def add_audio(self, paragraph_id, audio_filename):
        for paragraph in self.paragraphs:
            if paragraph['id'] == paragraph_id:
                # 删除旧的音频文件
                if paragraph['audio']:
                    old_audio_path = os.path.join(self.audio_dir, paragraph['audio'])
                    if os.path.exists(old_audio_path):
                        os.remove(old_audio_path)
                # 更新音频文件
                paragraph['audio'] = audio_filename
                return paragraph
        return None
    
    def move_paragraph(self, paragraph_id, direction):
        for i, paragraph in enumerate(self.paragraphs):
            if paragraph['id'] == paragraph_id:
                new_index = i + direction
                if 0 <= new_index < len(self.paragraphs):
                    # 交换位置
                    self.paragraphs[i], self.paragraphs[new_index] = self.paragraphs[new_index], self.paragraphs[i]
                    return True
                break
        return False
    
    def get_full_text(self):
        return '\n'.join([p['text'] for p in self.paragraphs if p['text'].strip() and not p.get('is_end_paragraph')])
    
    def save(self):
        # 保存章节内容到文件
        import json
        import threading
        import os
        
        # 确保结尾段落块在最后，清理重复的结尾段落块
        self.ensure_end_paragraph()
        
        content_file = os.path.join(self.chapter_dir, 'content.json')
        temp_file = content_file + '.tmp'
        
        # 使用模块级别的锁确保文件写入的原子性
        if not hasattr(Chapter, '_save_lock'):
            Chapter._save_lock = threading.Lock()
        
        with Chapter._save_lock:
            # 先将数据序列化为字符串，确保数据完整性
            data = {
                'id': self.id,
                'title': self.title,
                'paragraphs': self.paragraphs
            }
            
            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 使用原子操作重命名文件，确保写入的完整性
            os.replace(temp_file, content_file)
    
    @staticmethod
    def load(chapter_id, book_id):
        chapter_dir = os.path.join(app.config['BOOKS_FOLDER'], book_id, 'chapters', chapter_id)
        content_file = os.path.join(chapter_dir, 'content.json')
        
        if os.path.exists(content_file):
            import json
            
            # 直接加载JSON文件，不进行任何修复
            with open(content_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chapter = Chapter(data['id'], data['title'], book_id)
            chapter.paragraphs = data.get('paragraphs', [])
            
            # 确保总是有一个结尾段落块，并且在最后位置
            chapter.ensure_end_paragraph()
            
            return chapter
        return None

class Book:
    def __init__(self, book_id, title, author=''):
        self.id = book_id
        self.title = title
        self.author = author
        self.chapters = []
        self.book_dir = os.path.join(app.config['BOOKS_FOLDER'], book_id)
        self.chapters_dir = os.path.join(self.book_dir, 'chapters')
        
        # 创建书籍目录
        os.makedirs(self.book_dir, exist_ok=True)
        os.makedirs(self.chapters_dir, exist_ok=True)
    
    def add_chapter(self, title='新章节'):
        chapter = {
            'id': str(uuid.uuid4()),
            'title': title,
            'created_at': datetime.datetime.now().isoformat()
        }
        self.chapters.append(chapter)
        
        # 创建章节文件
        chapter_obj = Chapter(chapter['id'], chapter['title'], self.id)
        chapter_obj.save()
        
        self.save()
        return chapter
    
    def update_chapter(self, chapter_id, title):
        for chapter in self.chapters:
            if chapter['id'] == chapter_id:
                chapter['title'] = title
                self.save()
                return chapter
        return None
    
    def delete_chapter(self, chapter_id):
        for i, chapter in enumerate(self.chapters):
            if chapter['id'] == chapter_id:
                # 删除章节目录
                chapter_dir = os.path.join(self.chapters_dir, chapter_id)
                if os.path.exists(chapter_dir):
                    import shutil
                    shutil.rmtree(chapter_dir)
                # 删除章节
                del self.chapters[i]
                self.save()
                return True
        return False
    
    def save(self):
        # 保存书籍信息到文件
        info_file = os.path.join(self.book_dir, 'book_info.json')
        import json
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump({
                'id': self.id,
                'title': self.title,
                'author': self.author,
                'chapters': self.chapters
            }, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load(book_id):
        book_dir = os.path.join(app.config['BOOKS_FOLDER'], book_id)
        info_file = os.path.join(book_dir, 'book_info.json')
        
        if os.path.exists(info_file):
            import json
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            book = Book(data['id'], data['title'], data['author'])
            book.chapters = data['chapters']
            return book
        return None
    
    @staticmethod
    def get_all_books():
        books = []
        for book_dir in os.listdir(app.config['BOOKS_FOLDER']):
            book_path = os.path.join(app.config['BOOKS_FOLDER'], book_dir)
            if os.path.isdir(book_path):
                info_file = os.path.join(book_path, 'book_info.json')
                if os.path.exists(info_file):
                    import json
                    with open(info_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    books.append(data)
        return books

@app.route('/')
def index():
    return render_template('bookshelf.html')

@app.route('/book/<book_id>')
def book_detail(book_id):
    return render_template('book.html', book_id=book_id)

@app.route('/editor/<book_id>/<chapter_id>')
def editor(book_id, chapter_id):
    return render_template('editor.html', book_id=book_id, chapter_id=chapter_id)

# 书籍相关API
@app.route('/api/books', methods=['GET'])
def get_books():
    books = Book.get_all_books()
    return jsonify({'success': True, 'books': books})

@app.route('/api/book/new', methods=['POST'])
def new_book():
    title = request.json.get('title', '未命名书籍')
    author = request.json.get('author', '')
    book_id = str(uuid.uuid4())
    
    book = Book(book_id, title, author)
    book.save()
    
    return jsonify({
        'success': True,
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author
        }
    })

@app.route('/api/book/<book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.load(book_id)
    if book:
        return jsonify({
            'success': True,
            'book': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'chapters': book.chapters
            }
        })
    return jsonify({'success': False, 'message': '书籍不存在'})

@app.route('/api/book/<book_id>/update', methods=['POST'])
def update_book(book_id):
    book = Book.load(book_id)
    if not book:
        return jsonify({'success': False, 'message': '书籍不存在'})
    
    title = request.json.get('title')
    author = request.json.get('author')
    
    if title:
        book.title = title
    if author is not None:
        book.author = author
    
    book.save()
    return jsonify({
        'success': True,
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author
        }
    })

@app.route('/api/book/<book_id>/delete', methods=['DELETE'])
def delete_book(book_id):
    book_dir = os.path.join(app.config['BOOKS_FOLDER'], book_id)
    if os.path.exists(book_dir):
        import shutil
        shutil.rmtree(book_dir)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '书籍不存在'})

# 章节相关API
@app.route('/api/book/<book_id>/chapter/new', methods=['POST'])
def new_chapter(book_id):
    book = Book.load(book_id)
    if not book:
        return jsonify({'success': False, 'message': '书籍不存在'})
    
    title = request.json.get('title', '新章节')
    chapter = book.add_chapter(title)
    
    return jsonify({'success': True, 'chapter': chapter})

@app.route('/api/book/<book_id>/chapter/<chapter_id>/update', methods=['POST'])
def update_chapter(book_id, chapter_id):
    book = Book.load(book_id)
    if not book:
        return jsonify({'success': False, 'message': '书籍不存在'})
    
    title = request.json.get('title')
    if not title:
        return jsonify({'success': False, 'message': '章节标题不能为空'})
    
    chapter = book.update_chapter(chapter_id, title)
    if chapter:
        return jsonify({'success': True, 'chapter': chapter})
    return jsonify({'success': False, 'message': '章节不存在'})

@app.route('/api/book/<book_id>/chapter/<chapter_id>/delete', methods=['DELETE'])
def delete_chapter(book_id, chapter_id):
    book = Book.load(book_id)
    if not book:
        return jsonify({'success': False, 'message': '书籍不存在'})
    
    if book.delete_chapter(chapter_id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '章节不存在'})

# 段落相关API
@app.route('/api/chapter/<book_id>/<chapter_id>/paragraphs', methods=['GET'])
def get_paragraphs(book_id, chapter_id):
    chapter = Chapter.load(chapter_id, book_id)
    if chapter:
        return jsonify({
            'success': True,
            'paragraphs': chapter.paragraphs,
            'full_text': chapter.get_full_text()
        })
    return jsonify({'success': False, 'message': '章节不存在'})

@app.route('/api/chapter/<book_id>/<chapter_id>/paragraph/add', methods=['POST'])
def add_paragraph(book_id, chapter_id):
    try:
        chapter = Chapter.load(chapter_id, book_id)
        if not chapter:
            return jsonify({'success': False, 'message': '章节不存在'})
        
        text = request.json.get('text', '')
        after_id = request.json.get('after_id')
        paragraph = chapter.add_paragraph(text, after_id)
        chapter.save()
        
        return jsonify({'success': True, 'paragraphs': chapter.paragraphs, 'full_text': chapter.get_full_text()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'添加段落失败: {str(e)}'})

@app.route('/api/chapter/<book_id>/<chapter_id>/paragraph/update', methods=['POST'])
def update_paragraph(book_id, chapter_id):
    try:
        chapter = Chapter.load(chapter_id, book_id)
        if not chapter:
            return jsonify({'success': False, 'message': '章节不存在'})
        
        paragraph_id = request.json.get('id')
        text = request.json.get('text')
        
        if not paragraph_id or text is None:
            return jsonify({'success': False, 'message': '参数错误'})
        
        paragraph = chapter.update_paragraph(paragraph_id, text)
        if paragraph:
            chapter.save()
            return jsonify({'success': True, 'paragraph': paragraph, 'full_text': chapter.get_full_text()})
        
        return jsonify({'success': False, 'message': '段落不存在'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'更新段落失败: {str(e)}'})

@app.route('/api/chapter/<book_id>/<chapter_id>/paragraph/delete/<paragraph_id>', methods=['DELETE'])
def delete_paragraph(book_id, chapter_id, paragraph_id):
    try:
        chapter = Chapter.load(chapter_id, book_id)
        if not chapter:
            return jsonify({'success': False, 'message': '章节不存在'})
        
        if chapter.delete_paragraph(paragraph_id):
            chapter.save()
            return jsonify({'success': True, 'full_text': chapter.get_full_text()})
        
        return jsonify({'success': False, 'message': '段落不存在'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'删除段落失败: {str(e)}'})

@app.route('/api/chapter/<book_id>/<chapter_id>/paragraph/move/<paragraph_id>/<direction>', methods=['POST'])
def move_paragraph(book_id, chapter_id, paragraph_id, direction):
    try:
        chapter = Chapter.load(chapter_id, book_id)
        if not chapter:
            return jsonify({'success': False, 'message': '章节不存在'})
        
        direction = 1 if direction == 'down' else -1
        if chapter.move_paragraph(paragraph_id, direction):
            chapter.save()
            return jsonify({'success': True, 'paragraphs': chapter.paragraphs, 'full_text': chapter.get_full_text()})
        
        return jsonify({'success': False, 'message': '移动失败'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'移动段落失败: {str(e)}'})

# 音频相关API
@app.route('/api/chapter/<book_id>/<chapter_id>/audio/upload/<paragraph_id>', methods=['POST'])
def upload_audio(book_id, chapter_id, paragraph_id):
    try:
        chapter = Chapter.load(chapter_id, book_id)
        if not chapter:
            return jsonify({'success': False, 'message': '章节不存在'})
        
        if 'audio' not in request.files:
            return jsonify({'success': False, 'message': '没有音频文件'})
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        # 生成唯一的文件名
        filename = f"{paragraph_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        # 保存文件到章节的音频目录
        audio_path = os.path.join(chapter.audio_dir, filename)
        audio_file.save(audio_path)
        
        # 更新段落的音频信息
        paragraph = chapter.add_audio(paragraph_id, filename)
        if paragraph:
            chapter.save()
            return jsonify({'success': True, 'paragraph': paragraph})
        
        return jsonify({'success': False, 'message': '段落不存在'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'上传录音失败: {str(e)}'})

@app.route('/api/audio/<book_id>/<chapter_id>/<filename>')
def get_audio(book_id, chapter_id, filename):
    audio_dir = os.path.join(app.config['BOOKS_FOLDER'], book_id, 'chapters', chapter_id, 'audio')
    return send_from_directory(audio_dir, filename)

@app.route('/api/chapter/<book_id>/<chapter_id>/audio/delete/<paragraph_id>', methods=['POST'])
def delete_audio(book_id, chapter_id, paragraph_id):
    try:
        chapter = Chapter.load(chapter_id, book_id)
        if not chapter:
            return jsonify({'success': False, 'message': '章节不存在'})
        
        # 删除段落的音频文件
        for i, paragraph in enumerate(chapter.paragraphs):
            if paragraph['id'] == paragraph_id:
                # 删除关联的音频文件
                if paragraph['audio']:
                    audio_path = os.path.join(chapter.audio_dir, paragraph['audio'])
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                # 更新段落信息
                paragraph['audio'] = ''
                chapter.save()
                return jsonify({'success': True, 'paragraph': paragraph})
        
        return jsonify({'success': False, 'message': '段落不存在'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'删除录音失败: {str(e)}'})

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
    print(f"HTTPS访问地址：{https_url}")
    print(f"注意，跨设备访问需在同一局域网下")
    print(f"当前版本 v{CURRENT_VERSION}，项目地址：https://github.com/{GITHUB_REPO}")
    print(f"首次访问HTTPS会提示证书不安全，点击'高级'->'继续访问'即可")
    
    # 关闭debug模式，避免自动重启导致的无限循环
    # 使用自签名证书支持HTTPS
    import ssl
    
    # 使用新生成的证书文件
    cert_file = 'localhost.crt'
    key_file = 'localhost.key'
    
    # 直接使用新生成的证书，无需检查存在性，因为我们已经生成了
    print(f"使用新生成的证书文件：{cert_file} 和 {key_file}")
    try:
        # 使用新生成的证书
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_file, key_file)
        # 启动HTTPS服务器
        print(f"正在启动HTTPS服务器...")
        app.run(debug=False, host='0.0.0.0', port=port, ssl_context=ssl_context)
    except Exception as e:
        print(f"HTTPS启动失败：{str(e)}")
        print("正在尝试启动HTTP服务器...")
        # 回退到HTTP
        app.run(debug=False, host='0.0.0.0', port=port)
