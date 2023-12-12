data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

advertise {
  http = ""
  rpc  = ""
  serf = ""
}

server {
  enabled = true
  bootstrap_expect = 1
}

client {
  enabled = true
  node_class = "web_ingress"
  servers = ["127.0.0.1"]
}

plugin "docker" {
  config {
    volumes {
      enabled = true
    }
  }
}