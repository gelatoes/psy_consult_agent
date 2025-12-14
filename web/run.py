import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash

# --- App Configuration ---
# 明确指定模板文件夹的路径，避免因运行路径问题导致 TemplateNotFound
app = Flask(__name__, template_folder='templates')
# 用于保护 Flask session 的密钥，生产环境中应使用更复杂的随机字符串
app.config['SECRET_KEY'] = 'a_very_secret_key_for_session_management_and_debugging'
# 你的 FastAPI 后端地址
API_BASE_URL = "http://127.0.0.1:8000"


# --- Helper Functions ---

def _get_auth_headers():
    """从 session 中获取认证 token 并构造成 HTTP 请求头"""
    if 'access_token' not in session:
        print("DEBUG: _get_auth_headers() -> No access_token in session!")
        return None
    token = session["access_token"]
    # print(f"DEBUG: _get_auth_headers() -> Found token: {token[:15]}...") # 打印部分token以确认存在
    return {'Authorization': f'Bearer {token}'}

def _get_current_user_from_api():
    """
    从 API 获取当前登录的用户信息。
    为了提高效率，会将用户信息缓存到 session 中。
    """
    if 'user' in session and session['user'] is not None:
        return session.get('user')
        
    headers = _get_auth_headers()
    if not headers:
        return None
        
    try:
        profile_url = f"{API_BASE_URL}/auth/profile"
        profile_res = requests.get(profile_url, headers=headers, timeout=180)
        
        if profile_res.status_code == 200:
            user_data = profile_res.json()
            session['user'] = user_data
            return user_data
        else:
            session.pop('access_token', None)
            session.pop('user', None)
            return None
            
    except requests.RequestException:
        return None

def _clear_session():
    """登出或会话无效时，清理所有 session 数据"""
    session.pop('access_token', None)
    session.pop('user', None)


