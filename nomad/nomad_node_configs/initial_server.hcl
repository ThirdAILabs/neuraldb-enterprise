data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

server {
  enabled = true
  bootstrap_expect = 1
  default_scheduler_config {
    preemption_config {
      batch_scheduler_enabled    = true
      system_scheduler_enabled   = true
      service_scheduler_enabled  = false
      sysbatch_scheduler_enabled = false
    }
  }
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