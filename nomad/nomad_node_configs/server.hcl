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
  enabled = false
}

ui {
  enabled = false
}

