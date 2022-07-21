import io
import os
from boto3.session import Session
from boto3.s3.transfer import TransferConfig

from LoraLogger import logger
logger = logger(__name__, "INFO")


class Ceph3BOTO3():
    def __init__(self):
        # prod credentials
        access_key = 'XXXXXXXXXXXXX'
        secret_key = 'XXXXXXXXXXXXX'
        self.session = Session(aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key)
        # self.url = 'http://rook-ceph-rgw-my-store.rook-ceph/'
        self.url = 'http://127.0.0.1:12345'
        self.s3_client = self.session.client('s3', endpoint_url=self.url)
        self.s3_resource = self.session.resource('s3', endpoint_url=self.url)

    def get_bucket(self):
        buckets = [bucket['Name']
                   for bucket in self.s3_client.list_buckets()['Buckets']]
        print(buckets)
        return buckets

    def create_bucket(self):
        self.s3_client.create_bucket(Bucket='')
        # ACL = 'private', 'public-read', 'public-read-write', 'authenticated-read'
        # self.s3_client.create_bucket(Bucket='new_bucket', ACL='public-read')

    def get_bucket_content(self, bkname):
        bk = self.s3_resource.Bucket(bkname)
        for obj in bk.objects.all():
            print(obj.key)

    def upload_folder(self, folder, bucket):
        config = TransferConfig(multipart_threshold=1024*25, max_concurrency=10,
                                multipart_chunksize=1024*25, use_threads=True)

        # bucket = self.s3_resource.Bucket(bucket)
        print('upload started')
        for subdir, dirs, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(subdir, file)
                print('uploading '+full_path)
                self.s3_client.upload_file(
                    full_path,  # file itself
                    bucket,
                    full_path,  # name
                    Config=config
                )
                print('completed uploading '+full_path)
        print('folder upload completed')

    def upload(self):
        fo = io.BytesIO(b'my data stored as file object in RAM')
        resp = self.s3_client.put_object(
            Bucket='stock2vec-test',
            Key='test.txt',  # target file name
            Body=fo
        )
        # with open('data_shards/cooccurrence/cooccurrence.hdf5', 'rb') as f:
        #     resp = self.s3_client.put_object(
        #         Bucket='stock2vec-test', Key='cooccurrence.hdf5', Body=f)
        #     logger.info('saved cooc matrix: cooccurrence.hdf5')
        #     logger.info(resp)
        # with open('data_shards/cooccurrence/vocab.pkl', 'rb') as f:
        #     resp = self.s3_client.put_object(
        #         Bucket='stock2vec-test', Key='vocab.pkl', Body=f)
        #     logger.info('saved cooc matrix: vocab.pkl')
        #     logger.info(resp)

    def download(self):
        self.s3_resource.meta.client.download_file(
            'stock2vec-test', 'vocab.pkl', './output/data_shards/cooccurrence/vocab.pkl')

    def delete(self, bucket, key):
        self.s3_resource.Object(bucket, key).delete()


if __name__ == "__main__":
    cephs3_boto3 = Ceph3BOTO3()
    cephs3_boto3.upload_folder('sklearn', bucket='models')
