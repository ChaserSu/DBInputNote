from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import sys
import uuid
import datetime
import subprocess

app = Flask(__name__)

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
                # 删除关联的音频文件和所有识别结果文件
                if paragraph['audio']:
                    # 获取音频文件的基本名称（不含扩展名）
                    audio_filename = paragraph['audio']
                    base_name = os.path.splitext(audio_filename)[0]
                    
                    # 定义所有可能的文件扩展名
                    extensions = ['.wav', '.merge.txt', '.txt', '.srt', '.json']
                    
                    # 删除所有相关文件
                    for ext in extensions:
                        file_path = os.path.join(self.audio_dir, base_name + ext)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                # 删除段落
                del self.paragraphs[i]
                return True
        return False
    
    def add_audio(self, paragraph_id, audio_filename):
        for paragraph in self.paragraphs:
            if paragraph['id'] == paragraph_id:
                # 删除旧的音频文件和所有识别结果文件
                if paragraph['audio']:
                    # 获取旧音频文件的基本名称（不含扩展名）
                    old_audio_filename = paragraph['audio']
                    old_base_name = os.path.splitext(old_audio_filename)[0]
                    
                    # 定义所有可能的文件扩展名
                    extensions = ['.wav', '.merge.txt', '.txt', '.srt', '.json']
                    
                    # 删除所有相关文件
                    for ext in extensions:
                        file_path = os.path.join(self.audio_dir, old_base_name + ext)
                        if os.path.exists(file_path):
                            os.remove(file_path)
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
        
        # 获取录音开始时间
        start_time = request.form.get('start_time')
        
        # 生成唯一的文件名
        filename = f"{paragraph_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        # 保存文件到章节的音频目录
        audio_path = os.path.join(chapter.audio_dir, filename)
        audio_file.save(audio_path)
        
        # 更新段落的音频信息
        paragraph = chapter.add_audio(paragraph_id, filename)
        if paragraph:
            chapter.save()
            # 返回音频文件的完整路径和开始时间
            return jsonify({
                'success': True, 
                'paragraph': paragraph,
                'audio_path': audio_path,
                'start_time': start_time
            })
        
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
                # 删除关联的音频文件和所有识别结果文件
                if paragraph['audio']:
                    # 获取音频文件的基本名称（不含扩展名）
                    audio_filename = paragraph['audio']
                    base_name = os.path.splitext(audio_filename)[0]
                    
                    # 定义所有可能的文件扩展名
                    extensions = ['.wav', '.merge.txt', '.txt', '.srt', '.json']
                    
                    # 删除所有相关文件
                    for ext in extensions:
                        file_path = os.path.join(chapter.audio_dir, base_name + ext)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                # 更新段落信息
                paragraph['audio'] = ''
                chapter.save()
                return jsonify({'success': True, 'paragraph': paragraph})
        
        return jsonify({'success': False, 'message': '段落不存在'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'删除录音失败: {str(e)}'})

