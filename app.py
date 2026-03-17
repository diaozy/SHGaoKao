#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海高考志愿填报辅助系统
Shanghai Gaokao Helper System
"""

import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from functools import lru_cache

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# 腾讯云 GLM-5 配置
GLM_API_URL = os.environ.get('GLM_API_URL', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')
GLM_API_KEY = os.environ.get('GLM_API_KEY', '')

# ==================== 数据加载 ====================

@lru_cache(maxsize=10)
def load_json_data(filename):
    """加载JSON数据文件"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_universities():
    return load_json_data('universities.json').get('universities', [])

def get_admission_scores():
    return load_json_data('admission_scores.json')

def get_high_schools():
    return load_json_data('high_schools.json').get('schools', [])

def get_majors():
    data = load_json_data('majors.json')
    # 从categories中提取所有专业
    majors = []
    for cat in data.get('categories', []):
        for major in cat.get('majors', []):
            major['category'] = cat.get('name', '')
            majors.append(major)
    return majors

def get_score_lines():
    return load_json_data('score_lines.json').get('score_lines', [])

def get_news():
    return load_json_data('news.json')

# ==================== 辅助函数 ====================

def get_rank_by_score(score, year=2024):
    """根据分数估算全市排名"""
    if score >= 610:
        return max(1, int((660 - score) * 5 + 50))
    elif score >= 580:
        return int((610 - score) * 50 + 300)
    elif score >= 550:
        return int((580 - score) * 100 + 1500)
    elif score >= 520:
        return int((550 - score) * 200 + 4500)
    elif score >= 480:
        return int((520 - score) * 300 + 10500)
    elif score >= 440:
        return int((480 - score) * 400 + 22500)
    elif score >= 400:
        return int((440 - score) * 500 + 38500)
    else:
        return int((400 - score) * 300 + 48500)

def calculate_probability(score, min_score, avg_score):
    """计算录取概率"""
    if score >= avg_score + 10:
        return 95
    elif score >= avg_score:
        return 85
    elif score >= min_score + 10:
        return 75
    elif score >= min_score:
        return 60
    elif score >= min_score - 5:
        return 40
    elif score >= min_score - 10:
        return 25
    else:
        return 10

def call_glm(prompt):
    """调用腾讯云 GLM-5 API"""
    if not GLM_API_KEY:
        return None
    try:
        headers = {
            'Authorization': f'Bearer {GLM_API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'glm-4',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
            'max_tokens': 1500
        }
        resp = requests.post(GLM_API_URL, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"GLM API error: {e}")
    return None

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    stats = {
        'universities': len(load_json_data('universities.json').get('universities', [])),
        'majors': sum(len(cat.get('majors', [])) for cat in load_json_data('majors.json').get('categories', [])),
        'schools': len(load_json_data('high_schools.json').get('schools', [])),
        'years': 6
    }
    return render_template('index.html', stats=stats)

@app.route('/query')
def query():
    """分数查询页面"""
    return render_template('query.html')

@app.route('/simulate')
def simulate():
    """模拟填报页面"""
    return render_template('simulate.html')

@app.route('/school')
def school():
    """高中分析页面"""
    return render_template('school.html')

@app.route('/major')
def major():
    """专业指导页面"""
    return render_template('major.html')

@app.route('/news')
def news():
    """政策资讯页面"""
    return render_template('news.html')

@app.route('/sources')
def sources():
    """数据来源说明页面"""
    return render_template('sources.html')

# ==================== API 路由 ====================

