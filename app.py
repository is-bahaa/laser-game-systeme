from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import datetime
import uuid
from threading import Timer

app = Flask(__name__)

# === CONFIG ===
DB_DIR = os.path.join(os.path.dirname(__file__), 'database')
MATCHES_FILE = os.path.join(DB_DIR, 'matches.json')
USERS_FILE = os.path.join(DB_DIR, 'users.json')
BUGS_FILE = os.path.join(DB_DIR, 'bugs.json')
SETTINGS_FILE = os.path.join(DB_DIR, 'settings.json')

VESTES = [
    "Hulk", "Batman", "Superman", "Spiderman", "Flash", "Ironman",
    "Joker", "Venom", "Sonic", "Samurai", "Yoda", "Ninja",
    "Naplam", "Conan", "Watchmen", "Rambo", "Robocop", "Jonwick",
    "Elektra", "Thor", "Hellboy", "Blade", "Punisher", "Falcon"
]

USERS = {
    "Yosra": {"pin": "0000", "role": "admin", "color": "#00f0ff"},
    "Khaled": {"pin": "1111", "role": "admin", "color": "#ff00ff"},
    "Controle": {"pin": "2222", "role": "viewer", "color": "#39ff14"}
}

# Active match timers
active_timers = {}
MATCH_DURATION = 15 * 60  # 15 minutes in seconds

# === HELPERS ===
def ensure_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    for f in [MATCHES_FILE, BUGS_FILE, SETTINGS_FILE]:
        if not os.path.exists(f):
            with open(f, 'w') as file:
                json.dump([], file)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as file:
            json.dump(USERS, file)

def load_json(path):
    ensure_db()
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    ensure_db()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def end_match_auto(match_id):
    """Auto-end match after 15 minutes"""
    matches = load_json(MATCHES_FILE)
    for m in matches:
        if m['id'] == match_id and m['status'] == 'active':
            m['status'] = 'ended'
            m['ended_at'] = datetime.datetime.now().isoformat()
            save_json(MATCHES_FILE, matches)
            break
    if match_id in active_timers:
        del active_timers[match_id]

# === ROUTES ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    pin = data.get('pin', '').strip()
    users = load_json(USERS_FILE)
    if username in users and users[username]['pin'] == pin:
        return jsonify({"success": True, "user": {"name": username, "role": users[username]['role'], "color": users[username]['color']}})
    return jsonify({"success": False, "error": "Identifiants incorrects"})

@app.route('/api/matches', methods=['GET', 'POST'])
def matches():
    if request.method == 'GET':
        return jsonify(load_json(MATCHES_FILE))
    data = request.json
    matches = load_json(MATCHES_FILE)

    accesses = min(int(data.get('accesses', 0)), 24)
    if accesses <= 0:
        return jsonify({"success": False, "error": "Veuillez entrer un nombre d'acces"})

    players = accesses

    new_match = {
        "id": str(uuid.uuid4())[:8],
        "players": players,
        "accesses": accesses,
        "bugs": [],
        "status": "active",
        "created_by": data.get('created_by', ''),
        "created_at": datetime.datetime.now().isoformat(),
        "ended_at": None,
        "duration": 15
    }
    matches.append(new_match)
    save_json(MATCHES_FILE, matches)

    timer = Timer(MATCH_DURATION, end_match_auto, args=[new_match['id']])
    timer.start()
    active_timers[new_match['id']] = timer

    return jsonify({"success": True, "match": new_match})

@app.route('/api/matches/<match_id>', methods=['PUT', 'DELETE'])
def match_detail(match_id):
    matches = load_json(MATCHES_FILE)
    idx = next((i for i, m in enumerate(matches) if m['id'] == match_id), None)
    if idx is None:
        return jsonify({"success": False, "error": "Manche introuvable"})

    if request.method == 'DELETE':
        if match_id in active_timers:
            active_timers[match_id].cancel()
            del active_timers[match_id]
        matches.pop(idx)
        save_json(MATCHES_FILE, matches)
        return jsonify({"success": True})

    data = request.json
    if 'status' in data:
        matches[idx]['status'] = data['status']
        if data['status'] == 'ended':
            matches[idx]['ended_at'] = datetime.datetime.now().isoformat()
            if match_id in active_timers:
                active_timers[match_id].cancel()
                del active_timers[match_id]
    if 'players' in data:
        matches[idx]['players'] = min(data['players'], 24)
    if 'accesses' in data:
        matches[idx]['accesses'] = min(data['accesses'], 24)
    if 'bugs' in data:
        matches[idx]['bugs'] = data['bugs']
    save_json(MATCHES_FILE, matches)
    return jsonify({"success": True, "match": matches[idx]})

@app.route('/api/matches/<match_id>/end', methods=['POST'])
def end_match(match_id):
    matches = load_json(MATCHES_FILE)
    for m in matches:
        if m['id'] == match_id:
            m['status'] = 'ended'
            m['ended_at'] = datetime.datetime.now().isoformat()
            if match_id in active_timers:
                active_timers[match_id].cancel()
                del active_timers[match_id]
            save_json(MATCHES_FILE, matches)
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Manche introuvable"})

@app.route('/api/matches/<match_id>/bug', methods=['POST'])
def add_bug(match_id):
    data = request.json
    matches = load_json(MATCHES_FILE)
    for m in matches:
        if m['id'] == match_id:
            bug = {
                "id": str(uuid.uuid4())[:8],
                "veste": data.get('veste', ''),
                "description": data.get('description', ''),
                "reported_by": data.get('reported_by', ''),
                "time": datetime.datetime.now().isoformat()
            }
            m['bugs'].append(bug)
            m['players'] = min(m.get('players', 0) + 1, 24)
            save_json(MATCHES_FILE, matches)
            return jsonify({"success": True, "match": m})
    return jsonify({"success": False, "error": "Manche introuvable"})

