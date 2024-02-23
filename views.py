from flask import Blueprint, render_template, request
import subprocess
import logging
freecad_path = "/home/magicfrank/Documents/freecad_appimage/squashfs-root/usr/bin/freecadcmd"

views = Blueprint(__name__, "views")

# Konfiguracja loggera
#logging.basicConfig(filename='logfile.log', level=logging.INFO)


@views.route("/")
def home():
    return render_template("index.html")


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























