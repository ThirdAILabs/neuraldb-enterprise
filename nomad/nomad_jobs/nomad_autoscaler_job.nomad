job "autoscaler" {
  datacenters = ["dc1"]

  type = "service"

  group "autoscaler" {
    count = 1


    network {
      port "http" {}
    }

    task "autoscaler" {
      driver = "docker"

      config {
        image   = "hashicorp/nomad-autoscaler:0.3.7"
        command = "nomad-autoscaler"
        ports   = ["http"]

        args = [
          "agent",
          "-config",
          "${NOMAD_TASK_DIR}/config.hcl",
          "-http-bind-address", 
          "0.0.0.0",
          "-http-bind-port",
          "${NOMAD_PORT_http}",
        ]
      }

      template {
        data = <<EOF
nomad {
  address = "http://{{ env "attr.unique.network.ip-address" }}:4646"
}

apm "nomad-apm" {
  driver = "nomad-apm"
}

strategy "target-value" {
  driver = "target-value"
}
          EOF

        destination = "${NOMAD_TASK_DIR}/config.hcl"
      }

      resources {
        cpu    = 50
        memory = 128
      }

      service {
        name = "autoscaler"
        provider = "nomad"
        port = "http"

        check {
          type     = "http"
          path     = "/v1/health"
          interval = "3s"
          timeout  = "1s"
        }
      }
    }
  }
}