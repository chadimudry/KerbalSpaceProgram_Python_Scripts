import krpc
import kRPC_Tools as tools
import time
import os
import matplotlib.pyplot as plt
import sys

def center_colored_text(text, color_code, total_width):
    raw_len = len(text)
    padding = max(0, total_width - raw_len)
    left = padding // 2
    right = padding - left
    return " " * left + f"{color_code}{text}{RESET}" + " " * right

# ANSI styles
BOLD = "\033[1m"
RESET = "\033[0m"
BLUE = "\033[94m"

inside_width = 36
title_text = "Système de régulation PID"

def pad(content, width):
    return content.ljust(width)

def afficher_lignes(q, throttle):
    print("\033[H", end='')  # Curseur en haut

    print( "┌────────────────────────────────────┐")
    print(f"│{center_colored_text(title_text, BOLD + BLUE, inside_width)}│")
    print( "├────────────────────────────────────┤")
    print(f"│ {pad(f'Q dynamique : {q:>10.0f} Pa', 35)}│")
    print(f"│ {pad(f'Gaz         : {throttle*100:>10.0f} %', 35)}│")
    print( "└────────────────────────────────────┘")
    sys.stdout.flush()


# === Initialisation ===
os.system('cls' if os.name == 'nt' else 'clear')
print('\033[?25l', end='')  # Cacher le curseur
print("\033[2J", end='')    # Effacer tout
print("\033[H", end='')     # Curseur en haut

conn = krpc.connect(name='SubOrbiter3')
vessel = conn.space_center.active_vessel
dynamic_pressure = conn.add_stream(getattr, vessel.flight(), 'dynamic_pressure')

thrust_pid = tools.PID(kp=0.002, ki=0, kd=0.0, setpoint=20000, min_output=0, max_output=1)

# Logs
time_log = []
throttle_log = []
q_log = []
start_time = time.time()

# === Affichage initial ===
for _ in range(6): print()

try:
    while True:
        current_q = dynamic_pressure()
        dt = 0.05
        elapsed = time.time() - start_time

        # PID
        throttle_output = thrust_pid.update(current_q, dt)
        vessel.control.throttle = max(0.0, min(1.0, throttle_output))

        # Logs
        time_log.append(elapsed)
        throttle_log.append(vessel.control.throttle)
        q_log.append(current_q)

        error = thrust_pid.setpoint - current_q
        afficher_lignes(current_q, vessel.control.throttle)

        time.sleep(dt)

except KeyboardInterrupt:
    print('\033[?25h', end='')  # Réaffiche le curseur
    print("\nArrêt du PID.\n")