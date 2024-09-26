from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from config import newsapi_key, secret_key

app = Flask(__name__)
app.secret_key = secret_key
users_folder = 'users'

# Überprüfen, ob der Ordner 'users' existiert, andernfalls erstellen (es werden keine Benutzerdaten auf GitHub hochgeladen, weshalb der Ordner nicht im Repo existiert)
if not os.path.exists(users_folder):
    os.makedirs(users_folder)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Wenn das Forumlar vom User abgeschickt wurde, wird der Inhalt in Variablen gespeichert
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Überprüfen, ob die E-Mail-Adresse bereits vergeben ist
        user_file_path = os.path.join(users_folder, f"{email}.json")
        if os.path.exists(user_file_path):
            flash('Diese E-Mail-Adresse ist bereits vergeben. Bitte verwenden Sie eine andere E-Mail-Adresse.')
            return redirect(url_for('register'))
        
        # Passwort wird verschlüsselt und in einer Variablen gespeichert
        hashed_password = generate_password_hash(password) 

        # Benutzerdaten in einem JSON-Objekt speichern
        user_data = {
            'email': email,
            'password': hashed_password,
            'dashboard': {
                'country': '',
                'category': '',
                'keyword': ''
            }
        }

        # JSON-Datei mit Benutzerdaten erstellen, die Datei wird nach der E-Mail-Adresse benannt
        with open(os.path.join(users_folder, f"{email}.json"), 'w') as f:
            json.dump(user_data, f)

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Wenn das Formular vom User abgeschickt wurde, wird der Inhalt in Variablen gespeichert
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_file = os.path.join(users_folder, f"{email}.json")
        # Überprüfen, ob die E-Mail-Adresse registriert ist, sonst wird eine Fehlermeldung angezeigt
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)

            # Überprüfen, ob das eingegebene Passwort mit dem gespeicherten Passwort übereinstimmt, sonst wird eine Fehlermeldung angezeigt
            if check_password_hash(user_data['password'], password):
                # Eine Session wird gestartet, um den Benutzer eingeloggt zu halten, die Session wird mit der E-Mail-Adresse des Benutzers verknüpft
                session['user'] = email
                return redirect(url_for('home'))
            else:
                flash('Das Passwort ist falsch.')
        else:
            flash('Die E-Mail-Adresse ist nicht registriert.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    # Die Session wird beendet, wenn der Benutzer sich ausloggt
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/home')
def home():
    # Überprüfen, ob der Benutzer eingeloggt ist, wenn nicht, wird er auf die Login-Seite weitergeleitet
    if 'user' not in session:
        return redirect(url_for('login'))

    # Die Variable user_file wird mit dem Pfad zur JSON-Datei des Benutzers erstellt
    user_file = os.path.join(users_folder, f"{session['user']}.json")
    # Die Benutzerdaten werden aus der JSON-Datei gelesen und in der Variablen user_data gespeichert
    with open(user_file, 'r') as f:
        user_data = json.load(f)

    # Falls der Benutzer Präferenzen festgelegt hat, werden die Präferenzen in Variablen gespeichert
    country = user_data['dashboard']['country']
    category = user_data['dashboard']['category']
    keyword = user_data['dashboard']['keyword']

    # Es wird ein leeres Dictionary erstellt, um kein Error zu erhalten, wenn keine Artikel gefunden werden oder der Benutzer keine Präferenzen festgelegt hat
    articles = {"articles": []}
    # Wenn der Benutzer Präferenzen festgelegt hat, werden die Artikel basierend auf den Präferenzen abgerufen
    if keyword or country or category:
        # Wenn der Benutzer ein Keyword eingegeben hat, wird die URL für die Suche nach Artikeln mit dem Keyword erstellt. Beim Keyword wird der Endpoint Everything verwendet, um mehr Artikel zu finden.
        if keyword:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': keyword,
                'apiKey': newsapi_key
            }
        # Wenn der Benutzer ein Land und eine Kategorie ausgewählt hat, wird die URL für die Suche nach Artikeln mit dem Land und der Kategorie erstellt. Bei Land und Kategorie wird der Endpoint Top-Headlines verwendet, um die wichtigsten Artikel zu finden. 
        else:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'country': country,
                'category': category,
                'apiKey': newsapi_key
            }

        # Die Artikel werden abgerufen und in der Variablen articles gespeichert
        articles = fetch_articles(url, params)
    
    return render_template('home.html', articles=articles['articles'])

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    # Überprüfen, ob der Benutzer eingeloggt ist, wenn nicht, wird er auf die Login-Seite weitergeleitet
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Wenn das Forumlar vom User abgeschickt wurde, wird der Inhalt in Variablen gespeichert
        country = request.form['country']
        category = request.form['category']
        keyword = request.form['keyword']

        # Die e-mail-Adresse des Benutzers wird aus der Session gelesen
        email = session['user']
        # Der Pfad zur JSON-Datei des Benutzers wird in der Variablen user_file gespeichert
        user_file = os.path.join(users_folder, f'{email}.json')

        # Die Benutzerdaten werden aus der JSON-Datei gelesen und in der Variablen user_data gespeichert
        with open(user_file, 'r') as file:
            user_data = json.load(file)

        # Die Präferenzen des Benutzers werden in der JSON-Datei aktualisiert
        user_data['dashboard'] = {
            'country': country,
            'category': category,
            'keyword': keyword,
        }

        # Die aktualisierten Benutzerdaten werden in der JSON-Datei gespeichert
        with open(user_file, 'w') as file:
            json.dump(user_data, file)
        # Der Benutzer wird auf die Home-Seite weitergeleitet
        return redirect(url_for('home'))
    return render_template('preferences.html')


@app.route('/search')
def search():
    # Überprüfen, ob der Benutzer eingeloggt ist, wenn nicht, wird er auf die Login-Seite weitergeleitet
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('search.html')


@app.route("/results", methods=["POST"])
def results():
    # Überprüfen, ob der Benutzer eingeloggt ist, wenn nicht, wird er auf die Login-Seite weitergeleitet
    if 'user' not in session:
        return redirect(url_for('login'))

    # Die Variablen country, category und keyword werden mit den Werten aus dem Formular gespeichert
    country = request.form.get("country")
    category = request.form.get("category")
    keyword = request.form.get("keyword")

    # Wenn der Benutzer ein Keyword eingegeben hat, wird die URL für die Suche nach Artikeln mit dem Keyword erstellt
    if keyword:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': keyword,
            'apiKey': newsapi_key
        }
    # Wenn der Benutzer ein Land und eine Kategorie ausgewählt hat, wird die URL für die Suche nach Artikeln mit dem Land und der Kategorie erstellt
    else:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'country': country,
            'category': category,
            'apiKey': newsapi_key
        }

    # Die Artikel werden abgerufen und in der Variablen articles gespeichert
    articles = fetch_articles(url, params)
    return render_template("results.html", articles=articles["articles"])

# Funktion für die API abfrage
def fetch_articles(url, params):
    # Die Anfrage wird an die API gesendet und die Antwort wird in der Variablen response gespeichert
    response = requests.get(url, params=params)
    # Überprüfen, ob die Anfrage erfolgreich war, andernfalls wird ein Error geworfen
    response.raise_for_status()
    # Die Antwort wird in JSON-Format umgewandelt und zurückgegeben
    return response.json()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
