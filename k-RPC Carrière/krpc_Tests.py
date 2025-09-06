import krpc
import time
import os
import math
import sys
from kRPC_Tools import *
from kRPC_NodeExecutor import nodeExec

# === Télémétrie ===
from dataclasses import dataclass

@dataclass
class Telemetry:
    altitude:      float = 0.0   # m
    q:             float = 0.0 # Pa
    pase_mode:     str   = "launch"  # -
    pitch_ang:     float = 0.0 # °
    throttle:      float = 0.0 # 0-1
    TWR:           float = 0.0 # -
    running:       bool  = True   # -

telemetry = Telemetry()
stop_event = threading.Event()
dt = 0.1 # s

inside_width = 36
title_text = "Télémetrie"

def show_telemetry():
    print("\033[2J\033[?25l", end='')  # Efface écran + cache curseur
    while not stop_event.is_set():
        telemetry.altitude = altitude() / 1000  # Convertir en km
        telemetry.q = dynamic_pressure() # Pa
        telemetry.phase_mode = phase_mode
        telemetry.pitch_ang = pitch_ang # °
        telemetry.throttle = vessel.control.throttle * 100 # 0-1
        telemetry.TWR = get_TWR() # -

        print("\033[H", end='')  # Curseur en haut
        print( "┌────────────────────────────────────┐")
        print(f"│{center_colored_text(title_text, BOLD + BLUE, inside_width)}│")
        print( "├────────────────────────────────────┤")
        print(f"│ {pad(f'Altitude        : {telemetry.altitude:>10.3f} km', 35)}│")
        print(f"│ {pad(f'Q dynamique     : {telemetry.q:>10.0f} Pa', 35)}│")
        print(f"│ {pad(f'Pitch           : {telemetry.pitch_ang:>10.1f} °', 35)}│")
        print(f"│ {pad(f'TWR             : {telemetry.TWR:>10.2f}  ', 35)}│")
        print(f"│ {pad(f'Gaz             : {telemetry.throttle:>10.1f} %', 35)}│")
        print(f"│ {pad(f'Phase mode      : {telemetry.phase_mode}', 35)}│")
        print( "└────────────────────────────────────┘")
        sys.stdout.flush()
        time.sleep(dt)

# === Initialisation ===
os.system('cls')
print('\033[?25l', end='')  # Cacher le curseur
print("\033[2J", end='')    # Effacer tout
print("\033[H", end='')     # Curseur en haut

# Connexion à KSP
conn = krpc.connect(name='Orbiter4')
vessel = conn.space_center.active_vessel
srf_ref = vessel.surface_velocity_reference_frame
obt_ref = vessel.orbital_reference_frame
vel_ref = vessel.orbit.body.reference_frame

# Désactivation des contrôles automatiques
vessel.control.sas = False
vessel.control.rcs = False
vessel.control.throttle = 1.0

booster_type = 'liquid' # 'liquid' ; 'solid'

booster_stage = vessel.control.current_stage - 1

ut = conn.add_stream(getattr, conn.space_center, 'ut')
altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
booster_stage_ressources = vessel.resources_in_decouple_stage(stage=booster_stage, cumulative=False)

if booster_type == 'solid':
    booster_fuel = conn.add_stream(booster_stage_ressources.amount, 'SolidFuel')
elif booster_type == 'liquid':
    booster_fuel = conn.add_stream(booster_stage_ressources.amount, 'LiquidFuel')
else:
    booster_fuel = -1

dynamic_pressure = conn.add_stream(getattr, vessel.flight(), 'dynamic_pressure')
# velocity = conn.add_stream(getattr, vessel.flight(vel_ref), 'velocity')
mass = conn.add_stream(getattr, vessel, 'mass')
thrust = conn.add_stream(getattr, vessel, 'thrust')

def get_TWR():
    mu = vessel.orbit.body.gravitational_parameter
    r = vessel.orbit.radius
    g_local = mu / (r ** 2)
    return thrust() / (mass() * g_local)

countdown()
vessel.control.activate_next_stage()
current_available_max_thrust = vessel.available_thrust

ap = vessel.auto_pilot
ap.target_pitch_and_heading(90, 90)
ap.auto_tune = False
ap.pitch_pid_gains = (0.5, 0.05, 5.0)  # Kp réduit, Kd augmenté
ap.yaw_pid_gains = (0.5, 0.05, 5.0)
ap.roll_pid_gains = (0.5, 0.02, 1.2)  # Roll plus sensible, gains plus bas
# ap.stopping_time = (0.3, 0.3, 0.3)    # Temps d'arrêt rapide
# ap.deceleration_time = (3.0, 3.0, 3.0)  # Décélération douce
# ap.attenuation_angle = (2.0, 2.0, 2.0)  # Angle d'atténuation pour cible atteinte
ap.engage()

