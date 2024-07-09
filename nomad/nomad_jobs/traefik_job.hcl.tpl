job "traefik" {
  datacenters = ["dc1"]

  type = "service"

  constraint {
    attribute = "${node.class}"
    value = "web_ingress"
  }

  node_pool = "default"

  group "traefik" {
    count = 1

    network {
      port "http" {
        static = 80
      }
      port "https" {
        static = 443
      }
      port "admin" {
        static = 8080
      }
    }

    service {
      name = "traefik-http"
      provider = "nomad"
      port = "http"
    }

    service {
      name = "traefik-https"
      provider = "nomad"
      port = "https"
    }

    task "server" {
      driver = "docker"

      template {
        destination = "${NOMAD_SECRETS_DIR}/env.vars"
        env = true
        change_mode = "restart"
        data = <<EOF
{{- with nomadVar "nomad/jobs" -}}
TASK_RUNNER_TOKEN = {{ .task_runner_token }}
{{- end -}}
EOF
      }

      config {
        image = "traefik:v2.10"
        ports = ["admin", "http", "https"]
        args = [
          "--api.dashboard=true",
          "--entrypoints.web.address=:${NOMAD_PORT_http}",
          "--entrypoints.websecure.address=:${NOMAD_PORT_https}",
          "--entrypoints.traefik.address=:${NOMAD_PORT_admin}",
          "--providers.nomad=true",
          "--providers.nomad.endpoint.address=http://172.31.24.191:4646", ### IP to your nomad server 
          "--providers.nomad.endpoint.token=${TASK_RUNNER_TOKEN}",
          "--entrypoints.websecure.http.tls=true",
          "--providers.file.filename=/certs/certificates.toml",
          "--log.level=DEBUG"
        ]
        volumes = [
          "/certs:/certs",
        ]
      }
    }
  }
}
