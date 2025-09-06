import krpc
import time
import os
import sys
from kRPC_Tools import *
import math

inside_width = 36
title_text = "Télémetrie"

def telemetry(altitude, q, throttle, pitch):
    print("\033[H", end='')  # Curseur en haut

    print( "┌────────────────────────────────────┐")
    print(f"│{center_colored_text(title_text, BOLD + BLUE, inside_width)}│")
    print( "├────────────────────────────────────┤")
    print(f"│ {pad(f'Altitude    : {altitude:>10.3f} km', 35)}│")
    print(f"│ {pad(f'Q dynamique : {q:>10.0f} Pa', 35)}│")
    print(f"│ {pad(f'Gaz         : {throttle*100:>10.0f} %', 35)}│")
    print(f"│ {pad(f'Inclinaison : {pitch:>10.1f} °', 35)}│")
    print( "└────────────────────────────────────┘")
    sys.stdout.flush()


# === Initialisation ===
os.system('cls')
print('\033[?25l', end='')  # Cacher le curseur
print("\033[2J", end='')    # Effacer tout
print("\033[H", end='')     # Curseur en haut

# Connexion à KSP
conn = krpc.connect(name='Orbiter1')
vessel = conn.space_center.active_vessel
print("Connecté à KSP : ", conn.krpc.get_status().version,"\n")
print(f"Vaisseau actif : {vessel.name}")
print(f"Kerbals à bord : {[kerbal.name for kerbal in vessel.crew]}")
time.sleep(1)

# Désactivation des contrôles automatiques
vessel.control.sas = False
vessel.control.rcs = False
vessel.control.throttle = 1.0

# Paramètres de vol
turn_start_altitude = 500 # m
target_altitude = 100000 # m

dynamic_pressure = conn.add_stream(getattr, vessel.flight(), 'dynamic_pressure')
ut = conn.add_stream(getattr, conn.space_center, 'ut')
altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
stage_2_resources = vessel.resources_in_decouple_stage(stage=2, cumulative=False)
srb_fuel = conn.add_stream(stage_2_resources.amount, 'SolidFuel')

# Régulateur PID pour la pression dynamique
dt = 0.05
thrust_pid = PID(kp=0.002, setpoint=20000)

# Logs
time_log = []
throttle_log = []
q_log = []
altitude_log = []
start_time = time.time()

# Décollage + 1ère phase de vol
# print("🟢 SAS activé")
print("🚀 Prêt pour le lancement !")
time.sleep(0.5)
print("Début du comptage à rebours...\n")
countdown(1)
vessel.control.activate_next_stage()
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(90, 90)
srbs_separated = False
active_pid = True
launch_phase = True
space_phase = False
circularization_calc_done = False
os.system('cls')

pitch = 90.0 # °C

# === Boucle ===
try:
    while True:
        if launch_phase:
        # rotation
            if altitude() >= 150:
                vessel.auto_pilot.target_roll = 0
        # Gravity turn
            if altitude() >= turn_start_altitude:
                pitch = linear_tangent(altitude(), target_altitude, s=8)
                vessel.auto_pilot.target_pitch_and_heading(pitch, 90) # 90 = Est
            
                # Separate SRBs when finished
            if not srbs_separated:
                if srb_fuel() < 0.1:
                    vessel.control.activate_next_stage()
                    srbs_separated = True
                    print('SRBs separated')

            # Régulation des gaz    
            current_q = dynamic_pressure()
            elapsed = time.time() - start_time

            # PID
            if active_pid:
                throttle_output = thrust_pid.update(current_q, dt)
                vessel.control.throttle = max(0.0, min(1.0, throttle_output))
                error = thrust_pid.setpoint - current_q

        # Decrease throttle when approaching target apoapsis
            if apoapsis() > target_altitude*0.9:
                active_pid = False
                launch_phase = False
                space_phase = True
                print('Approaching target apoapsis')
        
        elif space_phase:
            vessel.control.throttle = 0.25
            while apoapsis() < target_altitude-500:
                pass
            print('Target apoapsis reached')
            vessel.control.throttle = 0.0

            # Wait until out of atmosphere
            print('Coasting out of atmosphere')
            while altitude() < 70500:
                pass

            # Circularisation
            if not circularization_calc_done:
                print('Planning circularization burn')
                mu = vessel.orbit.body.gravitational_parameter
                r = vessel.orbit.apoapsis
                a1 = vessel.orbit.semi_major_axis
                a2 = r
                v1 = math.sqrt(mu*((2./r)-(1./a1)))
                v2 = math.sqrt(mu*((2./r)-(1./a2)))
                delta_v = v2 - v1
                node = vessel.control.add_node(
                    ut() + vessel.orbit.time_to_apoapsis, prograde=delta_v)

                # Calculate burn time (using rocket equation)
                F = vessel.available_thrust
                Isp = vessel.specific_impulse * 9.81
                m0 = vessel.mass
                m1 = m0 / math.exp(delta_v/Isp)
                flow_rate = F / Isp
                burn_time = (m0 - m1) / flow_rate
                # Orientate ship
                print('Orientating ship for circularization burn')
                vessel.auto_pilot.reference_frame = node.reference_frame
                vessel.auto_pilot.target_direction = (0, 1, 0)
                vessel.auto_pilot.wait()

                # Wait until burn
                print('Waiting until circularization burn')
                burn_ut = ut() + vessel.orbit.time_to_apoapsis - (burn_time/2.)
                lead_time = 5
                conn.space_center.warp_to(burn_ut - lead_time)

                # Execute burn
                print('Ready to execute burn')
                time_to_apoapsis = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
                while time_to_apoapsis() - (burn_time/2.) > 0:
                    pass
                print('Executing burn')
                vessel.control.throttle = 1.0
                time.sleep(burn_time - 0.1)
                print('Fine tuning')
                vessel.control.throttle = 0.05
                remaining_burn = conn.add_stream(node.remaining_burn_vector, node.reference_frame)
                while remaining_burn()[1] > 0.1:
                    pass
                vessel.control.throttle = 0.0
                node.remove()

                print('Vaisseau en orbite')
                circularization_calc_done = True
                break

        # Logs
        time_log.append(elapsed)
        throttle_log.append(vessel.control.throttle)
        q_log.append(current_q)
        
    # Affichage de la télémetrie
        telemetry(altitude()/1000, current_q, vessel.control.throttle, pitch)

        time.sleep(dt)

except KeyboardInterrupt:
    print('\033[?25h', end='')  # Réaffiche le curseur
    print("\nArrêt manuel du script de lancement.\n")

# faire_experiences(vessel)

print('Launch complete')