if booster_fuel == -1:
    booster_present = False
else:
    booster_present = True
boosters_separated = False
active_pid = False
phase_mode = "launch"
pitch_ang = 90 # °
os.system('cls')

# === Lancement du thread d'affichage ===
thread_show_telemetry = threading.Thread(target=show_telemetry)
thread_show_telemetry.start()

def pitch_program():
    switch_alt = 250 # m
    pitch_ang = 0 # °
    scale_factor = 1 # - 
    alt_diff = scale_factor * vessel.orbit.body.atmosphere_depth - switch_alt # m
    if altitude() >= switch_alt:
        pitch_ang = max(0, min(90, 90 * math.sqrt((apoapsis() - switch_alt) / alt_diff)))
    return pitch_ang

# Création du PID pour l'accélération
thrust_pid = PID(kp=1, ki=0.05, setpoint=2, anti_integral_windup=False)

# --- Orbite cible ---
target_apoapsis = 100_000 # m
target_heading = 90 # ° | 0 ° : Nord ; 90 ° : Est

try:
    while True:
        if phase_mode == 'launch' and altitude() >= 150:
            ap.target_pitch_and_heading(90, target_heading)
            current_max = vessel.max_thrust
            phase_mode = 'roll'
        
        elif phase_mode == 'roll':
            ap.target_roll = 0
            phase_mode = 'pitch_program'

        elif phase_mode == 'pitch_program' and altitude() >= 250:
            pitch_ang = 90 - pitch_program()
            ap.target_pitch_and_heading(pitch_ang, target_heading)
            
            # PID
            # Régulation des gaz    
            current_TWR = get_TWR()
            if active_pid:
                throttle_output = thrust_pid.update(current_TWR, dt)
                vessel.control.throttle = max(0.0, min(1.0, throttle_output))
                error = thrust_pid.setpoint - current_TWR

            # Séparation des boosters
            if booster_present:
                if not boosters_separated:
                    if booster_type == 'solid':
                        if booster_fuel < 0.1:
                            vessel.control.activate_next_stage()
                            boosters_separated = True
                            print("Séparation des boosters (solides)")
                    elif booster_type == 'liquid':
                        if vessel.available_thrust < current_available_max_thrust:
                            vessel.control.activate_next_stage()
                            boosters_separated = True
                            print("Séparation des boosters (liquides)")
            
            if vessel.available_thrust <= 0.1:
                vessel.control.activate_next_stage()

            if apoapsis() >= 0.95 * target_apoapsis:
                vessel.control.throttle = 0.25

                if apoapsis() >= target_apoapsis:
                    vessel.control.throttle = 0
                    phase_mode = 'circularization'

        elif phase_mode == 'circularization':
            # Equation de Vis-viva
            target_apoapsis = apoapsis()
            mu = vessel.orbit.body.gravitational_parameter
            r = vessel.orbit.apoapsis
            a = vessel.orbit.semi_major_axis
            body_radius = vessel.orbit.body.equatorial_radius
            vc = math.sqrt(mu * ((2/r) - (1/a)))
            v = math.sqrt(mu/(body_radius+target_apoapsis))
            delta_v = vc - v
            # print(f"Δv requis: {delta_v:.1f} m/s")

            # Création d'un noeud de manoeuvre
            node = vessel.control.add_node(
                ut = ut()+ vessel.orbit.time_to_apoapsis,
                prograde = -delta_v)
            
            while altitude() <= vessel.orbit.body.atmosphere_depth - 1000:
                time.sleep(0.1)
            vessel.auto_pilot.reference_frame = node.reference_frame
            vessel.auto_pilot.target_direction = (0, 1, 0)  # Vecteur du nœud de manœuvre
            vessel.auto_pilot.wait()

            ap.disengage()
            vessel.control.sas = True
            
            while altitude() <= vessel.orbit.body.atmosphere_depth:
                time.sleep(0.1)
            
            # Execution du noeud de manoeuvre de circularisation
            nodeExec(conn)
            break

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Interruption manuelle                  ")
    stop_event.set()
    thread_show_telemetry.join()

finally:
    print("Fin du script                          ")
    stop_event.set()
    thread_show_telemetry.join()
    conn.close()