# pip install streamlit sqlite3 pandas forex-python

import streamlit as st
import sqlite3
import pandas as pd
import re
from forex_python.converter import CurrencyRates  # For currency conversions
import datetime

conn = sqlite3.connect('web_management.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS websites
             (id INTEGER PRIMARY KEY, url TEXT, type TEXT, currency TEXT, pricing TEXT, region TEXT, language TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS changes
             (id INTEGER PRIMARY KEY, timestamp TEXT, action TEXT, website_id INTEGER, old_value TEXT, new_value TEXT)''')
conn.commit()

def add_website(url, web_type, currency, pricing, region, lang):
    c.execute("INSERT INTO websites (url, type, currency, pricing, region, language) VALUES (?, ?, ?, ?, ?, ?)",
              (url, web_type, currency, pricing, region, lang))
    conn.commit()

def get_all_websites():
    df = pd.read_sql_query("SELECT * FROM websites", conn)
    return df

def update_website(website_id, field, new_value):
    old_value = pd.read_sql_query(f"SELECT {field} FROM websites WHERE id={website_id}", conn).iloc[0][0]
    c.execute(f"UPDATE websites SET {field} = ? WHERE id = ?", (new_value, website_id))
    conn.commit()
    log_change(website_id, f"Updated {field}", old_value, new_value)

def log_change(website_id, action, old_value, new_value):
    timestamp = datetime.datetime.now().isoformat()
    c.execute("INSERT INTO changes (timestamp, action, website_id, old_value, new_value) VALUES (?, ?, ?, ?, ?)",
              (timestamp, action, website_id, old_value, new_value))
    conn.commit()

def get_changes():
    df = pd.read_sql_query("SELECT * FROM changes", conn)
    return df

def process_ai_command(command):
    command = command.lower()
    
    match_currency = re.match(r"change currency of website (\d+) to (\w+)", command)
    if match_currency:
        website_id, new_currency = match_currency.groups()
        try:
            update_website(int(website_id), 'currency', new_currency.upper())
            return f"Currency changed to {new_currency.upper()} for website {website_id}."
        except:
            return "Error: Invalid website ID."
    
    match_increase = re.match(r"increase ticket size by (\d+)% on all (\w+) websites", command)
    if match_increase:
        percent, web_type = match_increase.groups()
        df = get_all_websites()
        gaming_sites = df[df['type'] == web_type]
        for idx, row in gaming_sites.iterrows():
            try:
                old_pricing = float(row['pricing'])
                new_pricing = old_pricing * (1 + int(percent)/100)
                update_website(row['id'], 'pricing', str(new_pricing))
            except:
                pass
        return f"Pricing increased by {percent}% on all {web_type} websites."
    
    match_conversion = re.match(r"apply (\w+) to (\w+) conversion on selected websites", command)
    if match_conversion:
        from_curr, to_curr = match_conversion.groups()
        cr = CurrencyRates()
        rate = cr.get_rate(from_curr.upper(), to_curr.upper())
   
        df = get_all_websites()
        for idx, row in df.iterrows():
            if row['currency'] == from_curr.upper():
                try:
                    old_pricing = float(row['pricing'])
                    new_pricing = old_pricing * rate
                    update_website(row['id'], 'currency', to_curr.upper())
                    update_website(row['id'], 'pricing', str(new_pricing))
                except:
                    pass
        return f"Converted from {from_curr.upper()} to {to_curr.upper()} on applicable websites."
    
    if "preview" in command:
        return "Preview: Simulated changes shown below (implement actual preview logic)."
    
    if "suggest" in command:
        return "Suggestion: Based on region, recommend USD for US sites."
    
    return "Command not understood. Try examples like: 'Change currency of website 1 to USD'"

st.title("Centralized AI-Powered Web Management System")

st.sidebar.title("Menu")
page = st.sidebar.radio("Go to", ["Dashboard", "Add Website", "AI Command Panel", "History & Logs"])

if page == "Dashboard":
    st.header("Dashboard")
    df = get_all_websites()
    if not df.empty:
        st.dataframe(df)
        for idx, row in df.iterrows():
            st.write(f"**{row['url']}** - Status: Active")  # Simulate status
    else:
        st.write("No websites added yet.")

elif page == "Add Website":
    st.header("Add New Website")
    with st.form(key='add_website'):
        url = st.text_input("Website URL")
        web_type = st.selectbox("Website Type", ["e-commerce", "ticketing", "gaming", "service-based"])
        currency = st.selectbox("Current Currency", ["INR", "USD", "EUR"])
        pricing = st.text_input("Ticket Size / Pricing (e.g., 100 or 'Basic:50,Premium:100')")
        region = st.text_input("Region")
        lang = st.text_input("Language")
        submit = st.form_submit_button("Add")
        if submit:
            add_website(url, web_type, currency, pricing, region, lang)
            st.success("Website added!")

elif page == "AI Command Panel":
    st.header("AI Command Panel")
    command = st.text_area("Enter AI Command (e.g., 'Change currency of website 1 to USD')")
    if st.button("Execute"):
        if command:
            result = process_ai_command(command)
            st.write("AI Response:", result)
            # Simulate preview
            st.write("Preview of Changes:")
            st.dataframe(get_all_websites())
        else:
            st.warning("Enter a command.")
    
    st.subheader("Suggested Commands")
    st.write("- Change currency of Website A to USD")
    st.write("- Increase ticket size by 20% on all gaming websites")
    st.write("- Preview price changes before publishing")

elif page == "History & Logs":
    st.header("Change History")
    df_changes = get_changes()
    if not df_changes.empty:
        st.dataframe(df_changes)
        # Rollback simulation
        rollback_id = st.selectbox("Select Change ID to Rollback", df_changes['id'])
        if st.button("Rollback"):
            change = df_changes[df_changes['id'] == rollback_id].iloc[0]
            # Parse action to revert (simplified)
            if "currency" in change['action']:
                update_website(change['website_id'], 'currency', change['old_value'])
            st.success("Rollback applied.")
    else:
        st.write("No changes logged yet.")
