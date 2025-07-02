import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import csv
from typing import Dict, List

# Configuration
COLORS = {
    'primary': '#002a5c',
    'secondary': '#004b8e', 
    'accent': '#005dab',
    'highlight': '#017dc3'
}

USERS = {
    'jproano': {'password': 'leader123', 'role': 'Team Leader', 'permissions': ['view', 'create', 'edit', 'delete', 'assign']},
    'vpacheco': {'password': 'member123', 'role': 'Team Member', 'permissions': ['view', 'create', 'edit_own']},
    'dguerra': {'password': 'member123', 'role': 'Team Member', 'permissions': ['view', 'create', 'edit_own']}
}

# CSV file path
TASKS_CSV_FILE = 'team_tasks.csv'

# CSV Functions
def load_tasks_from_csv():
    """Load tasks from CSV file"""
    try:
        if os.path.exists(TASKS_CSV_FILE):
            df = pd.read_csv(TASKS_CSV_FILE)
            if not df.empty:
                # Convert DataFrame back to list of dictionaries
                tasks = df.to_dict('records')
                # Convert string tags back to list
                for task in tasks:
                    if 'tags' in task and pd.notna(task['tags']):
                        task['tags'] = eval(task['tags']) if task['tags'].startswith('[') else [task['tags']]
                    else:
                        task['tags'] = []
                return tasks
    except Exception as e:
        st.error(f"Error loading tasks from CSV: {str(e)}")
    return []

def save_tasks_to_csv():
    """Save tasks to CSV file"""
    try:
        if st.session_state.tasks:
            # Convert tasks to DataFrame
            df_tasks = pd.DataFrame(st.session_state.tasks)
            # Convert tags list to string for CSV storage
            df_tasks['tags'] = df_tasks['tags'].apply(lambda x: str(x) if x else '[]')
            # Save to CSV
            df_tasks.to_csv(TASKS_CSV_FILE, index=False)
            return True
    except Exception as e:
        st.error(f"Error saving tasks to CSV: {str(e)}")
    return False

