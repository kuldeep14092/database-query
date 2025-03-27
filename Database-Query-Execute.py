import gradio as gr
import mysql.connector
import pandas as pd
import os

# Database Configuration
DB_CONFIG = {
    "host": "192.170.1.181",
    "user": "rao",
    "password": "rao123",
    "database": "test1",
}

# User Authentication Data
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

# Function to Get Tables from Database
def get_table_names():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except mysql.connector.Error:
        return []

# Function to Execute SQL Queries
def execute_query(query, login_state):
    if not login_state.get("logged_in"):
        return gr.update(value="❌ Access Denied! Please log in.", visible=True), None, gr.update(visible=False), ""

    if login_state["role"] != "Admin" and not query.strip().lower().startswith("select"):
        return gr.update(value="❌ Access Denied! Only SELECT queries are allowed for non-admin users.", visible=True), None, gr.update(visible=False), ""

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)

        if query.strip().lower().startswith("select"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)

            # Save DataFrame as CSV
            csv_path = "/tmp/output.csv"
            df.to_csv(csv_path, index=False)

            cursor.close()
            conn.close()
            return gr.update(value="✅ Query executed successfully!", visible=True), df, gr.update(visible=True), csv_path

        else:
            conn.commit()
            cursor.close()
            conn.close()
            return gr.update(value="✅ Query executed successfully!", visible=True), None, gr.update(visible=False), ""

    except mysql.connector.Error as e:
        return gr.update(value=f"❌ Database error: {e}", visible=True), None, gr.update(visible=False), ""

# Login Function
def login(username, password, login_state):
    user_data = USERS.get(username)

    if user_data and user_data["password"] == password:
        login_state["logged_in"] = True
        login_state["username"] = username
        login_state["role"] = user_data["role"]

        tables = get_table_names()
        dashboard_text = "👑 **Admin Dashboard**" if user_data["role"] == "Admin" else "👤 **User Dashboard**"

        return (
            gr.update(value=f"✅ Welcome, {username}! You have **{user_data['role']} Access**.", visible=True),
            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=True), gr.update(visible=True, value=dashboard_text),
            gr.update(visible=True), gr.update(visible=True),
            gr.update(visible=True), gr.update(visible=False),  # Hide CSV button initially
            login_state
        )

    return (
        gr.update(value="❌ Incorrect username or password!", visible=True),
        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        login_state
    )

# Logout Function
def logout(login_state):
    login_state.clear()

    return (
        gr.update(value="✅ You have been logged out successfully!", visible=True),
        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        login_state
    )

# Gradio UI
with gr.Blocks() as gr_app:
    login_state = gr.State({"logged_in": False})

    login_heading = gr.Markdown("## 🔒 Login Page")
    error_message = gr.Markdown("", visible=False)

    with gr.Row():
        username = gr.Textbox(label="Username", placeholder="Enter username")
        password = gr.Textbox(label="Password", type="password", placeholder="Enter password")

    login_btn = gr.Button("Login")
    dashboard_heading = gr.Markdown("", visible=False)
    query_input = gr.TextArea(label="Enter SQL Query", visible=False)
    execute_btn = gr.Button("Run Query", visible=False)
    output_table = gr.Dataframe(visible=False)
    download_btn = gr.DownloadButton(label="Download CSV", visible=False)  # ✅ Fixed: Correct Download Button
    logout_btn = gr.Button("Logout", visible=False)

    # Click Action for Execute Query
    execute_btn.click(
        execute_query,
        inputs=[query_input, login_state],
        outputs=[error_message, output_table, download_btn, download_btn]  # ✅ CSV file path assigned to download button
    )

    # Login Click
    login_btn.click(
        login,
        inputs=[username, password, login_state],
        outputs=[
            error_message, login_heading, username, password, login_btn,
            logout_btn, dashboard_heading,
            query_input, execute_btn, output_table,
            download_btn,  # Ensure CSV button is hidden initially
            login_state
        ]
    )

    # Logout Click
    logout_btn.click(
        logout,
        inputs=[login_state],
        outputs=[
            error_message, login_heading, username, password, login_btn,
            logout_btn, dashboard_heading,
            query_input, execute_btn, output_table,
            download_btn,  # Hide CSV button on logout
            login_state
        ]
    )

gr_app.launch(server_name="0.0.0.0", server_port=7861, share=True)
