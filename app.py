from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import os
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Конфигурация за email (опционално)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

mail = Mail(app)

UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

# Администраторски данни
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin777'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Създаване на папки ако не съществуват
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

def allowed_file(filename):
    """Проверява дали файлът е разрешен тип"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_icon(filename):
    """Връща подходящата икона за файла"""
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if extension == 'pdf':
        return 'fas fa-file-pdf text-danger'
    elif extension in ['doc', 'docx']:
        return 'fas fa-file-word text-primary'
    else:
        return 'fas fa-file'

def get_file_type_name(filename):
    """Връща името на типа файл"""
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if extension == 'pdf':
        return 'PDF'
    elif extension in ['doc', 'docx']:
        return 'Word'
    else:
        return 'Файл'

def is_admin():
    """Проверява дали потребителят е администратор"""
    return session.get('user_type') == 'admin'

@app.route('/')
def home():
    """Начална страница с избор на роля"""
    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Вход за администратори"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user_type'] = 'admin'
            flash('Успешен вход като администратор!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Грешно потребителско име или парола!', 'error')
    
    return render_template('admin_login.html')

@app.route('/user_access')
def user_access():
    """Директен достъп за потребители"""
    session['user_type'] = 'user'
    return redirect(url_for('user_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    """Табло за администратори"""
    if not is_admin():
        flash('Нямате права за достъп до тази страница!', 'error')
        return redirect(url_for('home'))
    
    # Проверяваме дали има файлове в upload папката
    all_files = []
    if os.path.exists(UPLOAD_FOLDER):
        for f in os.listdir(UPLOAD_FOLDER):
            if allowed_file(f):
                all_files.append({
                    'name': f,
                    'icon': get_file_icon(f),
                    'type': get_file_type_name(f)
                })
    return render_template('admin_dashboard.html', files=all_files)

@app.route('/user_dashboard')
def user_dashboard():
    """Табло за потребители"""
    # Проверяваме дали има файлове в upload папката
    all_files = []
    if os.path.exists(UPLOAD_FOLDER):
        for f in os.listdir(UPLOAD_FOLDER):
            if allowed_file(f):
                all_files.append({
                    'name': f,
                    'icon': get_file_icon(f),
                    'type': get_file_type_name(f)
                })
    return render_template('user_dashboard.html', files=all_files)

@app.route('/download/<filename>')
def download_file(filename):
    """Изтегляне на файл"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path) and allowed_file(filename):
            return send_file(file_path, as_attachment=True)
        else:
            flash('Файлът не е намерен!', 'error')
            return redirect(url_for('user_dashboard' if session.get('user_type') == 'user' else 'admin_dashboard'))
    except Exception as e:
        flash(f'Грешка при изтегляне: {str(e)}', 'error')
        return redirect(url_for('user_dashboard' if session.get('user_type') == 'user' else 'admin_dashboard'))

@app.route('/view/<filename>')
def view_file(filename):
    """Преглед на файл в браузъра"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path) and allowed_file(filename):
            # Само PDF файловете могат да се преглеждат директно в браузъра
            if filename.lower().endswith('.pdf'):
                return send_file(file_path, mimetype='application/pdf')
            else:
                # За Word файлове - директно изтегляне
                return send_file(file_path, as_attachment=True)
        else:
            flash('Файлът не е намерен!', 'error')
            return redirect(url_for('user_dashboard' if session.get('user_type') == 'user' else 'admin_dashboard'))
    except Exception as e:
        flash(f'Грешка при преглед: {str(e)}', 'error')
        return redirect(url_for('user_dashboard' if session.get('user_type') == 'user' else 'admin_dashboard'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Качване на нов файл - само за администратори"""
    if not is_admin():
        flash('Нямате права за качване на файлове!', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Проверяваме дали има файл в заявката
        if 'file' not in request.files:
            flash('Не е избран файл!', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Проверяваме дали е избран файл
        if file.filename == '':
            flash('Не е избран файл!', 'error')
            return redirect(request.url)
        
        # Проверяваме дали файлът е разрешен тип
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(file_path)
                file_type = get_file_type_name(filename)
                flash(f'{file_type} файлът {filename} е качен успешно!', 'success')
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                flash(f'Грешка при качване: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Разрешени са само PDF и Word файлове!', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    """Изтриване на файл - само за администратори"""
    if not is_admin():
        flash('Нямате права за изтриване на файлове!', 'error')
        return redirect(url_for('home'))
    
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path) and allowed_file(filename):
            os.remove(file_path)
            file_type = get_file_type_name(filename)
            flash(f'{file_type} файлът {filename} е изтрит успешно!', 'success')
        else:
            flash('Файлът не е намерен!', 'error')
    except Exception as e:
        flash(f'Грешка при изтриване: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    """Изход от системата"""
    session.clear()
    flash('Успешно излязохте от системата!', 'success')
    return redirect(url_for('home'))

# Export за Vercel
vercel_app = app

if __name__ == '__main__':
    app.run(debug=True)