@app.route('/api/score', methods=['GET', 'POST'])
def api_score():
    """输入分数和年份，返回可填报院校列表"""
    if request.method == 'GET':
        score = request.args.get('score', type=int)
        year = request.args.get('year', default=2024, type=int)
    else:
        data = request.get_json() or {}
        score = data.get('score')
        year = data.get('year', 2024)

    if not score or score < 0 or score > 660:
        return jsonify({'success': False, 'message': '请提供有效分数(0-660)'}), 400

    universities = get_universities()
    score_lines = get_score_lines()

    # 获取分数线
    year_line = next((sl for sl in score_lines if sl['year'] == year), score_lines[0] if score_lines else None)
    special_line = year_line['batches']['special_type']['score'] if year_line else 503
    undergraduate_line = year_line['batches']['undergraduate']['score'] if year_line else 403

    # 计算排名
    rank = get_rank_by_score(score, year)

    # 筛选院校
    results = []
    for uni in universities:
        # 检查 admission_data 是否为有效列表
        admission_data_list = uni.get('admission_data', [])
        if isinstance(admission_data_list, dict):
            # 如果是字典（如 {"note": "暂无数据"}），跳过
            continue
        admission_data = next((ad for ad in admission_data_list if ad['year'] <= year), None)
        if not admission_data:
            continue

        min_score = admission_data.get('min_score', 0)
        avg_score = admission_data.get('avg_score', 0)

        # 分数范围筛选
        if score < min_score - 30:
            continue

        probability = calculate_probability(score, min_score, avg_score)

        # 推荐等级
        if probability >= 85:
            level = '稳妥'
        elif probability >= 60:
            level = '较稳'
        elif probability >= 40:
            level = '有风险'
        else:
            level = '冲一冲'

        results.append({
            'id': uni['id'],
            'name': uni['name'],
            'code': uni['code'],
            'level': uni['level'],
            'location': uni['location'],
            'type': uni['type'],
            'min_score': min_score,
            'avg_score': avg_score,
            'gap': score - min_score,
            'probability': probability,
            'recommend_level': level,
            'popular_majors': uni.get('popular_majors', []),
            'description': uni.get('description', '')
        })

    results.sort(key=lambda x: (-x['probability'], -x['avg_score']))

    return jsonify({
        'success': True,
        'data': {
            'score': score,
            'year': year,
            'rank': rank,
            'special_line': special_line,
            'undergraduate_line': undergraduate_line,
            'total': len(results),
            'universities': results[:50]
        }
    })

@app.route('/api/predict', methods=['GET', 'POST'])
def api_predict():
    """输入分数和志愿，返回落档预测"""
    if request.method == 'GET':
        score = request.args.get('score', type=int)
        choices = request.args.getlist('choices')
    else:
        data = request.get_json() or {}
        score = data.get('score')
        choices = data.get('choices', [])

    if not score:
        return jsonify({'success': False, 'message': '请提供分数'}), 400
    if not choices:
        return jsonify({'success': False, 'message': '请提供志愿列表'}), 400

    universities = {u['id']: u for u in get_universities()}
    results = []
    total_probability = 0

    for idx, choice in enumerate(choices):
        uni_id = choice.get('id') if isinstance(choice, dict) else choice
        uni = universities.get(uni_id)

        if not uni:
            results.append({'order': idx + 1, 'status': '未找到院校', 'probability': 0})
            continue

        # 检查 admission_data 是否为有效列表
        admission_data_list = uni.get('admission_data', [])
        if isinstance(admission_data_list, dict):
            min_score, avg_score = 0, 0
        else:
            admission_data = next((ad for ad in admission_data_list), None)
            min_score = admission_data.get('min_score', 0) if admission_data else 0
            avg_score = admission_data.get('avg_score', 0) if admission_data else 0

        probability = calculate_probability(score, min_score, avg_score)

        if probability >= 75:
            status = '极可能录取'
        elif probability >= 50:
            status = '可能录取'
        elif probability >= 30:
            status = '有风险'
        else:
            status = '落档风险高'

        results.append({
            'order': idx + 1,
            'name': uni['name'],
            'code': uni['code'],
            'level': uni['level'],
            'location': uni['location'],
            'min_score': min_score,
            'avg_score': avg_score,
            'gap': score - min_score,
            'status': status,
            'probability': probability
        })

        # 累计概率
        if total_probability == 0:
            total_probability = probability
        else:
            remaining = 1 - total_probability / 100
            total_probability = total_probability + remaining * probability

    fall_risk = max(0, 100 - total_probability)
    risk_level = '低风险' if total_probability >= 70 else ('中等风险' if total_probability >= 40 else '高风险')

    # AI 建议
    ai_advice = None
    if GLM_API_KEY:
        uni_names = [r['name'] for r in results if 'name' in r][:5]
        prompt = f"考生分数{score}分（上海高考总分660），填报志愿：{uni_names}。请简要分析志愿填报策略建议（150字内）。"
        ai_advice = call_glm(prompt)

    return jsonify({
        'success': True,
        'data': {
            'score': score,
            'predictions': results,
            'total_probability': round(min(99, total_probability), 1),
            'fall_risk': round(fall_risk, 1),
            'risk_level': risk_level,
            'ai_advice': ai_advice
        }
    })

