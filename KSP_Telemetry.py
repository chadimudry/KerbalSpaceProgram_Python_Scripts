# Création de la fonction de telemetrie
import krpc
import time

def telemetry_infos(conn):
    import time  # Assure que time est importé si non inclus
    import krpc  # Assure que kRPC est importé si non inclus

    # Connexion à kRPC
    vessel = conn.space_center.active_vessel  # Récupère le vaisseau actif
    space_center = conn.space_center
    vessel_name = vessel.name
    vessel_type = str(vessel.type).split(".")[-1]
    vessel_situation = str(vessel.situation).split(".")[-1]

    # Créer des streams pour récupérer les données en temps réel
    apo_stream = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
    per_stream = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')
    gs_stream = conn.add_stream(getattr, vessel.flight(), 'g_force')
    vsl_situation_stream = conn.add_stream(getattr, vessel, 'situation')
    current_body_stream = conn.add_stream(getattr, vessel.orbit.body, 'name')
    current_biome_stream = conn.add_stream(getattr, vessel, 'biome')
    target_body_stream = conn.add_stream(getattr, space_center, 'target_body')
    vessel_mass_stream = conn.add_stream(getattr, vessel, 'mass')
    g_surface_stream = conn.add_stream(getattr, vessel.orbit.body, 'surface_gravity')
    radius_stream = conn.add_stream(getattr, vessel.orbit.body, 'equatorial_radius')
    altitude_stream = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
    thrust_stream = conn.add_stream(getattr, vessel, 'thrust')
    pressure_stream = conn.add_stream(getattr, vessel.flight(), 'static_pressure')

    def get_thrust_MAX():
        p_atm = pressure_stream() / 101325
        return vessel.max_thrust_at(p_atm)

    # Compute TWRs
    current_TWR = thrust_stream() / (vessel_mass_stream() * g_surface_stream())

    if vessel_situation == 'pre_launch':
        max_thrust = 0
        active_stage = vessel.control.current_stage
        for engine in vessel.parts.engines:
            if engine.part.stage == active_stage-1:
                thrust = engine.max_thrust_at(pressure_stream() / 101325)
                max_thrust += thrust
        Max_TWR = max_thrust / (vessel_mass_stream() * g_surface_stream())

    else:            
        Max_TWR = get_thrust_MAX() / (vessel_mass_stream() * g_surface_stream())



    # Récupération de l'objet Canvas
    canvas = conn.ui.stock_canvas

    # Créer un conteneur pour l'affichage
    screen_size = canvas.rect_transform.size
    panel_size = (300, 300) # (x, y)
    panel = canvas.add_panel()
    panel.rect_transform.size = panel_size  # Taille du panneau (largeur, hauteur)
    panel.rect_transform.position = (-screen_size[0] / 2 + panel_size[0] / 2 + 5, screen_size[1] / 2 - panel_size[1])  # Position du panneau (x, y) dans l'écran

    # Base text position 
    y0 = panel.rect_transform.size[1] / 2 - 45  # Décalage initial pour laisser de l'espace au titre et à la ligne

    def make_line(y_pos):
        txt_separator = panel.add_text("-" * 38)
        txt_separator.rect_transform.position = (-60, y_pos)  # Sous le titre
        txt_separator.color = (1, 1, 1)
        txt_separator.size = 12
        txt_separator = panel.add_text("-" * 31)
        txt_separator.rect_transform.position = (90, y_pos)  # Sous le titre
        txt_separator.color = (1, 1, 1)
        txt_separator.size = 12
        return txt_separator

    # Title (ligne 0)
    txt_title = panel.add_text("Telemetry")
    txt_title.rect_transform.position = (-60, panel.rect_transform.size[1]/2 + 5) # (x, y)
    txt_title.color = (0.9, 0.9, 0.9)
    txt_title.size = 16

    # SubTitre "General Infos"
    txt_subtitle = panel.add_text("General")
    txt_subtitle.rect_transform.position = (-60, panel.rect_transform.size[1] / 2 - 30)  # Centré horizontalement
    txt_subtitle.color = (1, 1, 1)
    txt_subtitle.size = 12

    # SubTitre "Vessel"
    txt_subtitle = panel.add_text("Vessel")
    txt_subtitle.rect_transform.position = (-60, y0 - 4*15)  # Centré horizontalement
    txt_subtitle.color = (1, 1, 1)
    txt_subtitle.size = 12

    # SubTitre "Engine"
    txt_subtitle = panel.add_text("Engine(s)")
    txt_subtitle.rect_transform.position = (-60, y0 - 7*15)  # Centré horizontalement
    txt_subtitle.color = (1, 1, 1)
    txt_subtitle.size = 12

    # Simuler une ligne avec du texte (caractères -----)
    # make_line(panel.rect_transform.size[1] / 2 - 30)
    make_line(y0 + 2*15 - 2)
    make_line(y0 - 3*15)
    make_line(y0 - 6*15)

    # Dictionnaire pour stocker les paramètres des textes
    text_params = {
        "Vessel_name":{
            "content":f"Name: {vessel_name}",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0)
        },
        "Vessel_type":{
            "content":f"Type: {vessel_type}",
            "color": (1, 1, 1),
            "size": 12,
            "position": (90, y0)
        },
        "Vessel_situation":{
            "content":f"Status: {vessel_situation}",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0 - 2*15)
        },
        "Current_body":{
            "content":f"Current Body: {current_body_stream()}",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0 - 1*15)
        },
        "Current_biome":{
            "content":f"Current Biome: {current_biome_stream()}",
            "color": (1, 1, 1),
            "size": 12,
            "position": (90, y0 - 1*15)
        },
        "Target_body":{
            "content":f"Target Body: -",
            "color": (1, 1, 1),
            "size": 12,
            "position": (90, y0 - 2*15)
        },
        "Mass":{
            "content":f"Mass: {vessel_mass_stream()/1000} to",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0 - 5*15)
        },
        "TWR":{
            "content":f"TWR (Max): {current_TWR} ({Max_TWR})",
            "color": (1, 1, 1),
            "size": 12,
            "position": (90, y0 - 5*15)
        },
            "Apo": {
            "content": "Apoapsis: 0.000 km",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0 - 20*15)  # (ligne 1)
        },
        "Per": {
            "content": "Periapsis: 0.000 km",
            "color": (1, 1, 1),
            "size": 12,
            "position": (90, y0 - 20*15)  # (ligne 2)
        },
        "Gs": {
            "content": "G-Force: 0.0",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0 - 21*15)  # (ligne 3)
        },
        "Engine_names": {
            "content": "-",
            "color": (1, 1, 1),
            "size": 12,
            "position": (-60, y0 - 8*15)
        },
    }



    # Créer un dictionnaire pour stocker les objets Text créés
    texts = {}

    # Boucle pour créer et ajouter chaque texte
    for param, settings in text_params.items():
        text = panel.add_text(settings["content"])
        text.color = settings["color"]
        text.size = settings["size"]
        text.rect_transform.position = settings["position"]
        texts[param] = text

    # Mise à jour des textes en temps réel
    try:
        while True:
            # Récupérer les données en temps réel
            vsl_situation = str(vsl_situation_stream()).split(".")[-1]
            crt_body = current_body_stream()
            crt_biome = current_biome_stream()
            vsl_mass = vessel_mass_stream()/1000
            apo = apo_stream() / 1000
            per = per_stream() / 1000
            Gs = gs_stream()
            
            # Compute TWR
            current_TWR = thrust_stream() / (vessel_mass_stream() * g_surface_stream())

            # Compute Engines parameters
            active_stage = vessel.control.current_stage
            engine_names = []
            names = []
            max_thrusts = []
            for engine in vessel.parts.engines:
                if engine.part.stage == active_stage:
                    engine_names.append(engine.part.title)
                    thrust = engine.max_thrust_at(pressure_stream()/101325)
                    max_thrusts.append(thrust)

            for name in engine_names:
                names.append(f"{name.split()[4]} {name.split()[5]}")

            if vsl_situation == 'pre_launch':
                max_thrust = 0
                active_stage = vessel.control.current_stage
                for engine in vessel.parts.engines:
                    if engine.part.stage == active_stage-1:
                        thrust = engine.max_thrust_at(pressure_stream() / 101325)
                        max_thrust += thrust
                Max_TWR = max_thrust / (vessel_mass_stream() * g_surface_stream())
                names = "-"

            else:            
                Max_TWR = get_thrust_MAX() / (vessel_mass_stream() * g_surface_stream())

            try:
                target_body = target_body_stream().name
            except:
                target_body = '-'

            # Mettre à jour le contenu des textes avec les nouvelles valeurs
            texts['Vessel_situation'].content = f"Status: {vsl_situation}"
            texts['Current_body'].content = f"Current Body: {crt_body}"
            texts['Current_biome'].content = f"Current Biome: {crt_biome}"
            texts['Target_body'].content = f"Target Body: {target_body}"
            texts['Mass'].content = f"Mass: {vsl_mass:.3f} To"
            texts['TWR'].content = f"TWR (Max): {current_TWR:.2f} ({Max_TWR:.2f})"
            texts["Apo"].content = f"Apoapsis: {apo:.3f} km"
            texts["Per"].content = f"Periapsis: {per:.3f} km"
            texts["Gs"].content = f"G-Force: {Gs:.1f}"
            texts['Engine_names'].content = f"{names}"

            # Attendre un petit moment avant la prochaine mise à jour
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nScript interrompu.")

    finally:
        vsl_situation_stream.remove()
        current_body_stream.remove()
        current_biome_stream.remove()
        target_body_stream.remove()
        vessel_mass_stream.remove()
        g_surface_stream.remove()
        radius_stream.remove()
        altitude_stream.remove()
        apo_stream.remove()
        per_stream.remove()
        gs_stream.remove()
        thrust_stream.remove()
        pressure_stream.remove()
        print("Streams déconnectés")


conn = krpc.connect(name="Telemetry")
vessel = conn.space_center.active_vessel  # Récupère le vaisseau actif
vessel.control.throttle = 1
vessel.control.sas = True
telemetry_infos(conn)