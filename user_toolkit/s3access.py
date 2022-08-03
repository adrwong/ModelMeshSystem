import io
import os
from boto3.session import Session
from boto3.s3.transfer import TransferConfig

from LoraLogger import logger
logger = logger(__name__, "INFO")

with open('../es-syns-config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    logger = logger(__name__, config['LOGGERS']['main'])
    config = config['MAIN']

class Ceph3BOTO3():
    def __init__(self, ak=None, sk=None, url=None):
        # prod credentials
        logger.info(ak)
        access_key = ak
        secret_key = sk
        self.session = Session(aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key)

        self.s3_client = self.session.client('s3', endpoint_url=url)
        self.s3_resource = self.session.resource('s3', endpoint_url=url)

    def get_bucket(self):
        buckets = [bucket['Name']
                   for bucket in self.s3_client.list_buckets()['Buckets']]
        print(buckets)
        return buckets

    def create_bucket(self, bkname):
        self.s3_client.create_bucket(Bucket=bkname)
        # ACL = 'private', 'public-read', 'public-read-write', 'authenticated-read'
        # self.s3_client.create_bucket(Bucket='new_bucket', ACL='public-read')

    def delete_bucket(self, bkname):
        self.s3_client.delete_bucket(Bucket=bkname)

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

    def upload_file(self, bkname, from_file_path, bucket_file_path):
        with open(from_file_path, 'rb') as f:
            fo = io.BytesIO(f.read())

        resp = self.s3_client.put_object(
            Bucket=bkname,
            Key=bucket_file_path,  # target file name
            Body=fo
        )
        return resp

    def download_folder(self, bkname, from_bucket_dir, to_dir):
        bucket = self.s3_resource.Bucket(bkname)
        for obj in bucket.objects.filter(Prefix=from_bucket_dir):
            target_path = os.path.join(to_dir, obj.key)
            print(os.path.dirname(target_path))
            if not os.path.exists(os.path.dirname(target_path)):
                os.makedirs(os.path.dirname(target_path))
            bucket.download_file(obj.key, target_path)  # save to same path

    def download_file(self, bkname, from_bucket_path, to_file_path):
        self.s3_resource.meta.client.download_file(
            bkname, from_bucket_path, to_file_path)

    def delete(self, bucket, key):
        self.s3_resource.Object(bucket, key).delete()
        
if __name__ == '__main__':

    ceph = Ceph3BOTO3(ak=config['access_key'], sk=config[
                      'secret_key'], url=config['end_point'])
    ceph.download_folder(bkname='es-synonym',
                         from_bucket_dir='current', to_dir='analysis')