# 语音识别API
@app.route('/api/recognize-audio', methods=['POST'])
def recognize_audio():
    try:
        # 获取音频文件路径和录音开始时间
        data = request.json
        audio_path = data.get('audio_path')
        start_time = data.get('start_time')
        
        if not audio_path or not os.path.exists(audio_path):
            return jsonify({'success': False, 'message': '音频文件不存在'})
        
        # 从音频文件路径中提取book_id、chapter_id和paragraph_id
        # 音频文件路径格式：books/{book_id}/chapters/{chapter_id}/audio/{paragraph_id}_{timestamp}.wav
        parts = audio_path.split(os.sep)
        # 查找books目录的索引
        books_index = parts.index('books')
        book_id = parts[books_index + 1]
        chapter_id = parts[books_index + 3]
        # 从文件名中提取paragraph_id
        audio_filename = parts[-1]
        paragraph_id = audio_filename.split('_')[0]
        
        # 调用start_client.exe进行语音识别
        start_client_path = os.path.join('CW', 'start_client.exe')
        cmd = [
            start_client_path,
            audio_path
        ]
        
        # 启动start_client.exe进程，并实时读取输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            universal_newlines=True
        )
        
        # 实时读取输出，提取识别结果和音频长度
        audio_duration = 0.0  # 音频长度（秒）
        recognized_text = ''
        in_recognition_result = False
        recognition_done = False
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            
            # 打印start_client.exe的输出，方便调试
            print(line.strip())
            
            # 提取音频长度
            if "音频长度：" in line:
                try:
                    # 格式："    音频长度：3.12s "
                    duration_str = line.split("音频长度：")[1].strip()
                    audio_duration = float(duration_str.replace("s", ""))
                except (IndexError, ValueError):
                    pass
            
            # 提取识别结果
            if "识别结果：" in line:
                in_recognition_result = True
            elif in_recognition_result:
                # 跳过空行
                if line.strip():
                    recognized_text = line.strip()
                    in_recognition_result = False
                    recognition_done = True
                    # 一旦获取到识别结果，就可以跳出循环，不需要等待结束标志
                    break
            
            # 检查是否识别结束（冗余检查，防止异常情况）
            if "RECOGNITION_COMPLETE" in line:
                recognition_done = True
                break
        
        # 杀死start_client.exe进程
        process.terminate()
        try:
            process.wait(timeout=5)  # 等待进程终止，最多5秒
        except subprocess.TimeoutExpired:
            process.kill()
        
        # 直接更新content.json文件中的对应段落内容
        if recognition_done and recognized_text:
            chapter = Chapter.load(chapter_id, book_id)
            if chapter:
                # 计算转录延迟
                transcribe_delay = None
                if start_time:
                    try:
                        # 计算从开始录音到转录完成的总时间（秒）
                        current_time = datetime.datetime.now().timestamp() * 1000  # 转换为毫秒
                        total_delay_ms = current_time - float(start_time)
                        total_delay = total_delay_ms / 1000  # 转换为秒
                        
                        # 减去音频长度，得到真正的转录处理时间
                        transcribe_delay = max(0, round(total_delay - audio_duration, 2))  # 确保非负，保留两位小数
                    except ValueError:
                        pass
                
                # 更新对应段落的文本和转录延迟
                for paragraph in chapter.paragraphs:
                    if paragraph['id'] == paragraph_id:
                        paragraph['text'] = recognized_text
                        if transcribe_delay is not None:
                            paragraph['transcribe_delay'] = transcribe_delay
                        break
                # 保存更新后的章节内容
                chapter.save()
            
            return jsonify({
                'success': True,
                'text': recognized_text
            })
        else:
            error_msg = f"识别失败：未获取到识别结果"
            print(error_msg)
            return jsonify({
                'success': False,
                'message': error_msg
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'语音识别失败: {str(e)}'})

if __name__ == '__main__':
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='DBInputNote App Server')
    parser.add_argument('--port', type=int, default=5001, help='服务器端口')
    parser.add_argument('--ssl', action='store_true', help='是否使用SSL')
    parser.add_argument('--cert', type=str, default='localhost.crt', help='SSL证书文件路径')
    parser.add_argument('--key', type=str, default='localhost.key', help='SSL密钥文件路径')
    
    args = parser.parse_args()
    
    if args.ssl:
        # 使用HTTPS模式运行
        print(f"\napp.py HTTPS运行模式")
        print(f"HTTPS访问地址：https://0.0.0.0:{args.port}")
        print(f"使用证书：{args.cert} 和 {args.key}")
        
        try:
            import ssl
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(args.cert, args.key)
            app.run(debug=False, host='0.0.0.0', port=args.port, ssl_context=ssl_context)
        except Exception as e:
            print(f"HTTPS启动失败：{str(e)}")
            print("正在尝试回退到HTTP模式...")
            # 回退到HTTP模式
            print(f"HTTP访问地址：http://0.0.0.0:{args.port}")
            app.run(debug=False, host='0.0.0.0', port=args.port)
    else:
        # 直接运行时使用HTTP
        print(f"\napp.py 独立运行模式")
        print(f"HTTP访问地址：http://0.0.0.0:{args.port}")
        app.run(debug=False, host='0.0.0.0', port=args.port)
