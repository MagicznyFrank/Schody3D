from flask import Blueprint, render_template, request, redirect, url_for
from database import execute_query, fetch_data
import secrets
import subprocess
import logging
freecad_path = "/schody3d/FreeCadapp/freecad_appimage/squashfs-root/usr/bin/freecadcmd"

views = Blueprint(__name__, "views")


def generate_session_id():
    session_id = secrets.token_hex(16)
    return session_id

@views.route("/")
def home():
    return render_template("index.html")
@views.route("/admin/")
def admin():
    # Pobierz dane z tabeli osoby
    people = fetch_data("SELECT * FROM osoby")
    return render_template("admin.html", people=people)

@views.route("/admin/add/", methods=["POST"])
def add_person():
    if request.method == "POST":
        # Pobierz dane z formularza
        imie = request.form["imie"]
        nazwisko = request.form["nazwisko"]
        # Dodaj osobę do bazy danych
        execute_query("INSERT INTO osoby (imie, nazwisko) VALUES (?, ?)", (imie, nazwisko))
        return redirect(url_for("views.admin"))

@views.route("/admin/delete/<int:id>")
def delete_person(id):
    # Usuń osobę o podanym id
    execute_query("DELETE FROM osoby WHERE id=?", (id,))
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

        subprocess.run(
            [freecad_path, '-c', 'FreeCadScripts/Schody_Proste.FCMacro', str(length), str(width),
             str(height), str(step_height), str(num_steps)])

        return render_template('result.html')

    return render_template('create.html')


@views.route('/result/')
def result():
    return render_template('result.html')
























