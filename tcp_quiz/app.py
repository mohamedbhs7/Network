import streamlit as st
import socket
import time

# ----------------------- Server Configuration -----------------------
HOST = "192.168.54.220"   # IP of TCP server
PORT = 8888               # Port server listens on

# ----------------------- Initialize session state variables -----------------------
for key in ["client", "question", "options", "score", "game_over", "messages", "game_started"]:
    if key not in st.session_state:
        if key == "client":
            st.session_state[key] = None
        elif key == "messages":
            st.session_state[key] = []
        elif key == "score":
            st.session_state[key] = 0
        elif key == "game_over":
            st.session_state[key] = False
        elif key == "game_started":
            st.session_state[key] = False          # ✅ New state
        else:
            st.session_state[key] = ""

# ----------------------- App Title -----------------------
st.title("🎮 QuizNet Kahoot Game")

# ----------------------- Connect to the Server -----------------------
if not st.session_state.client:
    username = st.text_input("Enter your username:")
    if st.button("Join Server") and username:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(0.1)
            client.connect((HOST, PORT))
            client.sendall(f"join:{username}".encode())
            st.session_state.client = client
            st.success(f"✅ Connected to server as {username}")
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")

# ----------------------- Receive Data from Server -----------------------
if st.session_state.client and not st.session_state.game_over:
    client = st.session_state.client
    try:
        while True:
            try:
                data = client.recv(1024).decode()
            except socket.timeout:
                break

            if not data:
                break

            # ✅ Host started the game
            if data.startswith("start_game"):
                st.session_state.game_started = True

            elif data.startswith("question:") and st.session_state.game_started:
                qdata = data.replace("question:", "")
                q, opts = qdata.split("|", 1)
                st.session_state.question = q
                st.session_state.options = opts.split("|")

            elif data.startswith("score:"):
                st.session_state.score = int(data.replace("score:", ""))

            elif data.startswith("quiz_over:"):
                st.session_state.game_over = True
                st.session_state.messages.append(data.replace("quiz_over:", ""))

    except:
        st.warning("⚠ Connection lost or server not responding.")

# ----------------------- Display Before Game Starts -----------------------
if not st.session_state.game_started:
    st.warning("⏳ Waiting for the host to start the quiz...")
else:
    # ----------------------- Display Question and Options -----------------------
    if st.session_state.question and st.session_state.options:
        st.info(f"❓ **{st.session_state.question}**")
        cols = st.columns(len(st.session_state.options))
        for i, opt in enumerate(st.session_state.options):
            if cols[i].button(opt):
                try:
                    st.session_state.client.sendall(opt.encode())
                    st.success(f"✅ Answer '{opt}' sent!")
                    st.session_state.question = ""
                    st.session_state.options = []
                except:
                    st.error("❌ Failed to send answer.")

# ----------------------- Display Score and End Messages -----------------------
st.write(f"🏆 **Current Score:** {st.session_state.score}")
for msg in st.session_state.messages:
    st.success(msg)

# ----------------------- Auto Refresh Every 2 Seconds -----------------------
time.sleep(2)
st.rerun()
