from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory
from database import execute_query, fetch_data
from datetime import date
import secrets
import subprocess
import os
import logging

freecad_path = "/schody3d/FreeCadapp/freecad_appimage/squashfs-root/usr/bin/freecadcmd"
views = Blueprint(__name__, "views")

def generate_session_id():
    return ''.join(str(secrets.randbelow(10)) for _ in range(16))

@views.route("/")
def home():
    return render_template("index.html")

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
    return redirect(url_for("views.admin"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FREECAD_PROJECTS_DIR = os.path.join(BASE_DIR, 'FreeCadProjects')

@views.route('/projects/<session_id>')
def serve_project(session_id):
    """Serve the HTML file for a given session."""
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
        execute_query("INSERT INTO Stairs (session_id, length, width, height, step_height, number_of_steps, Type, generated_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (session_id, length, width, height, step_height, num_steps, "proste", date.today()))
        subprocess.run([freecad_path, '-c', 'FreeCadScripts/Schody_Proste.FCMacro', session_id, str(length), str(width), str(height), str(step_height), str(num_steps)])
        return redirect(url_for('views.result', session_id=session_id))
    return render_template('create.html')

@views.route('/result/<session_id>')
def result(session_id):
    return render_template('result.html', session_id=session_id)