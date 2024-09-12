

web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

web_ingress_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"

certs_dir="/opt/neuraldb_enterprise/certs"

$web_ingress_ssh_command <<EOF
    sudo mkdir -p $certs_dir
    cd $certs_dir

    if yum list available openssl11 &> /dev/null
    then
        OPENSSL_BIN="sudo openssl11"
        sudo yum install -y openssl11
    elif yum list available openssl &> /dev/null
    then
        OPENSSL_BIN="sudo openssl"
        sudo yum install -y openssl
    else
        echo "Neither openssl11 nor openssl is available in yum repositories."
    fi
    \$OPENSSL_BIN req -x509 -newkey rsa:4096 -keyout traefik.key -out traefik.crt -days 365 -nodes -subj "/CN=NEURALDB ENTERPRISE CERT" -addext "subjectAltName = IP:$web_ingress_public_ip"

    cat <<EOT | sudo tee certificates.toml
[tls.stores]
  [tls.stores.default]
    [tls.stores.default.defaultCertificate]
      certFile = "/certs/traefik.crt"
      keyFile = "/certs/traefik.key"
[http]
  [http.routers]
    [http.routers.nomad]
      rule = "PathPrefix(`/ui`) || PathPrefix(`/v1`)"
      service = "nomad"
      [http.routers.nomad.middlewares]
        headers = "nomad-headers"

  [http.services]
    [http.services.nomad]
      [http.services.nomad.loadBalancer]
        passHostHeader = true
        [[http.services.nomad.loadBalancer.servers]]
          url = "http://172.17.0.1:4646"

  [http.middlewares]
    [http.middlewares.nomad-headers]
      [http.middlewares.nomad-headers.headers]
        hostsProxyHeaders = ["X-Forwarded-For"]

[tcp]
  [tcp.routers]
    [tcp.routers.nomad-ws]
      entryPoints = ["websecure"]
      rule = "HostSNI(`*`)"
      service = "nomad-ws"

  [tcp.services]
    [tcp.services.nomad-ws]
      [tcp.services.nomad-ws.loadBalancer]
        [[tcp.services.nomad-ws.loadBalancer.servers]]
          address = "172.17.0.1:4646"

[websocket]
  [websocket.middlewares]
    [websocket.middlewares.nomad-ws]
      [websocket.middlewares.nomad-ws.headers]
        customRequestHeaders = {"Origin" = "${scheme}://${host}"}
EOT

EOF