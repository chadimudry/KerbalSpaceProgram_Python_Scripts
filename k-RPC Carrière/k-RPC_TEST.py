import krpc
import time
import numpy as np
from kRPC_NodeExecutor import nodeExec

conn = krpc.connect(name='Orbiter1')
vessel = conn.space_center.active_vessel
ref_frame = vessel.orbital_reference_frame  # Frame orbital pour manœuvre en orbite

time.sleep(1)
print("Alignement en cours ...")
nodeExec(conn)