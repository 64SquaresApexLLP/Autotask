import streamlit as st

# Hardcoded credentials from my-progress.md
USERS = {
    'U001': {'name': 'User1', 'password': 'Pass@001'},
    'U002': {'name': 'User2', 'password': 'Pass@002'},
    'U003': {'name': 'User3', 'password': 'Pass@003'},
    'U004': {'name': 'User4', 'password': 'Pass@004'},
}
TECHNICIANS = {
    'T101': {'name': 'Technician1', 'password': 'Tech@9382xB'},
    'T102': {'name': 'Technician2', 'password': 'Tech@4356vL'},
    'T103': {'name': 'Technician3', 'password': 'Tech@6439yZ'},
    'T104': {'name': 'Technician4', 'password': 'Tech@2908aF'},
}

def login_page():
    st.set_page_config(page_title="Login", page_icon="🔑", layout="centered")
    st.title("🔐 Login Portal")
    tab1, tab2 = st.tabs(["User Login", "Technician Login"])
    with tab1:
        st.subheader("User Login")
        user_id = st.text_input("User ID", key="user_id")
        user_pw = st.text_input("Password", type="password", key="user_pw")
        if st.button("Login as User", key="login_user_btn"):
            if user_id in USERS and USERS[user_id]['password'] == user_pw:
                st.session_state['user'] = {'id': user_id, 'name': USERS[user_id]['name']}
                st.session_state['role'] = 'user'
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid User ID or Password.")
    with tab2:
        st.subheader("Technician Login")
        tech_id = st.text_input("Technician ID", key="tech_id")
        tech_pw = st.text_input("Password", type="password", key="tech_pw")
        if st.button("Login as Technician", key="login_tech_btn"):
            if tech_id in TECHNICIANS and TECHNICIANS[tech_id]['password'] == tech_pw:
                st.session_state['technician'] = {'id': tech_id, 'name': TECHNICIANS[tech_id]['name']}
                st.session_state['role'] = 'technician'
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid Technician ID or Password.")

if __name__ == "__main__":
    login_page() 