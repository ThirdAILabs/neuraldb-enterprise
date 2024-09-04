job "redis-server" {
  datacenters = ["dc1"]

  group "redis" {
    count = 1

    network {
      port "redis-http" {
        to = 6379
      }
    }

    task "redis" {
      driver = "docker"

      config {
        image = "redis:latest"
        ports = ["redis-http"]
      }

      resources {
        cpu    = 500
        memory = 256
      }

      service {
        name = "redis"
        provider = "nomad"
        port = "redis-http"
        tags = ["traefik.enable=true"]

        check {
          type     = "tcp"
          port     = "redis-http"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }
  }
}