@app.route('/')
def home():
    """应用首页，现在直接重定向到注册页面以简化流程"""
    # 原本这里显示 home.html，现在改为直接跳转到注册
    return redirect(url_for('register'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录页面及逻辑处理"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        payload = {"username": username, "password": password}

        try:
            response = requests.post(f"{API_BASE_URL}/auth/login", json=payload, timeout=180)

            if response.status_code == 200:
                _clear_session()
                token_data = response.json()
                session['access_token'] = token_data['access_token']
                flash('登录成功！', 'success')
                return redirect(url_for('profile'))
            else:
                error_detail = response.json().get('detail', '用户名或密码错误')
                flash(error_detail, 'error')
        except requests.RequestException:
            flash("无法连接到认证服务，请检查后端是否开启。", "error")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册页面及逻辑处理"""
    if request.method == 'POST':
        # 从表单获取注册所需信息
        grade = request.form.get('grade')
        gender = request.form.get('gender')
        university = request.form.get('university')
        major = request.form.get('major')

        username = grade+gender+university+major
        email = username + "@example.com"

        register_payload = {
            "username": username,
            "email": email,
            "password": username,
            "grade": request.form.get('grade'),
            "gender": request.form.get('gender'),
            "university": request.form.get('university'),
            "major": request.form.get('major')
        }
        
        try:
            # --- 步骤 1: 提交注册信息 ---
            register_response = requests.post(f"{API_BASE_URL}/auth/register", json=register_payload, timeout=180)

            # --- 步骤 2: 检查注册是否成功 ---
            if register_response.status_code == 201:
                # 注册成功！现在开始执行自动登录和开始咨询的流程

                # --- 步骤 3: 使用刚刚注册的凭据自动登录 ---
                try:
                    login_payload = {"username": username, "password": username}
                    login_response = requests.post(f"{API_BASE_URL}/auth/login", json=login_payload, timeout=180)

                    if login_response.status_code == 200:
                        # 自动登录成功，将会话信息存入 session
                        _clear_session() # 清理旧会话以防万一
                        token_data = login_response.json()
                        session['access_token'] = token_data['access_token']
                        
                        # --- 步骤 4: 获取当前用户信息 (需要用 token) ---
                        user = _get_current_user_from_api()
                        if not user:
                            # 这是一个理论上不应发生的边缘情况
                            flash('注册成功，但获取用户信息时出错，请手动登录。', 'error')
                            return redirect(url_for('login'))

                        # --- 步骤 5: 自动开始一个新的咨询会话 ---
                        start_payload = {"user_id": user['id']}
                        headers = _get_auth_headers()
                        start_response = requests.post(
                            f"{API_BASE_URL}/consultation/start", 
                            headers=headers, 
                            json=start_payload, 
                            timeout=180
                        )
                        
                        if start_response.status_code == 200:
                            # 成功开始咨询，直接跳转到聊天页面
                            consultation_data = start_response.json()
                            flash('注册成功！已为您自动开始新的咨询。', 'success')
                            return redirect(url_for('chat_session', session_id=consultation_data['session_id']))
                        else:
                            # 开始咨询失败，但用户已登录，跳转到个人主页
                            flash('注册并登录成功，但开始新咨询失败。请从个人主页手动开始。', 'warning')
                            return redirect(url_for('profile'))
                    else:
                        # 自动登录失败
                        flash('注册成功，但自动登录失败，请您手动登录。', 'warning')
                        return redirect(url_for('login'))

                except requests.RequestException:
                    flash("注册成功，但后续服务连接失败，请手动登录。", "error")
                    return redirect(url_for('login'))
            
            else: # 注册失败的逻辑保持不变
                error_detail = register_response.json().get('detail', '注册失败，请检查输入。')
                flash(error_detail, 'error')

        except requests.RequestException:
             flash("无法连接到注册服务，请检查后端是否开启。", "error")
             
    return render_template('register.html')

@app.route('/logout')
def logout():
    """用户登出"""
    _clear_session()
    flash('您已成功登出。', 'info')
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    """个人资料页面"""
    user = _get_current_user_from_api()
    if not user:
        flash('您的会话已过期或无效，请重新登录。', 'warning')
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)


# --- Consultation Routes ---

@app.route('/consultation/start', methods=['POST'])
def start_consultation():
    """处理“开始新咨询”按钮的请求"""
    print("\n[DEBUG] In start_consultation()")
    user = _get_current_user_from_api()
    if not user:
        flash('会话已过期，请重新登录。', 'warning')
        return redirect(url_for('login'))

    headers = _get_auth_headers()
    payload = {"user_id": user['id']}
    
    try:
        api_url = f"{API_BASE_URL}/consultation/start"
        print(f"  -> Calling API: POST {api_url}")
        print(f"  -> With Headers: {headers}")
        print(f"  -> With Payload: {payload}")
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        
        print(f"  <- API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  <- API Response JSON: {data}")
            flash('新的咨询已开始！', 'success')
            return redirect(url_for('chat_session', session_id=data['session_id']))
        else:
            try:
                print(f"  <- API Error Response: {response.json()}")
            except requests.exceptions.JSONDecodeError:
                print(f"  <- API Error Response (not JSON): {response.text}")
            
            flash(f"开始咨询失败: {response.json().get('detail', '未知错误')}", 'error')
            return redirect(url_for('profile'))

    except requests.RequestException as e:
        print(f"  <- Request Exception: {e}")
        flash("无法连接到咨询服务。", "error")
        return redirect(url_for('profile'))

@app.route('/consultation/history')
def consultation_history():
    """显示用户的咨询历史列表"""
    # ... (此部分暂时不修改，因为不是当前问题的焦点) ...
    user = _get_current_user_from_api()
    if not user:
        flash('请先登录以查看历史记录。', 'warning')
        return redirect(url_for('login'))
    
    try:
        response = requests.get(f"{API_BASE_URL}/consultation/{user['id']}/history", headers=_get_auth_headers(), timeout=180)
        if response.status_code == 200:
            sessions = response.json()
            
            return render_template('history.html', sessions=sessions)
        else:
            flash('无法获取历史会话。', 'error')
            return redirect(url_for('profile'))
    except requests.RequestException:
        flash("无法连接到咨询服务。", "error")
        return redirect(url_for('profile'))

# 在 run.py 中

@app.route('/consultation/<session_id>', methods=['GET', 'POST'])
def chat_session(session_id):
    user = _get_current_user_from_api()
    if not user:
        flash('请先登录以继续咨询。', 'warning')
        return redirect(url_for('login'))
        
    headers = _get_auth_headers()
    
    try:
        if request.method == 'POST':
            form_type = request.form.get('form_type')

            if form_type == 'survey':
                # --- GHQ 问卷处理逻辑 ---
                ghq_questions = [
                    "大致来说每样事情都颇开心",
                    "你是不是做事情都能够集中精神",
                    "是不是很满意自己做事情的方式",
                    "最近是否忙碌及充分利用时间",
                    "处理日常事务是不是和别人一样好",
                    "是不是觉得自己在很多事情上都能帮手或提供一些意见",
                    "觉得很不开心及闷闷不乐",
                    "能够开心地过你平日正常的生活",
                    "是不是容易同人相处",
                    "觉得自己的将来还有希望",
                    "觉得做人没有什么意思",
                    "对自己失去信心",
                    "觉得人生完全没有希望",
                    "觉得自己是个无用的人",
                    "整天觉得人生好似战场一样",
                    "是不是因为担心而睡不着",
                    "是不是心情烦燥睡得不好",
                    "整天觉得心神不安与紧张",
                    "是不是觉得整天有精神压力",
                    "因为神经太过紧张觉得有时什么事情都做不到",
                    "我愿意经常使用这个系统",
                    "我认为这个系统没必要这么复杂",
                    "我认为这个系统容易使用",
                    "我需要技术人员的支持才能使用这个系统",
                    "我认为这个系统中的不同功能被较好地整合在了一起",
                    "我认为这个系统太不一致了",
                    "我认为大部分人能很快学会使用这个系统",
                    "我认为这个系统使用起来非常笨拙",
                    "对于使用这个系统，我感到很自信",
                    "在我能够使用这个系统之前，我需要学习很多东西"
                ]
                answers = []
                for i in range(len(ghq_questions)):
                    question = ghq_questions[i]
                    # 从表单中获取 q0, q1, ... q19 的答案
                    answer = request.form.get(f'q{i}')
                    if answer:
                        answers.append(f"{i+1}. {question}\n回答: {answer}")
                    else:
                        # 如果有某个问题没回答，给出提示并中止
                        flash(f'请完成所有问卷题目。问题 {i+1} 未回答。', 'warning')
                        return redirect(url_for('chat_session', session_id=session_id))
                
                # 将所有答案拼接成一个长字符串
                formatted_survey = "\n\n".join(answers)
                
                payload = {"user_survey": formatted_survey}
                api_url = f"{API_BASE_URL}/consultation/{session_id}/survey"

            else: # 普通消息
                user_input = request.form.get('user_input')
                if not user_input:
                    flash('消息内容不能为空。', 'warning')
                    return redirect(url_for('chat_session', session_id=session_id))
                
                payload = {"user_input": user_input}
                api_url = f"{API_BASE_URL}/consultation/{session_id}/message"

            # 发送请求到后端
            response = requests.post(api_url, headers=headers, json=payload, timeout=180)
            
            if response.status_code != 200:
                flash(f"提交失败: {response.json().get('detail', '请稍后重试')}", 'error')
            
            return redirect(url_for('chat_session', session_id=session_id))

        # --- GET 请求逻辑保持不变 ---
        session_url = f"{API_BASE_URL}/consultation/{session_id}"
        get_response = requests.get(session_url, headers=headers, timeout=180)
        if get_response.status_code == 200:
            session_data = get_response.json()
            if session_data.get('user_id') != user['id']:
                flash('您无权访问此会话。', 'error')
                return redirect(url_for('profile'))
            return render_template('chat.html', session_data=session_data)
        else:
            error_detail = "未知错误"
            try:
                error_detail = get_response.json().get('detail', error_detail)
            except: pass
            flash(f"无法加载会话 (状态码: {get_response.status_code}): {error_detail}", 'error')
            return redirect(url_for('profile'))

    except requests.RequestException as e:
        flash(f"无法连接到咨询服务: {e}", "error")
        return redirect(url_for('profile'))

# --- Main Application Runner ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)