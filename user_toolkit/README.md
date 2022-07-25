# User's Guide

## Step 1. Push your model to Rook Ceph bucket

Check out s3access.py to see the python class for Rook Ceph Bucket operations.

1. Select or Create your own bucket through RookCeph dashboard, get the ACCESS_KEY and SECRET_KEY of the owner of the bucket
2. Push your model to the bucket, checkout https://github.com/kserve/modelmesh-serving/tree/main/docs/model-formats to correctly specify your model's path/dir format in the bucket.

## Step 2. Create Inference Service

1. Modify firsts3.yaml to your configs
2. Switch to the modelmesh-serving namespace in kubernetes, apply your .yaml by `kubectl -n modelmesh-serving apply -f your_isvc.yaml`
   Note: Ready status can be checked by `kubectl -n modelmesh-serving get isvc`, logs are in modelmesh-controller pod

## Step 3. Inference Test

1. Port-forward modelmesh service by `kubectl -n modelmesh-serving port-forward service/modelmesh-serving 8033` to allow local access to the cluster service
2. modify query `grpcurl -plaintext -proto kfs_inference_v2.proto -d '{ "model_name": "your-model-name", "inputs": [ { "name": "predict", "shape": [1, 4], "datatype": "FP32", "contents": {"fp32_contents": [6.8, 2.8, 4.8, 1.9]} } ] }' localhost:8033 inference.GRPCInferenceService.ModelInfer` and run it to test out your model's accessibility

## Step 4. Client Implementation

1. Adapt grpc-predict/client.py to your settings to implement a client application for model inference
