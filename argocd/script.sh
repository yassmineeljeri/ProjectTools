#!/bin/bash
#-e Exit the script immediately if any command fails
#-u Treat unset variables as an error and exit immediately
#-o pipefail Make the entire pipeline fail if any command in it fails.
set -euo pipefail

helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

#https://github.com/argoproj/argo-helm/blob/main/charts/argo-cd/values.yaml
#https://artifacthub.io/packages/helm/argo/argo-cd?modal=values

helm upgrade --install argocd argo/argo-cd \
		--create-namespace  \
  --namespace argocd \
 -f values.yaml


kubectl wait --namespace argocd \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/name=argocd-server \
  --timeout=180s

sleep 90

ARGOCD_ADMIN_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 --decode)

argocd login argocd.devops-tool.com \
  --grpc-web \
  --username admin \
  --password "$ARGOCD_ADMIN_PASSWORD" \
  --skip-test-tls

sleep 90

kubectl apply -f image-updater.yaml


#helm uninstall argocd -n argocd
#kubectl delete ns argocd


#brew install argocd

sudo apt update && sudo apt install -y curl tar

curl -fsSL https://get.helm.sh/helm-v3.17.3-linux-amd64.tar.gz -o helm.tar.gz
tar -zxvf helm.tar.gz
sudo mv linux-amd64/helm /usr/local/bin/helm
rm -rf linux-amd64 helm.tar.gz
helm version
#
#helm completion bash | sudo tee /etc/bash_completion.d/helm > /dev/null
#source /etc/bash_completion


#Install ArgoCD CLI
#VERSION=$(curl --silent "https://api.github.com/repos/argoproj/argo-cd/releases/latest" | grep -Po '"tag_name": "\K.*?(?=")')
#curl -sSL -o argocd "https://github.com/argoproj/argo-cd/releases/download/${VERSION}/argocd-linux-amd64"
#chmod +x argocd
#sudo mv argocd /usr/local/bin/
#argocd version --client
