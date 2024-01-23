data_dir  = "/opt/nomad/data"
bind_addr = "0.0.0.0"

server {
  enabled = $SERVER_ENABLED
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
  $NODE_CLASS_STRING
  node_pool = "$NODE_POOL"
  enabled = $CLIENT_ENABLED
  server_join {
    retry_join = ["$NOMAD_SERVER_PRIVATE_IP"]
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