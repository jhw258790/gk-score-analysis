from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import json
import hashlib
import random
import requests
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey12345'

DATA_DIR = 'data'
STATIC_DIR = 'static'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
RAW_DATA_FILE = os.path.join(DATA_DIR, 'raw_data.json')
CLEANED_DATA_FILE = os.path.join(DATA_DIR, 'cleaned_data.json')
ANALYSIS_FILE = os.path.join(DATA_DIR, 'analysis.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

BANNED_WORDS = ['作弊', '泄题', '代考', '贿赂', '虚假', '伪造']

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def generate_mock_data():
    majors = ['计算机科学与技术', '电子信息工程', '金融学', '临床医学', '土木工程', '会计学', '机械工程', '经济学', '法学', '教育学']
    universities = ['北京大学', '清华大学', '复旦大学', '上海交通大学', '浙江大学', '南京大学', '中国人民大学', '武汉大学', '华中科技大学', '中山大学']
    
    data = []
    for year in [2023, 2024, 2025]:
        for i in range(500):
            score = random.randint(300, 750)
            if score >= 480:
                batch = '本科'
            elif score >= 350:
                batch = '专科'
            else:
                batch = '未上线'
            
            university = None
            if score >= 600:
                university = random.choice(universities)
            
            data.append({
                'id': f'{year}_{i+1}',
                'year': year,
                'score': score,
                'batch': batch,
                'major': random.choice(majors),
                'university': university,
                'region': '内蒙古自治区',
                'gender': random.choice(['男', '女']),
                'ethnic': random.choice(['汉族', '蒙古族', '回族', '满族', '其他'])
            })
    return data

def fetch_real_data():
    try:
        response = requests.get('https://api.example.com/gaokao/neimenggu', timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result and 'data' in result:
                return result['data']
    except:
        pass
    return None

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    raw_count = 0
    cleaned_count = 0
    
    if os.path.exists(RAW_DATA_FILE):
        with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
            raw_count = len(json.load(f))
    
    if os.path.exists(CLEANED_DATA_FILE):
        with open(CLEANED_DATA_FILE, 'r', encoding='utf-8') as f:
            cleaned_count = len(json.load(f))
    
    return render_template('index.html', 
                           username=session['username'],
                           raw_count=raw_count,
                           cleaned_count=cleaned_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_users()
        if username in users and users[username] == hash_password(password):
            session['username'] = username
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        flash('用户名或密码错误！', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('两次输入的密码不一致！', 'danger')
            return redirect(url_for('register'))
        
        users = load_users()
        if username in users:
            flash('用户名已存在！', 'danger')
            return redirect(url_for('register'))
        
        users[username] = hash_password(password)
        save_users(users)
        flash('注册成功，请登录！', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('已退出登录！', 'info')
    return redirect(url_for('login'))

@app.route('/collect')
def collect():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    real_data = fetch_real_data()
    if real_data:
        data = real_data
        source = '真实数据'
    else:
        data = generate_mock_data()
        source = '模拟数据（接口获取失败）'
    
    with open(RAW_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return render_template('collect.html', data=data, source=source)

@app.route('/clean')
def clean():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if not os.path.exists(RAW_DATA_FILE):
        flash('请先进行数据采集！', 'warning')
        return redirect(url_for('collect'))
    
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    original_count = len(df)
    
    df = df.drop_duplicates()
    
    df = df.dropna(subset=['score', 'batch', 'major'])
    
    df = df[(df['score'] >= 0) & (df['score'] <= 750)]
    
    for word in BANNED_WORDS:
        df = df[~df['major'].astype(str).str.contains(word)]
        df = df[~df['university'].astype(str).str.contains(word)]
    
    cleaned_count = len(df)
    
    cleaned_data = df.to_dict('records')
    
    if cleaned_count == 0:
        flash('数据清洗后无数据，将跳过清洗步骤！', 'warning')
    else:
        with open(CLEANED_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    return render_template('clean.html', 
                           original_count=original_count,
                           cleaned_count=cleaned_count,
                           data=cleaned_data)

@app.route('/analyze')
def analyze():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    data_file = CLEANED_DATA_FILE if os.path.exists(CLEANED_DATA_FILE) else RAW_DATA_FILE
    
    if not os.path.exists(data_file):
        flash('请先进行数据采集！', 'warning')
        return redirect(url_for('collect'))
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    score_distribution = {
        '0-350': len(df[(df['score'] >= 0) & (df['score'] < 350)]),
        '350-450': len(df[(df['score'] >= 350) & (df['score'] < 450)]),
        '450-550': len(df[(df['score'] >= 450) & (df['score'] < 550)]),
        '550-650': len(df[(df['score'] >= 550) & (df['score'] < 650)]),
        '650-750': len(df[(df['score'] >= 650) & (df['score'] <= 750)])
    }
    
    batch_stats = df['batch'].value_counts().to_dict()
    total_students = len(df)
    undergraduate_rate = round((batch_stats.get('本科', 0) / total_students) * 100, 2) if total_students > 0 else 0
    
    uni_data = df[df['university'].notna()]
    university_min_scores = uni_data.groupby('university')['score'].min().sort_values(ascending=False).head(10).to_dict()
    
    major_counts = df['major'].value_counts().head(10).to_dict()
    
    yearly_stats = {}
    for year in [2023, 2024, 2025]:
        year_df = df[df['year'] == year]
        yearly_stats[year] = {
            'total': len(year_df),
            'avg_score': round(year_df['score'].mean(), 2) if len(year_df) > 0 else 0,
            'undergraduate': len(year_df[year_df['batch'] == '本科']),
            'undergraduate_rate': round((len(year_df[year_df['batch'] == '本科']) / len(year_df)) * 100, 2) if len(year_df) > 0 else 0
        }
    
    analysis = {
        'score_distribution': score_distribution,
        'batch_stats': batch_stats,
        'undergraduate_rate': undergraduate_rate,
        'university_min_scores': university_min_scores,
        'major_counts': major_counts,
        'yearly_stats': yearly_stats,
        'total_students': total_students
    }
    
    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    return render_template('analyze.html', analysis=analysis)

@app.route('/visualize')
def visualize():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if not os.path.exists(ANALYSIS_FILE):
        flash('请先进行数据分析！', 'warning')
        return redirect(url_for('analyze'))
    
    with open(ANALYSIS_FILE, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    return render_template('visualize.html', analysis=analysis)

# ============================================================
# 真实数据 SQL 分析：读取 MySQL（gaokao.nm_gk_score）后渲染
# ============================================================
MYSQL_CONF = dict(host='127.0.0.1', port=3306, user='root', password='258790',
                  database='gaokao', charset='utf8mb4',
                  cursorclass=pymysql.cursors.DictCursor)

SQL_SCALE = """
    select year, category, max(cumulative) as total_exam, min(score) as min_score,
           max(score) as max_score, count(*) as bands
    from nm_gk_score group by year, category order by year, category
"""
SQL_600 = """
    select year, category,
           sum(case when score >= 600 then band_count else 0 end) as above_600,
           max(cumulative) as total_exam,
           round(100.0 * sum(case when score >= 600 then band_count else 0 end)
                 / max(cumulative), 2) as pct
    from nm_gk_score
    where category in ('文科','理科','历史类','物理类')
    group by year, category order by year, category
"""
SQL_DIST = """
    select floor(score / 50) * 50 as band_start, sum(band_count) as students
    from nm_gk_score where year = 2025 and category = '物理类'
    group by band_start order by band_start
"""
SQL_HOT = """
    select year, category, score, band_count from (
        select year, category, score, band_count,
               rank() over (partition by year, category order by band_count desc) as rk
        from nm_gk_score
    ) t where rk = 1 order by year, category
"""


@app.route('/gk')
def gk_analysis():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        conn = pymysql.connect(**MYSQL_CONF)
    except Exception as e:  # noqa: BLE001
        flash('MySQL 连接失败：%s（请先执行 db/load_gk.sql 导入数据）' % e, 'danger')
        return redirect(url_for('index'))

    try:
        with conn.cursor() as cur:
            def q(sql):
                cur.execute(sql)
                return cur.fetchall()
            scale = q(SQL_SCALE)
            ratio600 = q(SQL_600)
            dist = q(SQL_DIST)
            hot = q(SQL_HOT)
            cur.execute("select count(*) as n, min(year) as y1, max(year) as y2 from nm_gk_score")
            summary = cur.fetchone()
    finally:
        conn.close()

    return render_template('gk.html', scale=scale, ratio600=ratio600,
                           dist=dist, hot=hot, summary=summary)


if __name__ == '__main__':
    app.run(debug=True)