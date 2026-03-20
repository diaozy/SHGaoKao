# 上海高考志愿填报辅助系统

基于 Flask + Vue3 的上海高考志愿填报辅助系统，提供分数查询、模拟填报、高中分析、专业指导等功能。

**🌐 访问地址**: http://shgk.xihu-nttdata.top

## 功能特点

- **分数查询**：输入高考分数，智能匹配可填报院校，显示录取概率
- **模拟填报**：24个平行志愿模拟分析，预测落档风险
- **高中分析**：四校、四分、八校及其他重点高中录取数据分析
- **专业指导**：热门专业介绍、就业前景、选科要求
- **AI智能推荐**：集成腾讯云GLM-5，提供个性化推荐建议

## 数据覆盖

- 2020-2025年上海高考分数线
- 25+所985/211及上海本地高校录取数据
- 42所上海重点高中录取统计
- 100+热门专业信息

## 技术栈

- **后端**: Flask (Python)
- **前端**: Vue 3 + Tailwind CSS (CDN引入)
- **数据**: 本地JSON文件存储
- **AI**: 腾讯云GLM-5 API

## 快速开始

### 1. 安装依赖

```bash
pip install flask requests
```

### 2. 启动服务

```bash
cd sh-gaokao-helper
python app.py
```

### 3. 访问系统

打开浏览器访问: http://localhost:5000

## 项目结构

```
sh-gaokao-helper/
├── app.py                 # Flask主应用
├── requirements.txt       # Python依赖
├── README.md             # 项目说明
├── data/                 # 数据文件
│   ├── score_lines.json  # 分数线数据
│   ├── universities.json # 院校录取数据
│   ├── high_schools.json # 高中数据
│   └── majors.json       # 专业数据
└── templates/            # 页面模板
    ├── index.html        # 首页
    ├── query.html        # 分数查询
    ├── simulate.html     # 模拟填报
    ├── school.html       # 高中分析
    └── major.html        # 专业指导
```

## API接口

### 分数查询
```
GET /api/score?score=550&year=2024
```

### 模拟填报分析
```
POST /api/predict
{
    "score": 550,
    "choices": [{"id": 1}, {"id": 2}]
}
```

### 高中数据
```
GET /api/schools?type=四校&district=徐汇区
```

### 专业数据
```
GET /api/majors?category=工学&keyword=计算机
```

### AI智能推荐
```
POST /api/recommend
{
    "score": 550,
    "interests": ["计算机", "金融"],
    "location": "上海"
}
```

## 配置AI推荐（可选）

设置环境变量以启用GLM-5智能推荐：

```bash
export GLM_API_KEY="your_api_key"
export GLM_API_URL="https://open.bigmodel.cn/api/paas/v4/chat/completions"
```

## 注意事项

- 本系统仅供参考，志愿填报请以官方信息为准
- 数据来源于公开信息，可能存在偏差
- 建议结合多方信息进行综合判断

## 部署说明

### 生产环境部署

```bash
# 1. 克隆仓库
git clone https://github.com/diaozy/sh-gaokao-helper.git
cd sh-gaokao-helper

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务（端口5001）
python app.py
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name shgk.xihu-nttdata.top;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## SEO 优化

- ✅ Meta Description & Keywords
- ✅ Open Graph 标签
- ✅ Schema.org 结构化数据
- ✅ 语义化 HTML 结构
- ✅ 移动端响应式设计

## 更新日志

### v1.1.0 (2026-03-20)
- ✅ 修复历年分数查询页面图表显示问题
- ✅ 更换Chart.js CDN源
- ✅ 添加访问计数功能
- ✅ API接口: `/api/counter` 获取访问统计

### v1.0.0 (2026-03-20)
- ✅ 初始版本发布
- ✅ 添加 SEO 优化
- ✅ 部署到 shgk.xihu-nttdata.top

## 许可证

MIT License
