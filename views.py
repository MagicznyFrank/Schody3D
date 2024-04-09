from flask import Blueprint, render_template, request, redirect, url_for
from database import execute_query, fetch_data
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
    # Pobierz dane z tabeli osoby
    stairs = fetch_data("SELECT * FROM Stairs")
    return render_template("admin.html", stairs=stairs)

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
        execute_query("INSERT INTO Stairs (session_id, length, width, height, step_height, number_of_steps) VALUES (?, ?, ?, ?, ?, ?)",
                      (session_id, length, width, height, step_height, num_steps))

        # Wywołaj skrypt FreeCADa
        subprocess.run(
            [freecad_path, '-c', 'FreeCadScripts/Schody_Proste.FCMacro', str(length), str(width),
             str(height), str(step_height), str(num_steps)])

        return render_template('result.html')

    return render_template('create.html')


@views.route('/result/')
def result():
    return render_template('result.html')
