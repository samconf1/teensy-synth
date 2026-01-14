#Runs once on teensy power on. Initialise storage as writeable. Read only from the computer.


import storage
storage.remount("/", readonly=False)

