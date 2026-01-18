# DBInputNote —— 如我所述 如我所书

[![GitHub Stars](https://img.shields.io/github/stars/ChaserSu/DBInputNote?style=social)](https://github.com/ChaserSu/DBInputNote)
[![GitHub Forks](https://img.shields.io/github/forks/ChaserSu/DBInputNote?style=social)](https://github.com/ChaserSu/DBInputNote)

> 【这是一个超早期的demo，请勿用于生产环境】

## 📖 项目简介

人人有模型练，人人有故事写，在写作初期就将作品本身作为一个智能体来培养。

DBInputNote是一款专为网文作者设计的文本编辑器，在创作阶段就以分段录入的形式准备语音训练的标注数据，支持语音识别（即将上线）和闲时语音模型自训练（即将上线），为每一本书准备一个最合适的语音模型。

## ✨ 核心功能

- 📝 **分段录入**：以分段形式录入文本，同时生成语音训练标注数据
- 🎤 **语音识别**：支持语音输入转文本（即将上线）
- 🤖 **模型自训练**：利用作者自己的语音和文本数据训练专属模型（即将上线）
- 💻 **跨平台运行**：前后端分离设计，支持在各种硬件上部署
- 🌐 **多设备访问**：可在手机、平板、PC等任意设备上使用

## 🎯 开发目标

- 在16GB显存设备上实现模型自训练
- 支持作者自己的台式机、服务器、云服务器集群、家用NAS等平台长期运行
- 提供一致的多设备写作体验
- 为每本书生成专属语音模型

## 🛠️ 技术栈

### 后端
- Python
- Flask

### 前端
- Web技术栈（HTML/CSS/JavaScript）

### 核心特性
- 前后端分离架构
- 支持跨平台部署
- 语音数据处理与模型训练

## 🚀 快速开始

### 环境要求
- Python 3.7+
- Flask
- 其他依赖包（见requirements.txt）

### 启动方式
#### 从预编译二进制文件启动
（Windows AMD64推荐）

直接去[Release](https://github.com/ChaserSu/DBInputNote/releases)下载预编译二进制文件。

#### 从源代码启动
（Windows ARM或其他系统下需要从源代码启动源代码）

1. 克隆仓库
   ```bash
   git clone https://github.com/ChaserSu/DBInputNote.git
   cd DBInputNote
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 启动应用
   ```bash
   python app.py
   ```

4. 在浏览器中访问
   ```
   http://localhost:5000
   ```

5. 同局域网设备可通过IP地址访问（或扫描生成的二维码）
   ```
   http://<your-ip>:5000
   ```

## 📸 界面预览

### 编辑页面
<img width="686" height="514" alt="编辑页面" src="https://github.com/user-attachments/assets/c3c69890-40d4-4077-b7a8-ad9b76c7ffcd" />

### 章节管理页面
<img width="686" height="514" alt="章节管理页面" src="https://github.com/user-attachments/assets/9c32ecbf-3c9d-4d88-8469-ba6975e3ccfd" />

### 首页
<img width="686" height="514" alt="首页" src="https://github.com/user-attachments/assets/240745a3-941c-440c-89ff-27bb701893e1" />

### 多设备访问
<img width="381" height="381" alt="多设备访问" src="https://github.com/user-attachments/assets/1fd72cf7-f217-4b56-ac6f-bfdbc6bf9bcb" />

## 📊 Coding Analysis

### GitHub Stats
![GitHub Stats](https://github-readme-stats.vercel.app/api?username=ChaserSu&show_icons=true)

### Top Languages
![Top Languages](https://github-readme-stats.vercel.app/api/top-langs/?username=ChaserSu&layout=compact&show_icons=true)

## 📝 创作理念

AI写作比传统写作效率更高，但出于网文作者的朴素情感和创作路径依赖，我们更倾向于"人力+语音"的传统创作方式。

在AI文大量涌入的背景下，许多纯人力作者开始引入各种工具提升效率。我们认为，创作本身高度依赖AI生成，可能会切断个人创作者的水平成长路径。

DBInputNote旨在帮助作者在保持人力创作核心的同时，利用AI技术提升效率，为每一位作者打造专属的写作工具和语音模型。

## 🤝 贡献指南

欢迎对项目提出建议和贡献！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📧 联系方式

- GitHub: [@ChaserSu](https://github.com/ChaserSu)
- 项目地址: [https://github.com/ChaserSu/DBInputNote](https://github.com/ChaserSu/DBInputNote)

## 🎯 未来规划

- [ ] 语音识别功能
- [ ] 闲时语音模型自训练
- [ ] 更完善的章节管理
- [ ] 多格式导出功能
- [ ] 云端同步
- [ ] 转移至electron
- [ ] 发布全平台的服务端和客户端

---

> 早岁已知世事艰，仍许飞鸿荡云间。
> 一路寒风身如絮，命海沉浮客独行。
> 千磨万击心铸铁，殚精竭虑铸一剑。
> 今朝剑指叠云处，炼蛊炼人还炼天!
