job "modelbazaar" {
  datacenters = ["dc1"]

  type = "service"

  group "modelbazaar" {
    count = 1

    network {
       port "modelbazaar-http" {
         to = 80
       }
    }

    service {
      name = "modelbazaar"
      port = "modelbazaar-http"
      provider = "nomad"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.modelbazaar-http.rule=PathPrefix(`/`)",
        "traefik.http.routers.modelbazaar-http.priority=1"
      ]
    }

    task "server" {

      driver = "docker"

      template {
        destination = "${NOMAD_SECRETS_DIR}/env.vars"
        env         = true
        change_mode = "restart"
        data        = <<EOF
{{- with nomadVar "nomad/jobs" -}}
TASK_RUNNER_TOKEN = {{ .task_runner_token }}
{{- end -}}
EOF
      }

      env {
        DATABASE_URI = "{{ SQL_URI }}"
        PUBLIC_MODEL_BAZAAR_ENDPOINT = "http://{{ PUBLIC_SERVER_IP }}/"
        PRIVATE_MODEL_BAZAAR_ENDPOINT = "http://{{ PRIVATE_SERVER_IP }}/"
        LICENSE_PATH = "/model_bazaar/license/ndb_enterprise_license.json"
        NOMAD_ENDPOINT = "http://172.17.0.1:4646/"
        SHARE_DIR = "{{ SHARE_DIR }}"
        JWT_SECRET = "{{ JWT_SECRET }}"
        ADMIN_USERNAME =  "{{ ADMIN_USERNAME }}"
        ADMIN_MAIL = "{{ ADMIN_MAIL }}"
        ADMIN_PASSWORD = "{{ ADMIN_PASSWORD }}"
        AUTOSCALING_ENABLED = "{{ AUTOSCALING_ENABLED }}"
        AUTOSCALER_MAX_COUNT = "{{ AUTOSCALER_MAX_COUNT }}"
        GENAI_KEY = "{{ GENAI_KEY }}"

        TASK_RUNNER_TOKEN = "${TASK_RUNNER_TOKEN}"
      }

      config {
        image = "neuraldbenterprise.azurecr.io/model_bazaar_s3support:latest"
        ports = ["modelbazaar-http"]
        group_add = ["4646"]
        auth {
          username = "neuraldb-enterprise-pull-s3-streaming"
          password = "XXIpWrFv6MreHf6Ds+U/k85oY4YsooPfY702K4Jv3w+ACRD7zMiw"
          server_address = "neuraldbenterprise.azurecr.io"
        }
        volumes = [
          "{{ SHARE_DIR }}:/model_bazaar"
        ]
      }

      resources {
        cpu    = 1000
        memory = 1000

      }
    }
  }
}
