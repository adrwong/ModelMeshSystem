import argparse
from functools import partial
import os
import sys

from PIL import Image
import numpy as np

import grpc_predict_v2_pb2 as pb
import grpc_predict_v2_pb2_grpc as pb_grpc
import grpc

# Can use this for sending inference requests through ModelMesh for ONNX DenseNet:
# https://github.com/triton-inference-server/server/tree/main/docs/examples/model_repository/densenet_onnx
#
# Adopted from https://github.com/triton-inference-server/client/blob/main/src/python/examples/image_client.py

LABELS_FILE = 'densenet_labels.txt'


def dtype_to_np_dtype(dtype):
    if dtype == "BOOL":
        return bool
    elif dtype == "INT8":
        return np.int8
    elif dtype == "INT16":
        return np.int16
    elif dtype == "INT32":
        return np.int32
    elif dtype == "INT64":
        return np.int64
    elif dtype == "UINT8":
        return np.uint8
    elif dtype == "UINT16":
        return np.uint16
    elif dtype == "UINT32":
        return np.uint32
    elif dtype == "UINT64":
        return np.uint64
    elif dtype == "FP16":
        return np.float16
    elif dtype == "FP32":
        return np.float32
    elif dtype == "FP64":
        return np.float64
    elif dtype == "BYTES":
        return np.object_
    return None


def preprocess(img, dtype, c, h, w, scaling):
    if c == 1:
        sample_img = img.convert('L')
    else:
        sample_img = img.convert('RGB')

    resized_img = sample_img.resize((w, h), Image.Resampling.BILINEAR)
    resized = np.array(resized_img)
    if resized.ndim == 2:
        resized = resized[:, :, np.newaxis]

    npdtype = dtype_to_np_dtype(dtype)
    typed = resized.astype(npdtype)

    if scaling == 'INCEPTION':
        scaled = (typed / 127.5) - 1
    elif scaling == 'VGG':
        if c == 1:
            scaled = typed - np.asarray((128,), dtype=npdtype)
        else:
            scaled = typed - np.asarray((123, 117, 104), dtype=npdtype)
    else:
        scaled = typed

    ordered = np.transpose(scaled, (2, 0, 1))
    return ordered


def postprocess(results, output_name):
    """
    Post-process results to show classifications based on label file.
    """
    output_array = np.frombuffer(results.raw_output_contents[0], dtype=np.float32)
    output_array = output_array.reshape([1000])
    indices = np.argpartition(output_array, -3)[-3:]

    print('Results:')
    with open(LABELS_FILE) as f:
        lines = f.read().split('\n')
        for _, index in enumerate(indices[::-1]):
            print(f'{lines[index]}: {output_array[index]:.5f}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Perform a gRPC inference request')
    parser.add_argument('model', type=str, help='Name of model resource')
    parser.add_argument('image_path', type=str, help='Path of the image')
    args = parser.parse_args()

    max_batch_size = 0
    input_name = 'data_0'
    output_name = 'fc6_1'
    c, h, w = 3, 224, 224
    dtype = 'FP32'
    scaling = 'INCEPTION'

    img = Image.open(args.image_path)

    processed_img = preprocess(img, dtype, c, h, w, scaling)
    channel = grpc.insecure_channel('localhost:8033')
    infer_client = pb_grpc.GRPCInferenceServiceStub(channel)

    tensor_contents = pb.InferTensorContents(fp32_contents=processed_img.flatten())

    infer_input = pb.ModelInferRequest().InferInputTensor(
        name=input_name,
        shape=[c, h, w],
        datatype=dtype,
        contents=tensor_contents
    )

    inputs = [infer_input]
    request = pb.ModelInferRequest(model_name=args.model, inputs=inputs)

    results, call = infer_client.ModelInfer.with_call(request=request)
    postprocess(results, output_name)
