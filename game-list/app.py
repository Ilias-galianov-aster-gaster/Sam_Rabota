from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('games.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    # Создание таблицы, если её нет
    conn.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            game_name TEXT,                     -- новое поле
            game_link TEXT,                     -- новое поле
            achievements INTEGER DEFAULT 0,
            total_achievements INTEGER DEFAULT 0,
            hours REAL DEFAULT 0,
            goal TEXT,
            status TEXT,
            rebirths INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Проверяем наличие новых столбцов и добавляем при необходимости
    cursor = conn.execute("PRAGMA table_info(games)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'game_name' not in columns:
        conn.execute('ALTER TABLE games ADD COLUMN game_name TEXT')
    if 'game_link' not in columns:
        conn.execute('ALTER TABLE games ADD COLUMN game_link TEXT')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    sort_by = request.args.get('sort', 'name')

    if request.method == 'POST':
        username = request.form['username']
        game_name = request.form.get('game_name', '')
        game_link = request.form.get('game_link', '')
        achievements = int(request.form.get('achievements', 0))
        total_achievements = int(request.form.get('total_achievements', 0))
        hours = float(request.form.get('hours', 0.0))
        goal = request.form.get('goal', '')
        status = request.form.get('status', '')
        rebirths = int(request.form.get('rebirths', 0))

        conn = get_db()
        conn.execute('''
            INSERT INTO games (username, game_name, game_link, achievements, total_achievements, hours, goal, status, rebirths)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, game_name, game_link, achievements, total_achievements, hours, goal, status, rebirths))
        conn.commit()
        conn.close()
        return redirect(url_for('index', sort=sort_by))

    conn = get_db()
    if sort_by == 'time':
        query = 'SELECT * FROM games ORDER BY created_at DESC'
    else:
        query = 'SELECT * FROM games ORDER BY username ASC'
    games = conn.execute(query).fetchall()
    conn.close()
    return render_template('index.html', games=games, sort_by=sort_by)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    conn = get_db()
    if request.method == 'POST':
        # Получаем обновлённые данные
        username = request.form['username']
        game_name = request.form.get('game_name', '')
        game_link = request.form.get('game_link', '')
        achievements = int(request.form.get('achievements', 0))
        total_achievements = int(request.form.get('total_achievements', 0))
        hours = float(request.form.get('hours', 0.0))
        goal = request.form.get('goal', '')
        status = request.form.get('status', '')
        rebirths = int(request.form.get('rebirths', 0))

        conn.execute('''
            UPDATE games
            SET username = ?, game_name = ?, game_link = ?,
                achievements = ?, total_achievements = ?,
                hours = ?, goal = ?, status = ?, rebirths = ?
            WHERE id = ?
        ''', (username, game_name, game_link, achievements, total_achievements,
              hours, goal, status, rebirths, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    # GET — показываем форму с текущими данными
    game = conn.execute('SELECT * FROM games WHERE id = ?', (id,)).fetchone()
    conn.close()
    if game is None:
        return redirect(url_for('index'))  # если записи нет
    return render_template('edit.html', game=game)

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM games WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

init_db()

if __name__ == '__main__':
    app.run(debug=True)