@app.route('/api/schools')
def api_schools():
    """高中数据分析"""
    schools = get_high_schools()

    # 筛选参数
    school_type = request.args.get('type')
    district = request.args.get('district')
    name = request.args.get('name')

    filtered = schools
    if school_type:
        filtered = [s for s in filtered if s.get('type') == school_type]
    if district:
        filtered = [s for s in filtered if district in s.get('district', '')]
    if name:
        filtered = [s for s in filtered if name in s.get('name', '')]

    # 统计
    summary = {
        'total': len(filtered),
        'by_type': {},
        'by_district': {}
    }
    for s in filtered:
        t = s.get('type', '未知')
        d = s.get('district', '未知')
        summary['by_type'][t] = summary['by_type'].get(t, 0) + 1
        summary['by_district'][d] = summary['by_district'].get(d, 0) + 1

    return jsonify({
        'success': True,
        'data': {
            'summary': summary,
            'schools': filtered
        }
    })

@app.route('/api/majors')
def api_majors():
    """专业查询"""
    # 直接加载原始数据，保留 categories 结构
    data = load_json_data('majors.json')
    categories = data.get('categories', [])
    
    # 同时提供扁平化的 majors 列表
    all_majors = []
    for cat in categories:
        for m in cat.get('majors', []):
            all_majors.append({**m, 'category': cat.get('name', '')})

    category_filter = request.args.get('category')
    name = request.args.get('name')
    keyword = request.args.get('keyword')

    filtered = all_majors
    if category_filter:
        filtered = [m for m in filtered if m.get('category') == category_filter]
    if name:
        filtered = [m for m in filtered if name in m.get('name', '')]
    if keyword:
        filtered = [m for m in filtered if
                    keyword in m.get('name', '') or
                    keyword in m.get('prospects', '') or
                    keyword in m.get('category', '')]

    return jsonify({
        'success': True,
        'data': {
            'total': len(filtered),
            'majors': filtered,
            'categories': categories
        }
    })

@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    """AI 智能推荐（使用 GLM-5）"""
    data = request.get_json() or {}
    score = data.get('score')
    interests = data.get('interests', [])
    location = data.get('location', '')

    if not score:
        return jsonify({'success': False, 'message': '请提供分数'}), 400

    universities = get_universities()
    majors = get_majors()

    # 基础筛选
    matched_unis = []
    for uni in universities:
        ad = next((a for a in uni.get('admission_data', [])), None)
        if ad and score >= ad.get('min_score', 0) - 15:
            matched_unis.append({
                'name': uni['name'],
                'level': uni['level'],
                'location': uni['location'],
                'min_score': ad['min_score'],
                'gap': score - ad['min_score']
            })

    # AI 推荐
    prompt = f"""你是高考志愿填报专家。考生分数{score}分（上海高考，总分660）。
兴趣方向：{', '.join(interests) if interests else '未指定'}
偏好地区：{location or '无特殊偏好'}

符合分数的院校有：{[u['name'] for u in matched_unis[:15]]}

请推荐5所适合的院校和3个适合的专业，简要说明理由（200字内）。"""

    ai_response = call_glm(prompt)

    if not ai_response:
        # 降级推荐
        rush = [u for u in matched_unis if -15 <= u['gap'] < 0][:2]
        stable = [u for u in matched_unis if 0 <= u['gap'] < 15][:3]
        safe = [u for u in matched_unis if u['gap'] >= 15][:2]
        ai_response = f"冲刺：{', '.join([u['name'] for u in rush])}；稳妥：{', '.join([u['name'] for u in stable])}；保底：{', '.join([u['name'] for u in safe])}"

    return jsonify({
        'success': True,
        'data': {
            'score': score,
            'matched_count': len(matched_unis),
            'recommendation': ai_response
        }
    })

