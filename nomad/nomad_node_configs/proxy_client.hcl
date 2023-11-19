data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

server {
  enabled = false
}

client {
  enabled = true
  server_join {
    retry_join = [""]
    retry_max = 3
    retry_interval = "15s"
  }
  node_class = "web_ingress"
}

plugin "docker" {
  config {
    volumes {
      enabled = true
    }
  }
}