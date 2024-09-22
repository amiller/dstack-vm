#!/bin/bash

rm host_volume/startup_script.log

# Create a new tmux session
tmux new-session -d -s demo

# Split the window into 4 panes
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

# Run commands or scripts in each pane
tmux send-keys -t demo.0 "waitress-serve --listen=127.0.0.1:8000 host_service:app; bash" Enter
tmux send-keys -t demo.1 './start_vm.sh ./ubuntu_vm_dev.img; bash' Enter
tmux send-keys -t demo.2 'cd dummy-tdx-dcap; go run cmd/httpserver/main.go; bash' Enter
tmux send-keys -t demo.3 'tail -F host_volume/startup_script.log; bash' Enter

# Attach to the tmux session
tmux attach-session -t demo
