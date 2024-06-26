from flask import Flask,Blueprint, render_template, request, redirect, url_for, send_from_directory
from database import execute_query, fetch_data
from datetime import date
import secrets
import subprocess
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from celery import Celery

freecad_path = "/schody3d/FreeCadapp/freecad_appimage/squashfs-root/usr/bin/freecadcmd"
views = Blueprint(__name__, "views")


def generate_session_id():
    while True:
        first_digit = secrets.randbelow(9) + 1
        rest_digits = ''.join(str(secrets.randbelow(10)) for _ in range(15))
        session_id = str(first_digit) + rest_digits
        existing_id = fetch_data("SELECT session_id FROM Stairs WHERE session_id = ?", (session_id,))
        if not existing_id:
            return session_id

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)

celery = make_celery(app)

@celery.task
def generate_project(session_id, length, width, height, step_height, num_steps):
    try:
        # Logika uruchamiania skryptu FreeCAD
        result = subprocess.run([freecad_path, '-c', 'FreeCadScripts/Schody_Proste.FCMacro', session_id, str(length), str(width), str(height), str(step_height), str(num_steps)], check=True)
        print("Project generated:", session_id)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        raise e
    return f"Project {session_id} generated successfully."

@views.route("/")
def home():
    return render_template("index.html")

@views.route("/kontakt/")
def contact():
    return render_template("contact.html")

@views.route("/admin/")
def admin():
    current_sort_by = request.args.get('sort', 'session_id')
    current_order = request.args.get('order', 'asc')
    filter_type = request.args.get('type')
    query = "SELECT * FROM Stairs"
    conditions = []
    if filter_type:
        conditions.append(f"Type = '{filter_type}'")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    if current_sort_by:
        previous_sort_by = request.args.get('prev_sort')
        new_order = 'desc' if current_order == 'asc' and previous_sort_by == current_sort_by else 'asc'
        query += f" ORDER BY {current_sort_by} {new_order}"
    stairs = fetch_data(query)
    return render_template("admin.html", stairs=stairs, sort_by=current_sort_by, order=new_order, prev_sort=current_sort_by)

@views.route('/delete/<session_id>', methods=['POST'])
def delete_stairs(session_id):

    execute_query("DELETE FROM Stairs WHERE session_id=?", (session_id,))

    try:
        os.remove(os.path.join(FREECAD_PROJECTS_DIR, f"{session_id}.html"))
        os.remove(os.path.join(FREECAD_PROJECTS_DIR, f"{session_id}.FCStd"))
    except FileNotFoundError:
        logging.error(f"Files for session_id {session_id} not found.")
    except Exception as e:
        logging.error(f"Error deleting files for session_id {session_id}: {str(e)}")

    return redirect(url_for("views.admin"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FREECAD_PROJECTS_DIR = os.path.join(BASE_DIR, 'FreeCadProjects')

@views.route('/projects/<session_id>')
def serve_project(session_id):
    file_path = f"{session_id}.html"
    if os.path.exists(os.path.join(FREECAD_PROJECTS_DIR, file_path)):
        return send_from_directory(FREECAD_PROJECTS_DIR, file_path)
    else:
        return "File not found", 404


@views.route('/create/', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        length = request.form.get("Długość stopnia (mm)")
        width = request.form.get("Szerokość stopnia (mm)")
        height = request.form.get("Wysokość stopnia (mm)")
        step_height = request.form.get("Wysokość między stopniami (mm)")
        num_steps = request.form.get("Ilość stopni")
        try:
            length = float(length)
            width = float(width)
            height = float(height)
            step_height = float(step_height)
            num_steps = int(num_steps)
        except ValueError:
            return render_template('error.html', error_message="Invalid input. Please enter numeric values.")
        session_id = generate_session_id()
        execute_query(
            "INSERT INTO Stairs (session_id, length, width, height, step_height, number_of_steps, Type, generated_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, length, width, height, step_height, num_steps, "proste", date.today()))

        generate_project.delay(session_id, length, width, height, step_height, num_steps)

        return redirect(url_for('views.result', session_id=session_id))
    return render_template('create.html')

@views.route('/result/<session_id>')
def result(session_id):
    return render_template('result.html', session_id=session_id)

@views.route('/download/<session_id>')
def download_project(session_id):
    """Allow the user to download the HTML file for a given session."""
    file_path = f"{session_id}.html"
    if os.path.exists(os.path.join(FREECAD_PROJECTS_DIR, file_path)):
        return send_from_directory(FREECAD_PROJECTS_DIR, file_path, as_attachment=True)
    else:
        return "File not found", 404


def clean_old_files():
    now = datetime.now()
    cutoff = now - timedelta(days=2)

    for filename in os.listdir(FREECAD_PROJECTS_DIR):
        file_path = os.path.join(FREECAD_PROJECTS_DIR, filename)
        file_stat = os.stat(file_path)
        file_creation_time = datetime.fromtimestamp(file_stat.st_ctime)
        if file_creation_time < cutoff:
            try:
                # Usuwanie pliku
                os.remove(file_path)
                print(f"Removed {filename}")

                # Usuwanie rekordu z bazy danych
                session_id = filename.split('.')[0]  # Zakładamy, że nazwa pliku to session_id.html lub session_id.FCStd
                execute_query("DELETE FROM Stairs WHERE session_id=?", (session_id,))
                print(f"Deleted record for session_id {session_id}")

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

scheduler = BackgroundScheduler()
scheduler.start()

scheduler.add_job(
    clean_old_files,
    trigger=CronTrigger(hour=2, minute=0)
)
@views.route('/check_file/<session_id>')
def check_file(session_id):
    file_path = os.path.join(FREECAD_PROJECTS_DIR, f"{session_id}.html")
    if os.path.exists(file_path):
        return {"exists": True}, 200
    else:
        return {"exists": False}, 404

