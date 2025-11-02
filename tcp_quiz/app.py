# app.py
"""
Streamlit UI for the quiz. Uses tcp_client module for networking.
- Call 'Join Server' (sidebar) to start the local tcp_client (persistent).
- The UI polls tcp_client.get_state() each rerun and renders the present state.
- When answering, the UI calls tcp_client.send_answer(answer).
"""

import streamlit as st
import time
import client  # our module above

st.set_page_config(page_title="QuizNet (TCP)", layout="centered")
st.title("🎮 QuizNet (UI)")

# Sidebar controls
st.sidebar.header("Connection")
username = st.sidebar.text_input("Username", value=client.get_state().get("username", ""))
if st.sidebar.button("Join Server"):
    if not username.strip():
        st.sidebar.error("Please enter a username.")
    else:
        ok = client.start_client(username.strip())
        if ok:
            st.sidebar.success(f"Connected as {username.strip()}")
        else:
            st.sidebar.error("Failed to connect to server. Check server is running.")

if st.sidebar.button("Disconnect"):
    client.stop_client()
    st.rerun()

# Get snapshot state from tcp_client
state = client.get_state()

# Show connection status
if not state["connected"]:
    st.warning("🔌 Not connected. Join the server from the sidebar.")
    if state["messages"]:
        st.subheader("Recent messages")
        for m in state["messages"][-10:]:
            st.write(m)
    # refresh slowly so user can click join
    time.sleep(1)
    st.rerun()
else:
    st.sidebar.write(f"👤 You: **{state['username']}**")
    st.sidebar.write(f"🎯 Score: **{state['score']}**")
    st.sidebar.markdown("---")

# Show messages
if state["messages"]:
    st.subheader("Messages")
    for msg in state["messages"][-5:]:
        st.write(msg)

# Waiting for host
if not state["game_started"] and not state["game_over"]:
    st.info("⏳ Waiting for host to start the quiz...")
    # lightweight refresh loop while waiting
    time.sleep(1.5)
    st.rerun()

# Game active
if state["game_started"] and not state["game_over"]:
    st.subheader("❓ Question")
    st.write(f"**{state['question']}**")
    opts = state["options"] or []
    if not opts:
        st.write("_No options available yet._")
    else:
        cols = st.columns(len(opts))
        for i, opt in enumerate(opts):
            if cols[i].button(opt):
                # send answer via tcp_client
                ok = client.send_answer(opt)
                if not ok:
                    st.error("Failed to send answer (not connected).")
                else:
                    st.success(f"Sent answer: {opt}")
    if state["feedback"]:
        st.info(state["feedback"])

# Live leaderboard (main area)
if state["leaderboard"]:
    st.subheader("🏅 Live Leaderboard")
    sorted_lb = sorted(state["leaderboard"].items(), key=lambda x: x[1], reverse=True)
    for user, pts in sorted_lb:
        if user == state["username"]:
            st.markdown(f"**{user}: {pts} pts**")
        else:
            st.write(f"{user}: {pts} pts")

# Game over screen
if state["game_over"]:
    st.success("🏁 Quiz Over")
    st.subheader("🏆 Final Leaderboard")
    sorted_lb = sorted(state["leaderboard"].items(), key=lambda x: x[1], reverse=True)
    for user, pts in sorted_lb:
        st.write(f"{user}: {pts} pts")
    if state["messages"]:
        st.write("---")
        for m in state["messages"]:
            st.write(m)

# Small auto-refresh so UI updates as tcp_client updates state
time.sleep(1.0)
st.rerun()
