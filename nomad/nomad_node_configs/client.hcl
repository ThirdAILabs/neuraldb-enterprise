data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

server {
  enabled = false
  preemption_config {
    batch_scheduler_enabled    = true
    system_scheduler_enabled   = true
    service_scheduler_enabled  = false
    sysbatch_scheduler_enabled = false
  }
}

client {
  enabled = true
  server_join {
    retry_join = [""]
    retry_max = 3
    retry_interval = "15s"
  }
}

plugin "docker" {
  config {
    volumes {
      enabled = true
    }
  }
}