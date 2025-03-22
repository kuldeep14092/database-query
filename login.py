import gradio as gr
import mysql.connector
import pandas as pd

# Database Configuration
DB_CONFIG = {
    "host": "192.170.1.181",
    "user": "rao",  
    "password": "rao123",  
    "database": "test",  
}

# User Authentication Data
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

# Global variable to store logged-in user
current_user = {"username": None, "role": None}

# Function to Get Tables from Database
def get_table_names():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        conn.close()
        print(tables)
        return tables
    except mysql.connector.Error:
        print("e")
        return []

# Function to Execute SQL Queries
def execute_query(query):
    if not current_user["role"]:
        return gr.update(value="❌ Access Denied! Please log in.", visible=True), None

    query = query.strip()

    # Prevent dangerous queries
    if any(word in query.lower() for word in ["drop", "alter", "truncate"]):
        return gr.update(value="⚠️ Unsafe query detected!", visible=True), None

    # Users can only execute SELECT queries
    if current_user["role"] == "User" and not query.lower().startswith("select"):
        return gr.update(value="⚠️ Access Denied! Users can only execute SELECT queries.", visible=True), None

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)

        # Handle SELECT query
        if query.lower().startswith("select"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cursor.close()
            conn.close()

            if not rows:
                return gr.update(value="✅ Query executed successfully, but no results found.", visible=True), None

            df = pd.DataFrame(rows, columns=columns)
            return gr.update(value="✅ Query executed successfully!", visible=True), df

        # Handle INSERT, UPDATE, DELETE queries (Admin only)
        elif query.lower().startswith(("insert", "update", "delete")):
            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return gr.update(value=f"✅ Query executed successfully! Affected rows: {affected_rows}", visible=True), None

    except mysql.connector.ProgrammingError as pe:
        return gr.update(value=f"❌ SQL Syntax Error: {pe}", visible=True), None
    except mysql.connector.Error as e:
        return gr.update(value=f"❌ Database error: {e}", visible=True), None

# Function to Display Table Data
def display_table_data(table_name):
    if not current_user["role"] == "Admin":
        return gr.update(value="❌ Access Denied! Only Admins can view table data.", visible=True), None

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        conn.close()

        if not rows:
            return gr.update(value=f"✅ Table '{table_name}' is empty.", visible=True), None

        df = pd.DataFrame(rows, columns=columns)
        return gr.update(value=f"✅ Data from table '{table_name}' loaded successfully!", visible=True), df

    except mysql.connector.Error as e:
        return gr.update(value=f"❌ Database error: {e}", visible=True), None

# Authentication Function
def login(username, password):
    global current_user
    user_data = USERS.get(username)

    if user_data and user_data["password"] == password:
        current_user["username"] = username
        current_user["role"] = user_data["role"]

        tables = get_table_names()  # Fetch tables after login
        dashboard_text = "👑 **Admin Dashboard**" if user_data["role"] == "Admin" else "👤 **User Dashboard**"

        return (
            gr.update(value=f"✅ Welcome, {username}! You have **{user_data['role']} Access**.", visible=True),
            gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
            gr.update(visible=True), gr.update(visible=True, value=dashboard_text),  
            gr.update(visible=True), gr.update(visible=True),  
            gr.update(visible=True), gr.update(visible=True),  
            gr.update(choices=tables, value=tables[0] if tables else None, visible=user_data["role"] == "Admin")  # ✅ Fix Here
        )

    return (
        gr.update(value="❌ Incorrect username or password!", visible=True), 
        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False)  # ✅ Ensure we return exactly 12 values
    )


# Logout Function
def logout():
    global current_user
    current_user = {"username": None, "role": None}

    return (
        gr.update(value="✅ You have been logged out successfully!", visible=True),
        gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False)
    )

# Gradio UI
with gr.Blocks() as app:
    login_heading = gr.Markdown("## 🔒 Login Page")  

    with gr.Row():
        username = gr.Textbox(label="Username", placeholder="Enter username")
        password = gr.Textbox(label="Password", type="password", placeholder="Enter password")

    login_btn = gr.Button("Login")
    error_message = gr.Markdown("", visible=False)  

    dashboard_heading = gr.Markdown("", visible=False)  
    query_input = gr.Textbox(label="Enter SQL Query (Only SELECT for Users)", visible=False)
    output_table = gr.Dataframe(visible=False)
    execute_btn = gr.Button("Run Query", visible=False)

    logout_btn = gr.Button("Logout", visible=False)

    admin_form_heading = gr.Markdown("### 🛠 Admin Update Form", visible=False)
    select_table = gr.Dropdown(label="Select Table", choices=[], visible=False)
    load_table_btn = gr.Button("Load Table Data", visible=False)

    login_btn.click(
        login, 
        inputs=[username, password], 
        outputs=[
            error_message, login_heading, username, password, login_btn, logout_btn, 
            dashboard_heading, query_input, execute_btn, output_table, 
            admin_form_heading, select_table
        ]
    )

    execute_btn.click(
        execute_query, 
        inputs=[query_input], 
        outputs=[error_message, output_table]
    )

    load_table_btn.click(
        display_table_data,
        inputs=[select_table],
        outputs=[error_message, output_table]
    )

    logout_btn.click(
        logout,     
        outputs=[
            error_message, login_heading, username, password, login_btn, 
            logout_btn, dashboard_heading, 
            query_input, execute_btn, output_table, 
            admin_form_heading, select_table
        ]
    )

app.launch()