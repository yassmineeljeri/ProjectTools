helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm upgrade --install falco falcosecurity/falco \
    --namespace falco --create-namespace \
      --values falco-value.yaml