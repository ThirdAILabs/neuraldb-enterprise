

web_ingress_public_ip=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.public_ip' config.json)
web_ingress_ssh_username=$(jq -r '.nodes[] | select(has("web_ingress")) | .web_ingress.ssh_username' config.json)

web_ingress_ssh_command="ssh -o StrictHostKeyChecking=no $web_ingress_ssh_username@$web_ingress_public_ip"

certs_dir="/opt/neuraldb_enterprise/certs"

$web_ingress_ssh_command <<EOF
    sudo apt install openssl
    sudo mkdir -p $certs_dir
    cd $certs_dir
    sudo openssl req -x509 -newkey rsa:4096 -keyout traefik.key -out traefik.crt -days 365 -nodes -subj "/CN=NEURALDB ENTERPRISE CERT" -addext "subjectAltName = IP:$web_ingress_public_ip"

    cat <<EOT | sudo tee certificates.toml
[tls.stores]
  [tls.stores.default]
    [tls.stores.default.defaultCertificate]
      certFile = "/certs/traefik.crt"
      keyFile = "/certs/traefik.key"
EOT

EOF
