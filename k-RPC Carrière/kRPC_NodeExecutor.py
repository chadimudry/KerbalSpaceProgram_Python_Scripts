import time
import math

def nodeExec(conn):
    vessel = conn.space_center.active_vessel

    vessel.control.sas = False

    # Vérifier s'il existe un nœud de manœuvre
    control = vessel.control
    if not control.nodes:
        print("Erreur : Aucun nœud de manœuvre trouvé !")
        conn.close()
        exit()

    # Récupérer le premier nœud de manœuvre
    node = control.nodes[0]
    delta_v = node.delta_v
    print(f"Nœud de manœuvre trouvé avec Delta-V : {delta_v:.2f} m/s")

    # Configurer l'auto-pilote pour pointer vers le nœud
    vessel.auto_pilot.reference_frame = node.reference_frame
    vessel.auto_pilot.target_direction = (0, 1, 0)  # Vecteur du nœud de manœuvre
    vessel.auto_pilot.engage()
    print("Auto-pilote engagé, orientation vers le nœud...")

    # Attendre que le vaisseau soit orienté correctement
    vessel.auto_pilot.wait()
    print("Vaisseau orienté vers le nœud !")

    # Calculer la durée du burn
    isp = vessel.specific_impulse  # Impulsion spécifique (s)
    if isp == 0:
        print("Pas de moteur actif trouvé ...")
        print("Activation de l'étage supérieur")
        vessel.control.activate_next_stage()

    g0 = 9.81  # Accélération gravitationnelle standard (m/s²)
    mass = vessel.mass  # Masse du vaisseau (kg)
    thrust = vessel.available_thrust  # Poussée disponible (N)
    if thrust == 0:
        print("Erreur : Poussée nulle, vérifiez les moteurs ou le carburant !")
        conn.close()
        exit()

    # Calculer la durée du burn avec la formule de Tsiolkovsky
    flow_rate = thrust / (isp * g0)  # Débit massique (kg/s)
    burn_time = mass * (1 - math.exp(-delta_v / (isp * g0))) / flow_rate
    print(f"Durée du burn estimée : {burn_time:.2f} secondes")

    # Attendre le bon moment pour commencer le burn (T- burn_time/2)
    ut = conn.space_center.ut  # Temps universel actuel
    node_time = node.ut  # Temps du nœud
    burn_start = node_time - (burn_time / 2)
    print(f"En attente du début du burn à T-{burn_time/2:.2f} secondes...")

    # Warper jusqu'à 20 secondes avant le nœud de manœuvre
    node_time = node.ut  # Temps universel du nœud
    warp_target = node_time - 20  # T-20 secondes
    print(f"Warping jusqu'à 10 secondes avant le nœud ...")
    conn.space_center.warp_to(warp_target)

    # Phase 1 : Burn principal à pleine poussée (jusqu'à 5% du Δv restant)
    # Attendre le moment exact du burn
    ut = conn.add_stream(getattr, conn.space_center, 'ut')
    while ut() < burn_start:
        time.sleep(0.1)

    print("Début du burn principal !")
    vessel.control.throttle = 1.0
    remaining_dv = node.remaining_delta_v
    while remaining_dv > min(0.05 * delta_v, 10):  # Continuer jusqu'à 5% du Δv initial ou 10 m/s
        remaining_dv = node.remaining_delta_v
        # Vérifier l'orientation
        if vessel.auto_pilot.error > 5:  # Si l'erreur d'angle dépasse 5 degrés
            print("Réajustement de l'orientation...")
            vessel.auto_pilot.wait()
        if vessel.available_thrust <= 0.1:
            vessel.control.activate_next_stage()
        time.sleep(0.01)

    # Phase 2 : Burn précis à faible poussée avec ajustement basé sur le TWR
    print("Passage au burn précis...")
    target_dv = 0.05  # Tolérance : arrêter quand Δv restant < 0.1 m/s

    # Récupérer la référence au corps céleste
    body = vessel.orbit.body
    gravity = body.gravitational_parameter / vessel.orbit.radius**2  # Gravité locale

    # Suivre les changements d'étage
    last_stage = vessel.control.current_stage

    while remaining_dv > target_dv:
        remaining_dv = node.remaining_delta_v

        if vessel.available_thrust <= 0.1:
            vessel.control.activate_next_stage()
        
        # Vérifier si l'étage a changé (staging)
        current_stage = vessel.control.current_stage
        if current_stage != last_stage:
            print("Changement d'étage détecté ! Recalcul des paramètres...")
            last_stage = current_stage
        
        # Calculer le TWR actuel
        thrust = vessel.available_thrust  # Poussée max disponible (N)
        mass = vessel.mass  # Masse du vaisseau (kg)
        weight = mass * gravity  # Poids (N)
        twr = thrust / weight if weight > 0 else 1.0
        
        # Calculer l'accélération pour anticiper l'arrêt
        acceleration = thrust * vessel.control.throttle / mass  # Accélération (m/s²)
        time_to_target = remaining_dv / acceleration if acceleration > 0 else float('inf')
        
        # Ajuster la poussée en fonction du Δv restant et du TWR
        base_throttle = min(0.1, remaining_dv / (remaining_dv + 0.01 * delta_v))  # Courbe hyperbolique
        twr_factor = min(1.0, 1 / twr)  # Plus contraignant pour TWR élevés
        
        # Poussée minimale dynamique plus fine
        min_throttle = max(0.0005, 0.005 / (twr * mass / 1000))  # Réduit pour moteurs puissants
        throttle = max(min_throttle, base_throttle * twr_factor)
        
        # Arrêt anticipé plus agressif
        if remaining_dv < target_dv or time_to_target < 0.1:  # Ex. < 0.2 m/s ou 0.1s avant cible
            print("Approche finale, coupure poussée...")
            vessel.control.throttle = 0.0
            break
        
        vessel.control.throttle = throttle
        
        # Pas de time.sleep pour maximiser la réactivité

    # Arrêter le burn
    vessel.control.throttle = 0.0
    print(f"Burn terminé avec Δv restant : {remaining_dv:.2f} m/s")

    # Désactiver l'auto-pilote
    vessel.auto_pilot.disengage()
    print("Auto-pilote désengagé.")

    # Supprimer le nœud de manœuvre
    node.remove()
    print("Nœud de manœuvre supprimé.")