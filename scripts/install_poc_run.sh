#!/bin/bash

# Create global command 'poc_run' for starting the GUI

echo "Setting up 'poc_run' alias command..."

sudo bash -c 'cat > /usr/local/bin/poc_run << "EOF"
#!/bin/bash
# POC Run - Global shortcut for starting the Demo GUI

echo "=========================================="
echo "Starting Robot POC GUI..."
echo "=========================================="

if [ -f "/home/nvidia/poc/poc-orin/gui/scripts/demo_gui_tk.py" ]; then
    /usr/bin/python3 /home/nvidia/poc/poc-orin/gui/scripts/demo_gui_tk.py "$@"
else
    echo "Error: GUI script not found at /home/nvidia/poc/poc-orin/gui/scripts/demo_gui_tk.py"
    echo "Are you sure the repository is cloned and synced?"
    exit 1
fi
EOF'

sudo chmod +x /usr/local/bin/poc_run

echo "Done! You can now type 'poc_run' anywhere in the terminal to start the GUI."