<?php
shell_exec("/home/pi/BirdNET-Lite/scripts/restart_birdnet.sh");
header('Location: http://birdnetsystem.local/scripts/index.html?success=true');
?>