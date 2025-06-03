bind = "0.0.0.0:10000"
workers = 1  # For WebSocket applications, it's better to use a single worker
worker_class = "eventlet"
timeout = 120
keepalive = 65
worker_connections = 1000 