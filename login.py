import gradio as gr
import mysql.connector
import pandas as pd

# Database Configuration
DB_CONFIG = {
    "host": "192.170.1.181",
    "user": "rao",
    "password": "rao123",
    "database": "status",
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

# Function to Get Column Names from a Table
def get_column_names(table_name, login_state):
    if not login_state.get("logged_in"):
        return gr.update(value="❌ Access Denied! Please log in.", visible=True), gr.update(choices=[], visible=False)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        columns = [column[0] for column in cursor.fetchall()]
        cursor.close()
        conn.close()
        return gr.update(value=f"✅ Columns for table '{table_name}' loaded.", visible=True), gr.update(choices=columns, value=columns[0] if columns else None, visible=True)

    except mysql.connector.Error as e:
        return gr.update(value=f"❌ Database error: {e}", visible=True), gr.update(choices=[], visible=False)

# Function to Display Selected Column Data
def display_selected_column_data(table_name, column_name, login_state):
    if not login_state.get("logged_in"):
        return gr.update(value="❌ Access Denied! Please log in.", visible=True), None

    if not column_name:
        return gr.update(value="⚠️ Please select a column.", visible=True), None

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = f"SELECT `{column_name}` FROM `{table_name}`"
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        df = pd.DataFrame(rows, columns=[column_name])
        return gr.update(value=f"✅ Data for column '{column_name}' loaded successfully!", visible=True), df

    except mysql.connector.Error as e:
        return gr.update(value=f"❌ Database error: {e}", visible=True), None

# Function to Execute Queries
def execute_query(query, login_state):
    if not login_state.get("logged_in"):
        return gr.update(value="❌ Access Denied! Please log in to execute queries.", visible=True), None

    if login_state["role"] != "Admin" and not query.strip().lower().startswith("select"):
        return gr.update(value="❌ Access Denied! Only SELECT queries are allowed for non-admin users.", visible=True), None

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)
        if query.strip().lower().startswith("select"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            cursor.close()
            conn.close()
            return gr.update(value="✅ Query executed successfully!", visible=True), df
        else:
            conn.commit()
            cursor.close()
            conn.close()
            return gr.update(value="✅ Query executed successfully!", visible=True), None

    except mysql.connector.Error as e:
        return gr.update(value=f"❌ Database error: {e}", visible=True), None

# Authentication Function
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
            gr.update(visible=True), gr.update(visible=True),  
            gr.update(choices=tables, value=tables[0] if tables else None, visible=True),  # Visible for all users
            gr.update(visible=True),  # Column dropdown is now visible
            login_state
        )

    return (
        gr.update(value="❌ Incorrect username or password!", visible=True), 
        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),  # Ensure table and column dropdowns are hidden
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
        gr.update(visible=False), gr.update(visible=False),  # Hide and column dropdowns after logout
        login_state
    )

# Gradio UI
with gr.Blocks() as gr_app:
    login_state = gr.State({"logged_in": False})  

    login_heading = gr.Markdown("## 🔒 Login Page")  

    with gr.Row():
        username = gr.Textbox(label="Username", placeholder="Enter username")
        password = gr.Textbox(label="Password", type="password", placeholder="Enter password")

    login_btn = gr.Button("Login")
    error_message = gr.Markdown("", visible=False)  

    dashboard_heading = gr.Markdown("", visible=False)  
    select_table = gr.Dropdown(label="Select Table", choices=[], visible=False)
    select_column = gr.Dropdown(label="Select Column", choices=[], visible=False)
    query_input = gr.TextArea(label="Enter SQL Query", visible=False)
    output_table = gr.Dataframe(visible=False)
    execute_btn = gr.Button("Run Query", visible=False)
    logout_btn = gr.Button("Logout", visible=False)

    admin_form_heading = gr.Markdown(visible=False)

    login_btn.click(
        login, 
        inputs=[username, password, login_state], 
        outputs=[
            error_message, login_heading, username, password, login_btn, logout_btn, 
            dashboard_heading, query_input, execute_btn, output_table, 
            admin_form_heading, select_table, select_column,  
            login_state
        ]
    )

    select_table.change(
        get_column_names,
        inputs=[select_table, login_state],
        outputs=[error_message, select_column]
    )

    select_column.change(
        display_selected_column_data,
        inputs=[select_table, select_column, login_state],
        outputs=[error_message, output_table]
    )

    query_input.change(
        execute_query,
        inputs=[query_input, login_state],
        outputs=[error_message, output_table]
    )

    logout_btn.click(
        logout, 
        inputs=[login_state],
        outputs=[
            error_message, login_heading, username, password, login_btn, 
            logout_btn, dashboard_heading, 
            query_input, execute_btn, output_table, 
            admin_form_heading, select_table, select_column,  
            login_state
        ]
    )

gr_app.launch(server_name="192.170.1.181", server_port=7860, share=True)
