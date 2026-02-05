# Web.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # change in production

# In-memory storage
websites = []           # list of dicts
website_id_counter = 1
pending_changes = {}    # {website_id: {'currency': new, 'ticket_size': new}}
history = []            # list of {'time':, 'command':, 'changes': [{website_id, old, new}]}

# Simple exchange rates (USD base)
rates = {
    'INR': {'USD': 0.012, 'EUR': 0.011},
    'USD': {'INR': 83.3, 'EUR': 0.92},
    'EUR': {'INR': 90.9, 'USD': 1.09}
}

def get_rate(from_curr, to_curr):
    if from_curr == to_curr:
        return 1.0
    return rates.get(from_curr, {}).get(to_curr, 1.0)

# Home 
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    message = None
    if request.method == 'POST' and 'command' in request.form:
        command = request.form['command'].strip()
        if command:
            success = parse_and_prepare(command)
            if success:
                return redirect(url_for('preview'))
            else:
                message = "I didn't understand that command. Try one of the examples."

    return render_template('dashboard.html', websites=websites, message=message)

# Simple login (for demo)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == 'admin':  # change this!
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Wrong password')
    return render_template('login.html')

# Add website
@app.route('/add', methods=['GET', 'POST'])
def add_website():
    if request.method == 'POST':
        global website_id_counter
        name = request.form['name'].strip()
        if any(w['name'].lower() == name.lower() for w in websites):
            flash('Website name already exists')
        else:
            new_site = {
                'id': website_id_counter,
                'name': name,
                'url': request.form['url'],
                'type': request.form['type'],
                'currency': request.form['currency'],
                'ticket_size': float(request.form['ticket_size'] or 0),
                'region': request.form['region'],
                'language': request.form['language']
            }
            websites.append(new_site)
            website_id_counter += 1
            return redirect(url_for('dashboard'))
    return render_template('add_website.html')

# Command parsing – simple but handles the required examples
def parse_and_prepare(command):
    global pending_changes
    pending_changes = {}
    cmd = command.lower()

    # 1. Change currency of specific website
    if 'change currency of' in cmd and 'to' in cmd:
        parts = command.split()
        try:
            name = parts[parts.index('of') + 1 : parts.index('to')][0]
            new_curr = parts[parts.index('to') + 1].upper()
            site = next((w for w in websites if w['name'].lower() == name.lower()), None)
            if site and new_curr in ['USD', 'EUR', 'INR']:
                rate = get_rate(site['currency'], new_curr)
                new_price = site['ticket_size'] * rate
                pending_changes[site['id']] = {
                    'currency': new_curr,
                    'ticket_size': round(new_price, 2)
                }
                return True
        except:
            pass

    # 2. Increase ticket size by % on all of a type
    match = re.search(r'increase ticket size by (\d+)% on all (\w+) websites', cmd)
    if match:
        percent = int(match.group(1)) / 100 + 1
        wtype = match.group(2).lower()
        for site in websites:
            if site['type'].lower() == wtype:
                new_price = site['ticket_size'] * percent
                pending_changes[site['id']] = {
                    'currency': site['currency'],
                    'ticket_size': round(new_price, 2)
                }
        return bool(pending_changes)

    # 3. Currency conversion on all (or "selected" = all for simplicity)
    if 'apply inr to eur conversion' in cmd or 'apply' in cmd and 'conversion' in cmd:
        for site in websites:
            if site['currency'] == 'INR':
                rate = get_rate('INR', 'EUR')
                pending_changes[site['id']] = {
                    'currency': 'EUR',
                    'ticket_size': round(site['ticket_size'] * rate, 2)
                }
        return bool(pending_changes)

    return False

@app.route('/preview')
def preview():
    if not pending_changes:
        return redirect(url_for('dashboard'))
    
    changes_list = []
    for wid, change in pending_changes.items():
        site = next(w for w in websites if w['id'] == wid)
        changes_list.append({
            'site': site,
            'old_currency': site['currency'],
            'new_currency': change['currency'],
            'old_price': site['ticket_size'],
            'new_price': change['ticket_size']
        })
    return render_template('preview.html', changes=changes_list)

@app.route('/apply')
def apply_changes():
    global pending_changes, history
    if not pending_changes:
        return redirect(url_for('dashboard'))

    applied = []
    for wid, change in pending_changes.items():
        site = next(w for w in websites if w['id'] == wid)
        old = {'currency': site['currency'], 'ticket_size': site['ticket_size']}
        site['currency'] = change['currency']
        site['ticket_size'] = change['ticket_size']
        applied.append({'site': site['name'], 'old': old, 'new': change})
    
    history.append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'command': session.get('last_command', 'Unknown'),
        'changes': applied
    })
    pending_changes = {}
    return redirect(url_for('dashboard'))

@app.route('/cancel')
def cancel():
    global pending_changes
    pending_changes = {}
    return redirect(url_for('dashboard'))

@app.route('/history')
def history():
    return render_template('history.html', history=history)

if __name__ == '__main__':
    app.run(debug=True)
