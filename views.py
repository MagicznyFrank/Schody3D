from flask import Blueprint, render_template, request, redirect, url_for
from database import execute_query, fetch_data
from datetime import date
import secrets
import subprocess
import logging
freecad_path = "/schody3d/FreeCadapp/freecad_appimage/squashfs-root/usr/bin/freecadcmd"

views = Blueprint(__name__, "views")


def generate_session_id():
    session_id = ''.join(str(secrets.randbelow(10)) for _ in range(16))
    return session_id

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
        # Logika zmiany kierunku sortowania
        previous_sort_by = request.args.get('prev_sort')  # Pobierz poprzedni typ sortowania z parametru URL
        if previous_sort_by and previous_sort_by == current_sort_by:
            # Odwróć kierunek sortowania jeśli kolumna była już sortowana
            new_order = 'desc' if current_order == 'asc' else 'asc'
        else:
            new_order = 'asc'  # Domyślne sortowanie rosnąco
        query += f" ORDER BY {current_sort_by} {new_order}"

    stairs = fetch_data(query)
    return render_template("admin.html", stairs=stairs, sort_by=current_sort_by, order=new_order, prev_sort=current_sort_by)

@views.route('/delete/<session_id>', methods=['POST'])
def delete_stairs(session_id):
    if request.method == 'POST':
        execute_query("DELETE FROM Stairs WHERE session_id=?", (session_id,))
        return redirect(url_for("views.admin"))

@views.route('/create/', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        # Pobierz dane z formularza
        length = request.form.get("Długość stopnia (mm)")
        width = request.form.get("Szerokość stopnia (mm)")
        height = request.form.get("Wysokość stopnia (mm)")
        step_height = request.form.get("Wysokość między stopniami (mm)")
        num_steps = request.form.get("Ilość stopni")
        button_disabled = True
        try:
            length = float(length)
            width = float(width)
            height = float(height)
            step_height = float(step_height)
            num_steps = int(num_steps)
        except ValueError as e:
            logging.error(f"Error converting arguments to numbers: {str(e)}")
            return render_template('error.html', error_message="Invalid input. Please enter numeric values.")

        # Generuj nowy identyfikator sesji
        session_id = generate_session_id()

        # Dodaj nowy rekord do bazy danych
        execute_query("INSERT INTO Stairs (session_id, length, width, height, step_height, number_of_steps, Type, generated_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (session_id, length, width, height, step_height, num_steps, "proste", date.today()))

        # Wywołaj skrypt FreeCADa
        subprocess.run(
            [freecad_path, '-c', 'FreeCadScripts/Schody_Proste.FCMacro', str(length), str(width),
             str(height), str(step_height), str(num_steps)])

        return render_template('result.html')

    return render_template('create.html')


@views.route('/result/')
def result():
    return render_template('result.html')
