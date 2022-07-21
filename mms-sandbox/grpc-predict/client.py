import argparse
import random
import json
from PIL import Image
from numpy import asarray

from itsdangerous import base64_decode

import grpc_predict_v2_pb2 as pb
import grpc_predict_v2_pb2_grpc as pb_grpc
import grpc

from sklearn import datasets
import base64
import tensorflow as tf

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Perform a gRPC inference request')
    parser.add_argument('model', type=str, help='Name of model resource')
    args = parser.parse_args()

    channel = grpc.insecure_channel('localhost:8033')
    infer_client = pb_grpc.GRPCInferenceServiceStub(channel)

    input = {}
    b64 = ""
    with open('flower-input-isvc.json', 'r') as inp:
        inp_js = json.load(inp)
        b64 = inp_js['instances'][0]['image_bytes']['b64']
        input = inp_js['instances'][0]
    # print(input)

    # with open('flower.png', 'wb+') as img:
    #     img.write(base64.b64decode(b64))

    # image = Image.open('flower.png')
    # data = asarray(image)
    # print(type(data))
    # print(data.shape)

    # input_data = data.reshape((1, -1))
    # print(input_data)
    # print(input_data.shape[1])
    # Load sample digit image from sklearn datasets.
    # digits = datasets.load_digits()
    # num_digits = len(digits.images)
    # rand_int = random.randint(0, num_digits-1)
    # random_digit_image = digits.images[rand_int]
    # random_digit_label = digits.target[rand_int]
    # print(type(random_digit_image))
    # data = random_digit_image.reshape((1, -1))
    # print(data)

    data = [6.8, 2.8, 4.8, 1.9]

    tensor_contents = pb.InferTensorContents(fp32_contents=data)

    infer_input = pb.ModelInferRequest().InferInputTensor(
        name="input-0",
        shape=[1, 4],
        datatype="FP32",
        contents=tensor_contents
    )

    inputs = [infer_input]
    request = pb.ModelInferRequest(model_name=args.model, inputs=inputs)

    results, call = infer_client.ModelInfer.with_call(request=request)
    print(results)
    # print('Expected Result: {}'.format(random_digit_label))
