import krpc
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Connexion au serveur kRPC
print("Connexion à KSP via kRPC...")
conn = krpc.connect(name="Altitude Tracker")
vessel = conn.space_center.active_vessel
print("Connexion établie ! Suivi de l'altitude du vaisseau en cours...\n")

# Variables pour stocker les données
time_data = []  # Temps écoulé
altitude_data = []  # Altitude par rapport au niveau de la mer

# Initialiser le temps de référence
start_time = time.time()

vessel.control.throttle = 1
vessel.control.sas = True
vessel.control.activate_next_stage()

# Configuration du graphique avec matplotlib
# plt.style.use('seaborn')         # Style par défaut de Seaborn
# plt.style.use('ggplot')          # Inspiré de ggplot2 (R)
# plt.style.use('classic')         # Style classique de Matplotlib
# plt.style.use('Solarize_Light2') # Style clair et épuré
# plt.style.use('bmh')             # Style simple et efficace
# plt.style.use('fivethirtyeight') # Style du site 538
# plt.style.use('dark_background') # Fond noir avec courbes lumineuses

fig, ax = plt.subplots()
line, = ax.plot([], [], label="Altitude (m)", color='tab:red')
ax.set_title("Évolution de l'altitude en temps réel")
ax.set_xlabel("Temps (s)")
ax.set_ylabel("Altitude (m)")
ax.legend()
plt.grid(axis='y')

# Fonction pour initialiser le graphique
def init():
    line.set_data([], [])
    return line,

# Fonction qui met à jour les données du graphique
def update(frame):
    # Récupérer le temps et l'altitude
    current_time = time.time() - start_time
    altitude = vessel.flight().mean_altitude  # Altitude par rapport au niveau de la mer

    # Ajouter les données
    time_data.append(current_time)
    altitude_data.append(altitude)

    # Mettre à jour les données de la ligne
    line.set_data(time_data, altitude_data)

    # Ajuster dynamiquement les limites des axes
    ax.set_xlim(0, max(10, current_time + 1))  # Étend l'axe X
    ax.set_ylim(0, max(1000, max(altitude_data) + 100))  # Étend l'axe Y

    return line,

# Animation avec matplotlib
ani = FuncAnimation(fig, update, init_func=init, blit=False, interval=100)

# Afficher le graphique
plt.show()