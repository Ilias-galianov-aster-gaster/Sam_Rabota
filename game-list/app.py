from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'замените-на-свой-секретный-ключ'  # Обязательно смените!

def get_db():
    conn = sqlite3.connect('games.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def migrate_db():
    """Автоматическое добавление новых столбцов при обновлении."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor = conn.execute("PRAGMA table_info(games)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'user_id' not in columns:
        conn.execute('ALTER TABLE games ADD COLUMN user_id INTEGER')
        default_user = conn.execute('SELECT id FROM users LIMIT 1').fetchone()
        if not default_user:
            hashed = generate_password_hash('admin')
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('admin', hashed))
            conn.commit()
            default_user = conn.execute('SELECT id FROM users LIMIT 1').fetchone()
        user_id = default_user['id']
        conn.execute('UPDATE games SET user_id = ?', (user_id,))
        conn.commit()
        print("✅ Добавлена колонка user_id")

    if 'game_name' not in columns:
        conn.execute('ALTER TABLE games ADD COLUMN game_name TEXT')
    if 'game_link' not in columns:
        conn.execute('ALTER TABLE games ADD COLUMN game_link TEXT')
    if 'playthroughs' not in columns:
        conn.execute('ALTER TABLE games ADD COLUMN playthroughs INTEGER DEFAULT 0')

    conn.commit()
    conn.close()

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            game_name TEXT,
            game_link TEXT,
            achievements INTEGER DEFAULT 0,
            total_achievements INTEGER DEFAULT 0,
            hours REAL DEFAULT 0,
            goal TEXT,
            status TEXT,
            rebirths INTEGER DEFAULT 0,
            playthroughs INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    migrate_db()

def login_required():
    if 'user_id' not in session:
        flash('Пожалуйста, войдите в систему', 'warning')
        return redirect(url_for('login'))
    return None

@app.route('/')
def index():
    redir = login_required()
    if redir:
        return redir

    # Получаем параметры из запроса
    sort_by = request.args.get('sort', 'name')
    search_query = request.args.get('search', '').strip()

    user_id = session['user_id']
    conn = get_db()

    # Базовый запрос с фильтром по user_id
    base_query = 'SELECT * FROM games WHERE user_id = ?'
    params = [user_id]

    # Добавляем поиск по названию игры (регистронезависимо)
    if search_query:
        base_query += ' AND game_name LIKE ?'
        params.append(f'%{search_query}%')

    # Определяем сортировку
    order_clause = ''
    if sort_by == 'name':
        order_clause = 'ORDER BY username ASC'
    elif sort_by == 'time':
        order_clause = 'ORDER BY created_at DESC'
    elif sort_by == 'hours_asc':
        order_clause = 'ORDER BY hours ASC'
    elif sort_by == 'hours_desc':
        order_clause = 'ORDER BY hours DESC'
    elif sort_by == 'playthroughs_asc':
        order_clause = 'ORDER BY playthroughs ASC'
    else:
        order_clause = 'ORDER BY username ASC'  # fallback

    query = f'{base_query} {order_clause}'
    games = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('index.html', games=games, sort_by=sort_by, search_query=search_query)

@app.route('/add', methods=['POST'])
def add_game():
    redir = login_required()
    if redir:
        return redir

    user_id = session['user_id']
    username = request.form['username']
    game_name = request.form.get('game_name', '')
    game_link = request.form.get('game_link', '')
    achievements = int(request.form.get('achievements', 0))
    total_achievements = int(request.form.get('total_achievements', 0))
    hours = float(request.form.get('hours', 0.0))
    goal = request.form.get('goal', '')
    status = request.form.get('status', 'В процессе')
    rebirths = int(request.form.get('rebirths', 0))
    playthroughs = int(request.form.get('playthroughs', 0))

    conn = get_db()
    conn.execute('''
        INSERT INTO games (user_id, username, game_name, game_link, achievements, total_achievements,
                           hours, goal, status, rebirths, playthroughs)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, game_name, game_link, achievements, total_achievements,
          hours, goal, status, rebirths, playthroughs))
    conn.commit()
    conn.close()
    flash('Игра добавлена!', 'success')
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    redir = login_required()
    if redir:
        return redir

    user_id = session['user_id']
    conn = get_db()
    game = conn.execute('SELECT * FROM games WHERE id = ? AND user_id = ?', (id, user_id)).fetchone()
    if game is None:
        flash('Запись не найдена или доступ запрещён', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        game_name = request.form.get('game_name', '')
        game_link = request.form.get('game_link', '')
        achievements = int(request.form.get('achievements', 0))
        total_achievements = int(request.form.get('total_achievements', 0))
        hours = float(request.form.get('hours', 0.0))
        goal = request.form.get('goal', '')
        status = request.form.get('status', 'В процессе')
        rebirths = int(request.form.get('rebirths', 0))
        playthroughs = int(request.form.get('playthroughs', 0))

        conn.execute('''
            UPDATE games
            SET username = ?, game_name = ?, game_link = ?,
                achievements = ?, total_achievements = ?,
                hours = ?, goal = ?, status = ?, rebirths = ?, playthroughs = ?
            WHERE id = ? AND user_id = ?
        ''', (username, game_name, game_link, achievements, total_achievements,
              hours, goal, status, rebirths, playthroughs, id, user_id))
        conn.commit()
        conn.close()
        flash('Запись обновлена!', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', game=game)

@app.route('/delete/<int:id>')
def delete(id):
    redir = login_required()
    if redir:
        return redir

    user_id = session['user_id']
    conn = get_db()
    conn.execute('DELETE FROM games WHERE id = ? AND user_id = ?', (id, user_id))
    conn.commit()
    conn.close()
    flash('Запись удалена', 'info')
    return redirect(url_for('index'))

@app.route('/clear', methods=['POST'])
def clear_all():
    redir = login_required()
    if redir:
        return redir

    user_id = session['user_id']
    conn = get_db()
    # Удаляем все игры данного пользователя
    conn.execute('DELETE FROM games WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('Все игры удалены', 'info')
    return redirect(url_for('index'))
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        password_confirm = request.form['password_confirm']

        if not username or not password:
            flash('Заполните все поля', 'danger')
            return redirect(url_for('register'))
        if password != password_confirm:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))
        if len(password) < 4:
            flash('Пароль должен быть не короче 4 символов', 'danger')
            return redirect(url_for('register'))

        hashed = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed))
            conn.commit()
            flash('Регистрация успешна! Теперь войдите', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем уже существует', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)