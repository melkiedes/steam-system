from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from datetime import datetime, timedelta

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.config['SECRET_KEY'] = 'steam_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- LOGIN MANAGER ----------------
login_manager = LoginManager()
login_manager.init_app(app)

# THIS FIXES YOUR "UNAUTHORIZED" ISSUE
login_manager.login_view = "login"

# ---------------- USER MODEL ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class SteamLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    pressure = db.Column(db.String(50))
    temperature = db.Column(db.String(50))
    water_level = db.Column(db.String(50))
    fuel = db.Column(db.String(50))
    fuel_consumption = db.Column(db.String(50))
    remark = db.Column(db.String(200))

    operator = db.Column(db.String(100))

    timestamp = db.Column(db.DateTime)

# ---------------- LOAD USER ----------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- HOME (DASHBOARD) ----------------
@app.route("/")
@login_required
def home():

    latest_log = SteamLog.query.order_by(SteamLog.id.desc()).first()

    return render_template("index.html", log=latest_log)

# ---------------- LOGIN ----------------
@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            login_user(user)
            return redirect(url_for('home'))

        return "Invalid username or password"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/add", methods=['GET', 'POST'])
@login_required
def add():

    if request.method == 'POST':

        pressure = request.form.get('pressure')
        temperature = request.form.get('temperature')
        water_level = request.form.get('water_level')
        fuel = request.form.get('fuel')
        fuel_consumption = request.form.get('fuel_consumption')
        remark = request.form.get('remark')

        new_log = SteamLog(
            pressure=pressure,
            temperature=temperature,
            water_level=water_level,
            fuel=fuel,
            fuel_consumption=fuel_consumption,
            remark=remark,
            operator=current_user.username,
            timestamp=datetime.now()
        )

        db.session.add(new_log)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template("add.html")

@app.route("/logs")
@login_required
def logs():

    search = request.args.get('search')

    if search:

        all_logs = SteamLog.query.filter(
            SteamLog.pressure.contains(search)
        ).all()

    else:

        all_logs = SteamLog.query.all()

    return render_template("logs.html", logs=all_logs)

@app.route("/chart")
@login_required
def chart():

    logs = SteamLog.query.all()

    pressures = []
    temperatures = []
    fuel = []
    efficiency = []
    labels = []

    for log in logs:

        try:
            pressure = float(log.pressure)
            temperature = float(log.temperature)

            fuel_value = log.fuel_consumption.replace("kg", "").strip()
            fuel_value = float(fuel_value)

            pressures.append(pressure)
            temperatures.append(temperature)
            fuel.append(fuel_value)

            if fuel_value != 0:
                efficiency.append(round(pressure / fuel_value, 2))
            else:
                efficiency.append(0)

            labels.append(str(log.id))

        except:
            pass

    return render_template(
        "chart.html",
        pressures=pressures,
        temperatures=temperatures,
        fuel=fuel,
        efficiency=efficiency,
        labels=labels
    )

@app.route("/efficiency")
@login_required
def efficiency():

    logs = SteamLog.query.all()

    from datetime import datetime, timedelta
    now = datetime.now()

    def calc(log_list):

        total = 0
        count = 0

        latest = 0

        for log in log_list:

            try:
                pressure = float(log.pressure)
                fuel = float(log.fuel_consumption.replace("kg", "").strip())

                if fuel != 0:
                    eff = (pressure / fuel) * 100
                    total += eff
                    count += 1
                    latest = eff

            except:
                pass

        avg = round(total / count, 2) if count > 0 else 0
        return round(latest, 2), avg

    # ---------------- FILTERS ----------------

    latest_log = logs[-1] if logs else None

    monthly_logs = [l for l in logs if l.timestamp and l.timestamp >= now - timedelta(days=30)]
    quarterly_logs = [l for l in logs if l.timestamp and l.timestamp >= now - timedelta(days=90)]
    semi_logs = [l for l in logs if l.timestamp and l.timestamp >= now - timedelta(days=182)]
    yearly_logs = [l for l in logs if l.timestamp and l.timestamp >= now - timedelta(days=365)]

    # ---------------- CALCULATIONS ----------------

    latest_eff, latest_avg = calc([latest_log]) if latest_log else (0, 0)
    monthly_latest, monthly_avg = calc(monthly_logs)
    quarterly_latest, quarterly_avg = calc(quarterly_logs)
    semi_latest, semi_avg = calc(semi_logs)
    yearly_latest, yearly_avg = calc(yearly_logs)
    overall_latest, overall_avg = calc(logs)

    return render_template(
        "efficiency.html",

        latest_eff=latest_eff if latest_log else 0,
        latest_avg=latest_avg,

        monthly_latest=monthly_latest,
        monthly_avg=monthly_avg,

        quarterly_latest=quarterly_latest,
        quarterly_avg=quarterly_avg,

        semi_latest=semi_latest,
        semi_avg=semi_avg,

        yearly_latest=yearly_latest,
        yearly_avg=yearly_avg,

        overall_avg=overall_avg
    )

@app.route("/delete/<int:id>")
@login_required
def delete(id):

    log = SteamLog.query.get_or_404(id)

    db.session.delete(log)
    db.session.commit()

    return redirect(url_for('logs'))

@app.route("/edit/<int:id>", methods=['GET', 'POST'])
@login_required
def edit(id):

    log = SteamLog.query.get_or_404(id)

    if request.method == 'POST':

        log.pressure = request.form.get('pressure')
        log.temperature = request.form.get('temperature')
        log.water_level = request.form.get('water_level')
        log.fuel = request.form.get('fuel')
        log.remark = request.form.get('remark')

        db.session.commit()

        return redirect(url_for('logs'))

    return render_template("edit.html", log=log)

# ---------------- CREATE DATABASE + ADMIN ----------------
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(username='admin').first()

    if not admin:
        new_admin = User(username='admin', password='admin123')
        db.session.add(new_admin)
        db.session.commit()

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)