@app.route('/api/matches/<match_id>/bug/<bug_id>', methods=['DELETE'])
def delete_bug(match_id, bug_id):
    matches = load_json(MATCHES_FILE)
    for m in matches:
        if m['id'] == match_id:
            bug_idx = next((i for i, b in enumerate(m['bugs']) if b.get('id') == bug_id), None)
            if bug_idx is not None:
                m['bugs'].pop(bug_idx)
                # Decrease players by 1 when bug is deleted
                m['players'] = max(m.get('players', 0) - 1, m.get('accesses', 0))
                save_json(MATCHES_FILE, matches)
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Bug introuvable"})
    return jsonify({"success": False, "error": "Manche introuvable"})

@app.route('/api/day-summary', methods=['GET'])
def day_summary():
    date = request.args.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
    matches = load_json(MATCHES_FILE)
    day_matches = [m for m in matches if m['created_at'].startswith(date)]
    total_matches = len(day_matches)
    total_players = sum(m['players'] for m in day_matches)
    total_accesses = sum(m['accesses'] for m in day_matches)
    total_bugs = sum(len(m['bugs']) for m in day_matches)
    return jsonify({
        "date": date,
        "total_matches": total_matches,
        "total_players": total_players,
        "total_accesses": total_accesses,
        "total_bugs": total_bugs,
        "matches": day_matches
    })

@app.route('/api/export/excel')
def export_excel():
    date = request.args.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
    matches = load_json(MATCHES_FILE)
    day_matches = [m for m in matches if m['created_at'].startswith(date)]

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rapport"

    ws.merge_cells('A1:F1')
    ws['A1'] = f"Rapport Geek Laser Tag - {date}"
    ws['A1'].font = Font(size=16, bold=True, color="FFFFFF")
    ws['A1'].fill = PatternFill(start_color="6C5CE7", end_color="6C5CE7", fill_type="solid")
    ws['A1'].alignment = Alignment(horizontal='center')

    headers = ["Manche", "Joueurs", "Acces", "Bugs", "Statut", "Creee par"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="00B894", end_color="00B894", fill_type="solid")

    for row, m in enumerate(day_matches, 3):
        ws.cell(row=row, column=1, value=f"Manche {row-2}")
        ws.cell(row=row, column=2, value=m['players'])
        ws.cell(row=row, column=3, value=m['accesses'])
        ws.cell(row=row, column=4, value=len(m['bugs']))
        ws.cell(row=row, column=5, value="Terminee" if m['status'] == 'ended' else "En cours")
        ws.cell(row=row, column=6, value=m['created_by'])

    total_row = len(day_matches) + 3
    ws.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=sum(m['players'] for m in day_matches)).font = Font(bold=True)
    ws.cell(row=total_row, column=3, value=sum(m['accesses'] for m in day_matches)).font = Font(bold=True)
    ws.cell(row=total_row, column=4, value=sum(len(m['bugs']) for m in day_matches)).font = Font(bold=True)

    ws2 = wb.create_sheet("Detail Bugs")
    ws2.append(["Manche", "Veste", "Description", "Signale par", "Heure"])
    for m in day_matches:
        for b in m['bugs']:
            ws2.append([m['id'], b['veste'], b['description'], b['reported_by'], b['time']])

    path = os.path.join(DB_DIR, f"rapport_{date}.xlsx")
    wb.save(path)
    return send_file(path, as_attachment=True, download_name=f"GeekLaserTag_Rapport_{date}.xlsx")

@app.route('/api/export/pdf')
def export_pdf():
    date = request.args.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
    matches = load_json(MATCHES_FILE)
    day_matches = [m for m in matches if m['created_at'].startswith(date)]

    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.set_text_color(108, 92, 231)
            self.cell(0, 10, f'Rapport Geek Laser Tag - {date}', 0, 1, 'C')
            self.ln(5)

    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)

    pdf.set_fill_color(0, 184, 148)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 8, 'Manche', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Joueurs', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Acces', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Bugs', 1, 0, 'C', True)
    pdf.cell(40, 8, 'Statut', 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0)
    for i, m in enumerate(day_matches, 1):
        pdf.cell(40, 8, f'Manche {i}', 1, 0, 'C')
        pdf.cell(30, 8, str(m['players']), 1, 0, 'C')
        pdf.cell(30, 8, str(m['accesses']), 1, 0, 'C')
        pdf.cell(30, 8, str(len(m['bugs'])), 1, 0, 'C')
        pdf.cell(40, 8, 'Terminee' if m['status'] == 'ended' else 'En cours', 1, 1, 'C')

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 8, 'TOTAL', 1, 0, 'C')
    pdf.cell(30, 8, str(sum(m['players'] for m in day_matches)), 1, 0, 'C')
    pdf.cell(30, 8, str(sum(m['accesses'] for m in day_matches)), 1, 0, 'C')
    pdf.cell(30, 8, str(sum(len(m['bugs']) for m in day_matches)), 1, 0, 'C')
    pdf.cell(40, 8, '', 1, 1, 'C')

    path = os.path.join(DB_DIR, f"rapport_{date}.pdf")
    pdf.output(path)
    return send_file(path, as_attachment=True, download_name=f"GeekLaserTag_Rapport_{date}.pdf")

if __name__ == '__main__':
    ensure_db()
    import socket
    hostname = socket.gethostname()
    local_ip = socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
    print(f"=== Geek Laser Tag Server ===")
    print(f"Ouvrir Chrome sur: http://{local_ip}:5000")
    print(f"Ou: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