# ==================== 其他 API ====================

@app.route('/api/score-lines')
def api_score_lines():
    """获取分数线数据"""
    data = load_json_data('score_lines.json')
    if data:
        return jsonify({'success': True, 'data': data})
    return jsonify({'success': False, 'message': '数据加载失败'}), 500

@app.route('/api/universities')
def api_universities():
    """获取院校数据"""
    data = load_json_data('universities.json')
    if data:
        universities = data.get('universities', [])
        level = request.args.get('level', '')
        location = request.args.get('location', '')
        if level:
            universities = [u for u in universities if level in u.get('level', '')]
        if location:
            universities = [u for u in universities if location in u.get('location', '')]
        return jsonify({'success': True, 'data': universities})
    return jsonify({'success': False, 'message': '数据加载失败'}), 500

@app.route('/api/university/<int:uni_id>')
def api_university_detail(uni_id):
    """获取院校详情"""
    for uni in get_universities():
        if uni.get('id') == uni_id:
            return jsonify({'success': True, 'data': uni})
    return jsonify({'success': False, 'message': '院校不存在'}), 404

@app.route('/api/major/<int:major_id>')
def api_major_detail(major_id):
    """获取专业详情"""
    for major in get_majors():
        if major.get('id') == major_id:
            return jsonify({'success': True, 'data': major})
    return jsonify({'success': False, 'message': '专业不存在'}), 404

@app.route('/api/statistics')
def api_statistics():
    """获取统计数据"""
    return jsonify({
        'success': True,
        'data': {
            'universities': len(get_universities()),
            'majors': len(get_majors()),
            'high_schools': len(get_high_schools()),
            'score_years': 6
        }
    })

@app.route('/api/news')
def api_news():
    """获取新闻资讯数据"""
    data = get_news()
    if data:
        return jsonify({
            'success': True,
            'data': {
                'news': data.get('news', []),
                'categories': data.get('categories', []),
                'sources': data.get('sources', []),
                'update_time': data.get('update_time', '')
            }
        })
    return jsonify({'success': False, 'message': '数据加载失败'}), 500

@app.route('/api/data-sources')
def api_data_sources():
    """获取所有数据来源信息"""
    sources = {
        'universities': {
            'source': '官方公布',
            'source_detail': '各高校招生官网、阳光高考网',
            'update_time': '2026-03-17',
            'reliability': '高'
        },
        'score_lines': {
            'source': '官方公布',
            'source_detail': '上海市教育考试院',
            'update_time': '2025-06-23',
            'reliability': '高'
        },
        'majors': {
            'source': '网络公开',
            'source_detail': '教育部专业目录、各高校官网',
            'update_time': '2026-01-15',
            'reliability': '中'
        },
        'high_schools': {
            'source': '网络公开',
            'source_detail': '上海市教委、各学校官网',
            'update_time': '2025-09-01',
            'reliability': '中'
        },
        'news': {
            'source': '官方公布',
            'source_detail': '上海招考热线、阳光高考网等',
            'update_time': '2026-03-17',
            'reliability': '高'
        }
    }
    return jsonify({
        'success': True,
        'data': sources
    })

if __name__ == '__main__':
    print("=" * 50)
    print("上海高考志愿填报辅助系统")
    print("=" * 50)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=80)
