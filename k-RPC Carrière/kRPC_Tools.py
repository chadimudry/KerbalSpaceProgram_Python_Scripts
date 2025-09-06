# This file is part of k-RPC Carrière.

# Librairies
from collections import defaultdict
import numpy as np
import time
import threading
import os

#-------------------------------------------------------------------------------------------------------------
# Permet de faire les expériences disponibles sur le vaisseau
def faire_experiences(vessel):
    done_experiments = set()
    remaining_modules_by_type = defaultdict(list)
    skipped_modules_by_type = defaultdict(list)

    modules_by_type = defaultdict(list)
    for exp in vessel.parts.experiments:
        exp_type = exp.name.strip()
        modules_by_type[exp_type].append(exp)

    for exp_type, modules in modules_by_type.items():
        executed = False
        for exp in modules:
            if exp.has_data:
                print(f"🔒 {exp_type} contient déjà des données")
                skipped_modules_by_type[exp_type].append(exp)
                continue

            if not exp.inoperable and exp.available:
                if not executed:
                    try:
                        exp.run()
                        # print(f"✅ Fait : {exp_type}")
                        done_experiments.add(exp_type)
                        executed = True
                    except Exception as e:
                        print(f"⚠️ Erreur sur {exp_type} : {e}")
                        skipped_modules_by_type[exp_type].append(exp)
                else:
                    skipped_modules_by_type[exp_type].append(exp)
            else:
                skipped_modules_by_type[exp_type].append(exp)

        remaining_modules_by_type[exp_type] = skipped_modules_by_type[exp_type]

    print("\n📋 Résumé des expériences :")
    print("✅ Effectuées :")
    for exp_type in sorted(done_experiments):
        total = len(modules_by_type[exp_type])
        print(f" - {exp_type} (1/{total})")

    print("🕒 Modules restants non utilisés :")
    for exp_type, remaining in remaining_modules_by_type.items():
        if exp_type not in done_experiments or len(remaining) > 0:
            print(f" - {exp_type} ({len(remaining)} restant(s))")
#-------------------------------------------------------------------------------------------------------------

# Compte à rebours
def countdown(t=3):
    for i in range(t, 0, -1):
        print(f"\rLancement dans {i}", end='', flush=True)
        time.sleep(1)
    print("\rDécollage ! 🚀                        ")

#-------------------------------------------------------------------------------------------------------------

# Décollage vertical
def decollage_vertical(vessel):
    vessel.control.throttle = 1.0

    vessel.auto_pilot.disengage()  # assure qu’on utilise bien le SAS manuel
    vessel.control.sas = True
    vessel.control.sas_mode = vessel.control.sas_mode.stability_assist

    countdown(3)
    vessel.control.activate_next_stage()
    print("🟢 SAS activé, plein gaz !")
#-------------------------------------------------------------------------------------------------------------

# Surveillance d'un changement de biome
def surveiller_biome(conn, vessel, check_interval=0.5):
    """
    Affiche le biome actuel en console et à l'écran dès qu'il change.

    Args:
        conn: connexion kRPC
        vessel: vaisseau actif
        check_interval: intervalle en secondes entre chaque vérification
    """
    print("📡 Surveillance des biomes activée...")
    previous_biome = vessel.biome

    while True:
        biome = vessel.biome
        if biome != previous_biome:
            previous_biome = biome
            msg = f"🌍 Nouveau biome détecté : {biome}"
            msg_KSP = f"Nouveau biome détecté : {biome}"
            print(msg)
            conn.ui.message(msg_KSP, duration=10, color=(0, 1, 0))
            break
        time.sleep(check_interval)
#-------------------------------------------------------------------------------------------------------------

def surveiller_et_decoupler(vessel, seuil=0.01):
    while True:
        total_fuel = vessel.resources.amount('LiquidFuel') + vessel.resources.amount('SolidFuel')
        max_fuel = vessel.resources.max('LiquidFuel') + vessel.resources.max('SolidFuel')

        if max_fuel == 0:
            print("⚠️ Aucun carburant détecté.")
            return

        proportion = total_fuel / max_fuel
        print(f"⛽ Carburant restant : {proportion*100:.2f}%")

        if proportion < seuil:
            print("🚀 Carburant bas, découplage de l'étage !")
            vessel.control.activate_next_stage()
            return

        time.sleep(0.5)
#-------------------------------------------------------------------------------------------------------------
# Réguléateur PID

class PID:
    def __init__(self, kp, ki=0.0, kd=0.0, setpoint=0.0, min_output=0.0, max_output=1.0, anti_integral_windup=True):
        self.kp = kp  # Coefficient proportionnel
        self.ki = ki  # Coefficient intégral
        self.kd = kd  # Coefficient dérivé
        self.setpoint = setpoint  # Cible à atteindre
        self.min_output = min_output
        self.max_output = max_output
        self.anti_integral_windup = anti_integral_windup

        self.integral = 0.0
        self.previous_error = 0.0

    def update(self, current_value, dt):
        # Calcul de l'erreur
        error = self.setpoint - current_value

        # Intégrale (somme des erreurs)
        self.integral += error * dt

        # Dérivée (variation de l'erreur)
        derivative = (error - self.previous_error) / dt if dt > 0 else 0.0

        # PID output
        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        # Anti-integral windup
        if self.anti_integral_windup:
            if output >= self.max_output:
                self.integral = 0.0

        # Mise à jour pour le prochain cycle
        self.previous_error = error

        return output
#-------------------------------------------------------------------------------------------------------------
# ANSI styles
BOLD = "\033[1m"
BLUE = "\033[94m"
RESET = "\033[0m"

def center_colored_text(text, color_code, total_width):
    raw_len = len(text)
    padding = max(0, total_width - raw_len)
    left = padding // 2
    right = padding - left
    return " " * left + f"{color_code}{text}{RESET}" + " " * right

def pad(content, width):
    return content.ljust(width)

# -------------------------------------------------------------------------------------------------------------
# Tangente linéaire
def linear_tangent(altitude, orbit_height=100000, s=8):
    return 90 - np.degrees(np.arctan(altitude * s / (orbit_height - altitude))) # picth en °

# -------------------------------------------------------------------------------------------------------------
