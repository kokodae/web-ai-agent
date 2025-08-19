from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import PyPDF2  
import pandas as pd  
from openai import OpenAI

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# TODO: Составить план реализации (какие инструменты) не для теста а для реального пользования.
#       ИБ.
#       Подключить агента к телеграм-боту. Сохранение всего диалога внутри кабинета для каждого чата.
#       Выход - документ.
#       

client = OpenAI(
    api_key="API_KEY"
)

# Функция для чтения пользователей из файла
def read_users():
    users = {}
    if not os.path.exists('users.txt'):
        return users
    with open('users.txt', 'r') as file:
        for line in file:
            username, password = line.strip().split(':')
            users[username] = password
    return users

# Функция для записи нового пользователя в файл
def write_user(username, password):
    with open('users.txt', 'a') as file:
        file.write(f'{username}:{password}\n')

# Функция для создания папки пользователя
def create_user_folder(username):
    user_folder = os.path.join('user_data', username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

# Функция для сохранения данных агента в файлы
def save_agent_to_files(username, agent_name, role, responsibilities, knowledge_file):
    user_folder = os.path.join('user_data', username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    # Создаем папку для агента
    agent_folder = os.path.join(user_folder, agent_name)
    if not os.path.exists(agent_folder):
        os.makedirs(agent_folder)

    # Сохраняем данные агента в файлы
    with open(os.path.join(agent_folder, 'agent_name.txt'), 'w', encoding='utf-8') as file:
        file.write(agent_name)

    with open(os.path.join(agent_folder, 'role.txt'), 'w', encoding='utf-8') as file:
        file.write(role)

    with open(os.path.join(agent_folder, 'responsibilities.txt'), 'w', encoding='utf-8') as file:
        file.write(responsibilities)

    # Сохраняем загруженный файл
    if knowledge_file:
        file_path = os.path.join(agent_folder, knowledge_file.filename)
        knowledge_file.save(file_path)

# Функция для чтения данных агента из файлов
def read_agent_from_files(username, agent_name):
    agent_folder = os.path.join('user_data', username, agent_name)
    if not os.path.exists(agent_folder):
        return None

    agent_data = {}
    try:
        with open(os.path.join(agent_folder, 'agent_name.txt'), 'r', encoding='utf-8') as file:
            agent_data['agent_name'] = file.read().strip()

        with open(os.path.join(agent_folder, 'role.txt'), 'r', encoding='utf-8') as file:
            agent_data['role'] = file.read().strip()

        with open(os.path.join(agent_folder, 'responsibilities.txt'), 'r', encoding='utf-8') as file:
            agent_data['responsibilities'] = file.read().strip()

        # Ищем файл базы знаний
        for filename in os.listdir(agent_folder):
            if filename not in ['agent_name.txt', 'role.txt', 'responsibilities.txt', 'chat_history.txt']:
                agent_data['knowledge_file'] = os.path.join(agent_folder, filename)
                break
    except FileNotFoundError:
        return None

    return agent_data

# Функция для получения списка агентов пользователя
def get_user_agents(username):
    user_folder = os.path.join('user_data', username)
    if not os.path.exists(user_folder):
        return []

    agents = []
    for agent_name in os.listdir(user_folder):
        agent_folder = os.path.join(user_folder, agent_name)
        if os.path.isdir(agent_folder):
            agent_data = read_agent_from_files(username, agent_name)
            if agent_data:
                agents.append(agent_data)
    return agents

# Функция для чтения файла базы знаний
def read_knowledge_file(file_path):
    if not os.path.exists(file_path):
        return None

    if file_path.endswith('.txt'):
        # Чтение текстового файла
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    elif file_path.endswith('.pdf'):
        # Чтение PDF-файла
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text

    elif file_path.endswith('.xlsx'):
        # Чтение Excel-файла
        df = pd.read_excel(file_path)
        return df.to_string()

    else:
        return None

# Функция для сохранения истории чата
def save_chat_history(username, agent_name, user_message, agent_response):
    history_file = os.path.join('user_data', username, agent_name, 'chat_history.txt')
    with open(history_file, 'a', encoding='utf-8') as file:
        file.write(f"Пользователь: {user_message}\n")
        file.write(f"Агент: {agent_response}\n\n")

# Функция для чтения истории чата
def read_chat_history(username, agent_name):
    history_file = os.path.join('user_data', username, agent_name, 'chat_history.txt')
    if not os.path.exists(history_file):
        return []
    with open(history_file, 'r', encoding='utf-8') as file:
        return file.readlines()

# Главная страница
@app.route('/')
def home():
    return render_template('login.html')

# Авторизация
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    users = read_users()

    if username in users and users[username] == password:
        session['username'] = username
        flash('Вы успешно авторизовались!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Неверное имя пользователя или пароль', 'error')
        return redirect(url_for('home'))

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = read_users()

        if username in users:
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('register'))

        # Создаем папку для пользователя
        create_user_folder(username)

        # Сохраняем пользователя
        write_user(username, password)
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('home'))

    return render_template('register.html')

# Личный кабинет
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('home'))

    username = session['username']
    agents = get_user_agents(username)

    # Чтение истории чата, если агент существует
    chat_history = []
    if agents:
        chat_history = read_chat_history(username, agents[0]['agent_name'])

    return render_template('dashboard.html', username=username, agents=agents, chat_history=chat_history)

# Создание агента
@app.route('/create_agent', methods=['GET', 'POST'])
def create_agent():
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('home'))

    username = session['username']
    agents = get_user_agents(username)

    # Проверяем, есть ли у пользователя уже агент
    if agents:
        flash('У вас уже есть агент. Вы можете создать только одного агента.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        agent_name = request.form['agent_name']
        role = request.form['role']
        responsibilities = request.form['responsibilities']
        knowledge_file = request.files['knowledge_file']

        # Сохраняем агента в файлы
        save_agent_to_files(username, agent_name, role, responsibilities, knowledge_file)
        flash('Агент успешно создан!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_agent.html')

# Чат с агентом
@app.route('/chat_with_agent', methods=['POST'])
def chat_with_agent():
    if 'username' not in session:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('home'))

    username = session['username']
    agent_name = request.form['agent_name']
    user_message = request.form['message']

    # Получаем данные агента
    agent_data = read_agent_from_files(username, agent_name)
    if not agent_data:
        flash('Агент не найден', 'error')
        return redirect(url_for('dashboard'))

    # Читаем базу знаний из файла
    knowledge_text = ""
    if 'knowledge_file' in agent_data:
        knowledge_text = read_knowledge_file(agent_data['knowledge_file'])

    # Формируем промт для ChatGPT
    prompt = f"Ты {agent_data['role']}. Твои обязанности: {agent_data['responsibilities']}. "
    if knowledge_text:
        prompt += f"Вот твоя база знаний:\n{knowledge_text}\n"
    prompt += f"Ответь на вопрос: {user_message}"

    # Отправляем запрос к OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=150
    )

    # Сохраняем историю чата
    agent_response = response.choices[0].message.content
    save_chat_history(username, agent_name, user_message, agent_response)

    # Возвращаем ответ
    return render_template('dashboard.html', username=username, agents=get_user_agents(username),
                           chat_response=agent_response, selected_agent=agent_data,
                           chat_history=read_chat_history(username, agent_name))

# Запуск приложения
if __name__ == '__main__':
    app.run(debug=True)