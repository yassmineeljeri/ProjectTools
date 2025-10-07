kubectl create namespace monitoring
kubectl apply -f prometheus-serviceaccount
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack -n monitoring -f prometheus-values.yaml
