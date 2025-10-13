#brew install velero

helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
helm repo update


helm upgrade --install velero vmware-tanzu/velero \
--namespace velero \
--create-namespace \
 -f values.yaml

helm repo add otwld https://helm.otwld.com/
helm repo update


kubectl apply -f secret.yaml
kubectl apply -f ingress.yaml


helm upgrade --install velero-ui otwld/velero-ui \
-n velero \
--create-namespace \
-f values-ui.yaml





#https://github.com/vmware-tanzu/helm-charts/blob/main/charts/velero/values.yaml

#   kubectl -n velero logs deploy/velero | grep "error"