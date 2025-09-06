import krpc
import kRPC_Tools as tools
import time
import os
import matplotlib.pyplot as plt

    # print( "╔══════════════════════════════════════════")
    # print( "║     Système de régulation PID            ")
    # print( "╠══════════════════════════════════════════")

def afficher_tableau_ligne(q, throttle, integral):
    print("\033[H", end='')  # Replace curseur en haut
    print( "-------------------------------------------")
    print( "|     Système de régulation PID            ")
    print( "-------------------------------------------")
    print(f"| Q dynamique   : {q:>10.0f} Pa            ")
    print(f"| Gaz           : {throttle*100:>10.1f} %  ")
    print(f"| Integral      : {integral:>10.0f}        ")




# === Nettoyage du terminal et préparation de l'affichage ===
os.system('cls')
print('\033[?25l', end='', flush=True)  # Cacher le curseur

# === Connexion à KSP ===
print("Connexion à KSP via kRPC...")
conn = krpc.connect(name='SubOrbiter3')
vessel = conn.space_center.active_vessel
print("Connecté à KSP :", conn.krpc.get_status().version, "\n")

# === Affichage des infos ===
print(f"Vaisseau actif : {vessel.name}")
print(f"Kerbals à bord : {[kerbal.name for kerbal in vessel.crew]}")
print("\nPréparation au lancement...\n")

# === Préparation du vol ===
dynamic_pressure = conn.add_stream(getattr, vessel.flight(), 'dynamic_pressure')
vessel.control.throttle = 1.0
vessel.auto_pilot.disengage()
vessel.control.sas = True
vessel.control.sas_mode = vessel.control.sas_mode.stability_assist

print("🟢 SAS activé")
print("🚀 Prêt pour le lancement !")
print("Début du comptage à rebours...")
tools.countdown(1)
vessel.control.activate_next_stage()

# === PID pour régulation de la pression dynamique ===
# 20 kPa kcrit = 0.004 ; Pcrit = 22.74 - 22.37 = 0.37 s
thrust_pid = tools.PID(kp=0.002, ki=0, kd=0.0, setpoint=20000, min_output=0, max_output=1)
# thrust_pid = tools.PID(kp=0.0024, ki=0.013, kd=0.0002, setpoint=20000)

# === Logs pour le graphique ===
time_log = []
throttle_log = []
q_log = []
start_time = time.time()

# === Boucle principale ===
print("\033[2J\033[H", end='')  # Nettoie tout au départ + replace curseur en haut

try:
    while True:
        current_q = dynamic_pressure()
        dt = 0.05
        elapsed = time.time() - start_time

        # PID
        throttle_output = thrust_pid.update(current_q, dt)
        vessel.control.throttle = max(0.0, min(1.0, throttle_output))

        # Log pour le graphique
        time_log.append(elapsed)
        throttle_log.append(vessel.control.throttle)
        q_log.append(current_q)

        # Affichage propre en ligne
        error = thrust_pid.setpoint - current_q
        afficher_tableau_ligne(current_q, vessel.control.throttle, thrust_pid.integral)


        # print(f"Q: {current_q:>7.1f} Pa | Gaz: {vessel.control.throttle:.2f}    ", end='\r', flush=True)

        time.sleep(dt)

except KeyboardInterrupt:
    # Réafficher le curseur proprement
    print('\033[?25h', end='', flush=True)
    print("\nArrêt du PID. Affichage du graphique...\n")

    # === Affichage du graphique ===
    plt.figure(figsize=(10, 5))
    plt.plot(time_log, throttle_log, label='Poussée (Throttle)', color='orange')
    plt.plot(time_log, [q / 1000 for q in q_log], label='Pression dynamique (kPa)', color='blue', linestyle='--')
    plt.axhline(20, color='blue', linestyle=':', label='Cible q̇ = 20 kPa')

    plt.xlabel("Temps (s)")
    plt.ylabel("Valeurs")
    plt.title("Évolution de la poussée et de la pression dynamique")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()