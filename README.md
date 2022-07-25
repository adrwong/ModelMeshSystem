Follow this to deploy ModelMesh serving + Etcd Server + KServe + Cert manager + Knative serving + Istio networking layer

Requirements:

1. Kubernetes v1.22 with Rook-Ceph installed + Object Store installed + Bucket initiated
2. Helm 3.2.0+
3. Cluster created with microk8s
4. kubctl of course

Versions:
KServe = v0.8
Knative = v1.6.0
Etcd = 8.3.4
ModelMesh = Release 0.9

# Session 1: Install prerequisites for KServe (i.e. Installing Knative + Istio networking + Cert manager)

Apply the followings in order
kubectl apply -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.6.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.6.0/istio.yaml

kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.6.0/net-istio.yaml

configure domain name by executing:
kubectl -n knative-serving edit configmap/config-domain

add `your-domain.xyz: ""` under data to get rid of the exmaple.com you may see
see Configure DNS session in https://knative.dev/docs/install/yaml-install/serving/install-serving-with-yaml/#verify-the-installation if you have real DNS

use `kubectl --namespace istio-system get service istio-ingressgateway` and `kubectl get pods -n knative-serving` to make sure all the svc and pods are running before proceding to the next step.

Next, install Cert manager: https://cert-manager.io/docs/installation/

Make sure everything is up and running before Session 2.

# Session 2: KServe installation and Inference service test

Apply the following:

1. `kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve.yaml`
2. `kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.8.0/kserve-runtimes.yaml`

# Testing 1: KServe functionality

1. run `kubectl -n kserve-test apply -f test1/firstInference.yaml` to deploy a testing inferenceservice (isvc) using a simple iris model in sklearn (.jolib) stored in GCP bucket.
2. check `kubectl get inferenceservices -n kserve-test` for isvc ready status
   check https://knative.dev/docs/serving/troubleshooting/debugging-application-issues/ for debugging if any issues arose
3. check `kubectl get svc istio-ingressgateway -n istio-system` for istio status
   note: `minikube tunnel` would help if you are using minikube
4. run (if ingressgateway is a loadbalancer, check https://kserve.github.io/website/0.8/get_started/first_isvc/#5-perform-inference otherwise)
   `export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')`
   `export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')`

   `SERVICE_HOSTNAME=$(kubectl get inferenceservice sklearn-iris -n kserve-test -o jsonpath='{.status.url}' | cut -d "/" -f 3)`

5. run `curl -v -H "Host: ${SERVICE_HOSTNAME}" http://${INGRESS_HOST}:${INGRESS_PORT}/v1/models/sklearn-iris:predict -d @./iris-input-isvc.json`
   you should see something like `{"predictions": [2, 1]}` in the response message if successful

# Testing 2: Test Rook Ceph object store bucket connectivity

1. create a bucket to store your models, each bucket can hold multiple models as long as they are in different directories.
2. retrieve the bucket's owner's ACCESS_KEY, ACCESS_SECRET and bucket name for later use
3. edit and apply s3secret.yaml with `kubectl -n kserve-test apply -f <FILENAME>`
4. `kubectl -n kserve-test apply -f test2/s3sa.yaml`
5. upload your model folder to your bucket. For experiment purpose, just go to test2 folder (cd test2) and run `python s3access.py` and the iris sklearn model we used in test 1 is then uploaded to the bucket in our cluster.
6. use `kubectl -n kserve-test apply -f test2/firsts3isvc.yaml` to build a isvc with the model in ceph.
7. run `SERVICE_HOSTNAME=$(kubectl get inferenceservice sklearn-iris -n mms-sklearn -o jsonpath='{.status.url}' | cut -d "/" -f 3)`
   run step5 in test1 again (you may need to change the input json file path)

# Session 3: Install prerequisites for ModelMesh (i.e. Etcd server)

1. run `kubectl get StorageClass -A` to choose the StorageClass you want for etcd server setup, change global.storageClass in etcd-settings.yaml to the StorageClass of yours.
2. run `kubectl create namespace etcd` and `kubectl config set-context --current --namespace=etcd`
3. run `helm repo add bitnami https://charts.bitnami.com/bitnami` and `helm install mms bitnami/etcd -f etcd-settings.yaml` (note: mms is the release name, can be customized)
   save the output for later use
   checkout https://artifacthub.io/packages/helm/bitnami/etcd for details
4. edit the fields in etcd-config.json with the output you got in the last step, default userid is root

# Session 4: Install ModelMesh

1. run
   `RELEASE=release-0.9`
   `git clone -b $RELEASE --depth 1 --single-branch https://github.com/kserve/modelmesh-serving.git`
   `cd modelmesh-serving`
   `kubectl create namespace modelmesh-serving`
   `./scripts/install.sh --namespace modelmesh-serving`
2. run `kubectl create secret generic model-serving-etcd --from-file=etcd_connection=etcd-config.json`
3. edit fields in k3secret.json for your own settings (note: leave region = us-south if your have no idea)
4. convert k3secret.json to a base64 string and append the string to under data as `s3Key: <your b64 string>` using `kubectl -n modelmesh-serving edit secrets storage-config`

# Testing 3: Test isvc with ModelMesh

Reference: https://github.com/kserve/modelmesh-serving/tree/release-0.9/docs/predictors

1. run `kubectl -n modelmesh-serving apply -f test3/firsts3.yaml` to create the isvc using ModelMesh
2. use `kubectl -n modelmesh-serving get isvc` to check isvc availability
3. use `kubectl -n modelmesh-serving logs modelmsesh-controller-xxxx` to debug
4. run `kubectl port-forward service/modelmesh-serving 8033` to expose port
5. run `./grpcurl -plaintext -proto kfs_inference_v2.proto localhost:8033 list` to check if the model can be accessed.
6. use `./grpcurl -plaintext -proto kfs_inference_v2.proto -d '{ "model_name": "mms-sklearn", "inputs": [ { "name": "predict", "shape": [1, 4], "datatype": "FP32", "contents": {"fp32_contents": [6.8, 2.8, 4.8, 1.9]} } ] }' localhost:8033 inference.GRPCInferenceService.ModelInfer` for a quick inference

Done!

checkout the mms-sandbox folder for grpc_predict_v2.proto for an inference application
checkout the mms-sandbox/grpc-predict folder for client.py for an example client application

MMS API Ref: https://github.com/kserve/kserve/blob/master/docs/predict-api/v2/required_api.md#grpc

MMS all Ref: https://github.com/kserve/modelmesh-serving/tree/release-0.9/docs

Model formats: https://github.com/kserve/modelmesh-serving/tree/main/docs/model-formats