def backup_csv():
    """Create a backup of the CSV file with timestamp"""
    try:
        if os.path.exists(TASKS_CSV_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"team_tasks_backup_{timestamp}.csv"
            df = pd.read_csv(TASKS_CSV_FILE)
            df.to_csv(backup_name, index=False)
            return backup_name
    except Exception as e:
        st.error(f"Error creating backup: {str(e)}")
    return None

# Initialize session state
def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'tasks' not in st.session_state:
        # Load tasks from CSV on initialization
        st.session_state.tasks = load_tasks_from_csv()
    if 'projects' not in st.session_state:
        st.session_state.projects = []

# Authentication
def authenticate_user(username: str, password: str) -> bool:
    if username in USERS and USERS[username]['password'] == password:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.user_role = USERS[username]['role']
        st.session_state.permissions = USERS[username]['permissions']
        return True
    return False

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.permissions = None

# Task Management Functions
def add_task(task_data: Dict):
    task_data['id'] = len(st.session_state.tasks) + 1
    task_data['created_by'] = st.session_state.username
    task_data['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    task_data['updated_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    st.session_state.tasks.append(task_data)
    # Save to CSV after adding
    save_tasks_to_csv()

def update_task(task_id: int, updated_data: Dict):
    for i, task in enumerate(st.session_state.tasks):
        if task['id'] == task_id:
            updated_data['updated_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            st.session_state.tasks[i].update(updated_data)
            # Save to CSV after updating
            save_tasks_to_csv()
            break

def delete_task(task_id: int):
    st.session_state.tasks = [task for task in st.session_state.tasks if task['id'] != task_id]
    # Save to CSV after deleting
    save_tasks_to_csv()

def get_user_tasks(username: str) -> List[Dict]:
    return [task for task in st.session_state.tasks if task['assigned_to'] == username or task['created_by'] == username]

# Dashboard Functions
def create_gantt_chart():
    if not st.session_state.tasks:
        return None
    
    df_tasks = pd.DataFrame(st.session_state.tasks)
    
    # Prepare data for Gantt chart
    gantt_data = []
    for _, task in df_tasks.iterrows():
        start_date = datetime.strptime(task['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(task['end_date'], '%Y-%m-%d')
        
        gantt_data.append({
            'Task': task['title'],
            'Start': start_date,
            'Finish': end_date,
            'Resource': task['assigned_to'],
            'Status': task['status'],
            'Priority': task['priority']
        })
    
    df_gantt = pd.DataFrame(gantt_data)
    
    # Create Gantt chart
    fig = px.timeline(
        df_gantt, 
        x_start="Start", 
        x_end="Finish", 
        y="Task",
        color="Status",
        color_discrete_map={
            'Not Started': COLORS['primary'],
            'In Progress': COLORS['highlight'], 
            'Completed': COLORS['accent'],
            'On Hold': COLORS['secondary']
        },
        title="Project Timeline - Gantt Chart"
    )
    
    fig.update_layout(
        height=400,
        showlegend=True,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_progress_summary():
    if not st.session_state.tasks:
        return None, None, None
    
    df = pd.DataFrame(st.session_state.tasks)
    
    # Status distribution
    status_counts = df['status'].value_counts()
    fig_status = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        title="Task Status Distribution",
        color_discrete_sequence=[COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['highlight']]
    )
    
    # Priority distribution
    priority_counts = df['priority'].value_counts()
    fig_priority = px.bar(
        x=priority_counts.index,
        y=priority_counts.values,
        title="Tasks by Priority",
        color=priority_counts.values,
        color_continuous_scale=[[0, COLORS['primary']], [1, COLORS['highlight']]]
    )
    
    # Team workload
    workload = df['assigned_to'].value_counts()
    fig_workload = px.bar(
        x=workload.index,
        y=workload.values,
        title="Team Workload Distribution",
        color=workload.values,
        color_continuous_scale=[[0, COLORS['secondary']], [1, COLORS['accent']]]
    )
    
    return fig_status, fig_priority, fig_workload

# UI Components
def login_page():
    st.markdown(f"""
    <div style="text-align: center; padding: 50px;">
        <h1 style="color: {COLORS['primary']};">Team Task Manager</h1>
        <p style="color: {COLORS['secondary']};">Please login to access the dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if authenticate_user(username, password):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

def dashboard_page():
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['secondary']}); 
                padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0;">📊 Team Dashboard</h1>
        <p style="color: white; margin: 5px 0;">Welcome back, {st.session_state.user_role}: {st.session_state.username}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key Metrics
    total_tasks = len(st.session_state.tasks)
    completed_tasks = len([t for t in st.session_state.tasks if t['status'] == 'Completed'])
    in_progress = len([t for t in st.session_state.tasks if t['status'] == 'In Progress'])
    overdue_tasks = len([t for t in st.session_state.tasks 
                        if datetime.strptime(t['end_date'], '%Y-%m-%d') < datetime.now() 
                        and t['status'] != 'Completed'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📋 Total Tasks",
            value=total_tasks,
            delta=f"+{len([t for t in st.session_state.tasks if t['created_date'].startswith(datetime.now().strftime('%Y-%m-%d'))])}"
        )
    
    with col2:
        st.metric(
            label="✅ Completed",
            value=completed_tasks,
            delta=f"{(completed_tasks/total_tasks*100):.1f}%" if total_tasks > 0 else "0%"
        )
    
    with col3:
        st.metric(
            label="🔄 In Progress",
            value=in_progress
        )
    
    with col4:
        st.metric(
            label="⚠️ Overdue",
            value=overdue_tasks,
            delta="Critical" if overdue_tasks > 0 else "None"
        )
    
    # Charts
    if st.session_state.tasks:
        st.subheader("📈 Progress Analytics")
        
        fig_status, fig_priority, fig_workload = create_progress_summary()
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_status, use_container_width=True)
        with col2:
            st.plotly_chart(fig_priority, use_container_width=True)
        
        st.plotly_chart(fig_workload, use_container_width=True)
        
        # Gantt Chart
        st.subheader("📅 Project Timeline")
        gantt_fig = create_gantt_chart()
        if gantt_fig:
            st.plotly_chart(gantt_fig, use_container_width=True)
        
        # Recent Tasks Table
        st.subheader("📝 Recent Tasks")
        df_display = pd.DataFrame(st.session_state.tasks)
        if not df_display.empty:
            df_display = df_display[['title', 'assigned_to', 'status', 'priority', 'end_date', 'progress', 'created_date', 'updated_date']]
            # Sort by most recently updated
            df_display = df_display.sort_values('updated_date', ascending=False) if 'updated_date' in df_display.columns else df_display
            st.dataframe(df_display, use_container_width=True)
            
            # CSV export info
            st.info(f"💾 All tasks are automatically saved to '{TASKS_CSV_FILE}' - Total tasks: {len(st.session_state.tasks)}")
    else:
        st.info("No tasks available. Create your first task in the Task Management section!")
        st.info("💡 Tasks will be automatically saved to CSV file for persistence.")

def task_management_page():
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, {COLORS['accent']}, {COLORS['highlight']}); 
                padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0;">📋 Task Management</h1>
        <p style="color: white; margin: 5px 0;">Create, edit, and manage tasks</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["➕ Create Task", "📝 Edit Tasks", "👥 My Tasks"])
    
    with tab1:
        st.subheader("Create New Task")
        
        with st.form("create_task_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Task Title *")
                assigned_to = st.selectbox("Assign To *", list(USERS.keys()))
                priority = st.selectbox("Priority *", ["Low", "Medium", "High", "Critical"])
                start_date = st.date_input("Start Date *", datetime.now())
            
            with col2:
                project = st.text_input("Project Name")
                status = st.selectbox("Status *", ["Not Started", "In Progress", "On Hold", "Completed"])
                end_date = st.date_input("End Date *", datetime.now() + timedelta(days=7))
                progress = st.slider("Progress (%)", 0, 100, 0)
            
            description = st.text_area("Description")
            tags = st.text_input("Tags (comma-separated)")
            
            submit = st.form_submit_button("Create Task", use_container_width=True)
            
            if submit:
                if title and assigned_to and priority and status:
                    task_data = {
                        'title': title,
                        'description': description,
                        'assigned_to': assigned_to,
                        'priority': priority,
                        'status': status,
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'progress': progress,
                        'project': project,
                        'tags': [tag.strip() for tag in tags.split(',') if tag.strip()]
                    }
                    add_task(task_data)
                    st.success("Task created successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields marked with *")
    
    with tab2:
        if 'delete' in st.session_state.permissions or 'edit' in st.session_state.permissions:
            st.subheader("Edit Existing Tasks")
            
            if st.session_state.tasks:
                task_options = {f"#{task['id']} - {task['title']}": task['id'] 
                              for task in st.session_state.tasks}
                
                selected_task_key = st.selectbox("Select Task to Edit", list(task_options.keys()))
                
                if selected_task_key:
                    task_id = task_options[selected_task_key]
                    task = next(task for task in st.session_state.tasks if task['id'] == task_id)
                    
                    # Check permissions
                    can_edit = ('edit' in st.session_state.permissions or 
                              ('edit_own' in st.session_state.permissions and 
                               task['created_by'] == st.session_state.username))
                    
                    if can_edit:
                        with st.form(f"edit_task_{task_id}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_title = st.text_input("Title", task['title'])
                                new_assigned = st.selectbox("Assigned To", list(USERS.keys()), 
                                                          index=list(USERS.keys()).index(task['assigned_to']))
                                new_priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"],
                                                           index=["Low", "Medium", "High", "Critical"].index(task['priority']))
                                new_start = st.date_input("Start Date", 
                                                         datetime.strptime(task['start_date'], '%Y-%m-%d'))
                            
                            with col2:
                                new_project = st.text_input("Project", task.get('project', ''))
                                new_status = st.selectbox("Status", ["Not Started", "In Progress", "On Hold", "Completed"],
                                                         index=["Not Started", "In Progress", "On Hold", "Completed"].index(task['status']))
                                new_end = st.date_input("End Date", 
                                                       datetime.strptime(task['end_date'], '%Y-%m-%d'))
                                new_progress = st.slider("Progress (%)", 0, 100, task['progress'])
                            
                            new_description = st.text_area("Description", task.get('description', ''))
                            
                            col_update, col_delete = st.columns(2)
                            
                            with col_update:
                                update = st.form_submit_button("Update Task", use_container_width=True)
                            
                            with col_delete:
                                delete = st.form_submit_button("Delete Task", use_container_width=True, 
                                                             type="secondary") if 'delete' in st.session_state.permissions else None
                            
                            if update:
                                updated_data = {
                                    'title': new_title,
                                    'description': new_description,
                                    'assigned_to': new_assigned,
                                    'priority': new_priority,
                                    'status': new_status,
                                    'start_date': new_start.strftime('%Y-%m-%d'),
                                    'end_date': new_end.strftime('%Y-%m-%d'),
                                    'progress': new_progress,
                                    'project': new_project
                                }
                                update_task(task_id, updated_data)
                                st.success("Task updated successfully!")
                                st.rerun()
                            
                            if delete and 'delete' in st.session_state.permissions:
                                delete_task(task_id)
                                st.success("Task deleted successfully!")
                                st.rerun()
                    else:
                        st.warning("You don't have permission to edit this task.")
            else:
                st.info("No tasks available to edit.")
        else:
            st.warning("You don't have permission to edit tasks.")
    
    with tab3:
        st.subheader("My Tasks")
        
        # For team leader, show all tasks; for members, show only their tasks
        if st.session_state.user_role == "Team Leader":
            display_tasks = st.session_state.tasks
            st.info("As Team Leader, you can see all team tasks here.")
        else:
            display_tasks = get_user_tasks(st.session_state.username)
        
        if display_tasks:
            for task in display_tasks:
                # Enhanced card display for team leader
                if st.session_state.user_role == "Team Leader":
                    with st.expander(f"#{task['id']} - {task['title']} | Status: {task['status']} | Responsible: {task['assigned_to']}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Priority:** {task['priority']}")
                            st.write(f"**Assigned to:** {task['assigned_to']}")
                            st.write(f"**Project:** {task.get('project', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Status:** {task['status']}")
                            st.write(f"**Start Date:** {task['start_date']}")
                            st.write(f"**End Date:** {task['end_date']}")
                        
                        with col3:
                            st.write(f"**Progress:** {task['progress']}%")
                            st.write(f"**Created by:** {task['created_by']}")
                            st.write(f"**Created on:** {task['created_date']}")
                        
                        if task.get('description'):
                            st.write(f"**Description:** {task['description']}")
                        
                        # Progress bar
                        st.progress(task['progress'] / 100)
                else:
                    # Standard display for team members
                    with st.expander(f"#{task['id']} - {task['title']} ({task['status']})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Priority:** {task['priority']}")
                            st.write(f"**Assigned to:** {task['assigned_to']}")
                            st.write(f"**Project:** {task.get('project', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Start Date:** {task['start_date']}")
                            st.write(f"**End Date:** {task['end_date']}")
                            st.write(f"**Progress:** {task['progress']}%")
                        
                        if task.get('description'):
                            st.write(f"**Description:** {task['description']}")
                        
                        # Progress bar
                        st.progress(task['progress'] / 100)
        else:
            if st.session_state.user_role == "Team Leader":
                st.info("No tasks available in the system yet.")
            else:
                st.info("No tasks assigned to you yet.")

def main():
    # Page config
    st.set_page_config(
        page_title="Team Task Manager",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown(f"""
    <style>
        * {{
            font-family: Arial, sans-serif !important;
        }}
        .stApp {{
            background-color: #f8f9fa;
            font-family: Arial, sans-serif !important;
        }}
        .metric-card {{
            background: white;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid {COLORS['primary']};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: Arial, sans-serif !important;
        }}
        .stButton > button {{
            background-color: {COLORS['primary']};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            font-family: Arial, sans-serif !important;
        }}
        .stButton > button:hover {{
            background-color: {COLORS['secondary']};
        }}
        .stSelectbox > div > div > div {{
            font-family: Arial, sans-serif !important;
        }}
        .stTextInput > div > div > input {{
            font-family: Arial, sans-serif !important;
        }}
        .stTextArea > div > div > textarea {{
            font-family: Arial, sans-serif !important;
        }}
        .stMarkdown, .stMarkdown * {{
            font-family: Arial, sans-serif !important;
        }}
        .stDataFrame {{
            font-family: Arial, sans-serif !important;
        }}
        h1, h2, h3, h4, h5, h6 {{
            font-family: Arial, sans-serif !important;
        }}
        p, span, div {{
            font-family: Arial, sans-serif !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        # Sidebar
        with st.sidebar:
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; background: {COLORS['primary']}; 
                        border-radius: 10px; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0;">👤 {st.session_state.username}</h3>
                <p style="color: white; margin: 5px 0;">{st.session_state.user_role}</p>
            </div>
            """, unsafe_allow_html=True)
            
            page = st.radio(
                "Navigation",
                ["📊 Dashboard", "📋 Task Management"],
                key="navigation"
            )
            
            st.markdown("---")
            
            if st.button("🚪 Logout", use_container_width=True):
                logout()
                st.rerun()
            
            # Quick Stats in Sidebar
            if st.session_state.tasks:
                st.markdown("### 📈 Quick Stats")
                my_tasks = len(get_user_tasks(st.session_state.username))
                st.metric("My Tasks", my_tasks)
                
                completed_today = len([t for t in st.session_state.tasks 
                                     if t['status'] == 'Completed' and 
                                     t.get('updated_date', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
                st.metric("Completed Today", completed_today)
                
                # CSV info
                st.markdown("---")
                st.markdown("### 💾 Data Storage")
                if os.path.exists(TASKS_CSV_FILE):
                    file_size = os.path.getsize(TASKS_CSV_FILE)
                    st.write(f"📁 CSV File: {file_size} bytes")
                    
                    # Download CSV button
                    with open(TASKS_CSV_FILE, 'r') as f:
                        csv_data = f.read()
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"team_tasks_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # Backup button (only for team leader)
                    if st.session_state.user_role == "Team Leader":
                        if st.button("🔄 Create Backup", use_container_width=True):
                            backup_file = backup_csv()
                            if backup_file:
                                st.success(f"Backup created: {backup_file}")
                else:
                    st.write("📁 No CSV file yet")
        
        # Main content
        if page == "📊 Dashboard":
            dashboard_page()
        elif page == "📋 Task Management":
            task_management_page()

if __name__ == "__main__":
    main()
