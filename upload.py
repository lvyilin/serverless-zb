import requests
import json
import time
import csv
from jose import jwk, jwt
from jose.utils import base64url_decode
import boto3
import base64

region = 'ap-northeast-1'
userpool_id = 'ap-northeast-1_c5w0oPPED'
app_client_id = 'j1av38g44mgpm8n54jvrmqa6g'
keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(region, userpool_id)

response = requests.get(keys_url)
keys = response.json()['keys']

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
table = dynamodb.Table('ZBDataset')


def verify_token(token):
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break
    if key_index == -1:
        return False, 'Public key not found in jwks.json'
    public_key = jwk.construct(keys[key_index])
    message, encoded_signature = str(token).rsplit('.', 1)
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        return False, 'Signature verification failed'
    claims = jwt.get_unverified_claims(token)
    if time.time() > claims['exp']:
        return False, 'Token is expired'
    if claims['aud'] != app_client_id:
        return False, 'Token was not issued for this audience'
    # print(claims)
    return True, claims


def handler(event, context):
    try:
        status, chaims = verify_token(event['headers']['Authorization'])
        flag = False
        message = ""
        while True:
            if status is False:
                message = chaims
                break
            username = chaims["cognito:username"]
            multipart = event['body']
            content_type = event['headers']['content-type']
            boundary = "--" + content_type.split(';')[1][1:].lstrip("boundary=")
            parts = multipart.split(''.join(('\r\n', boundary)))
            results = []
            for part in parts:
                ls = part.split("\r\n\r\n")
                if len(ls) >= 2:
                    results.append(ls[1])
            dataset_name = results[1]
            dataset_csv = bytes(results[0], encoding='utf8')
            if dataset_name is None or dataset_csv is None:
                message = "Missing parameter"
                break
            dataset_uid = username + "#" + dataset_name
            if dataset_csv is "":
                message = "Empty data"
                break
            if 'Item' in table.get_item(Key={'uid': dataset_uid, 'row': 0}):
                message = "Dataset name already exists"
                break
            lines_csv = str(dataset_csv, encoding='utf8').strip().split('\n')
            data_csv = csv.reader(lines_csv)
            with table.batch_writer() as batch:
                heading = next(data_csv)
                batch.put_item(Item={
                    'uid': dataset_uid,
                    'row': 0,
                    'col': heading,
                    'name': dataset_name,
                    'owner': username,
                    'partner': [],
                    'size': len(lines_csv) - 1,
                })
                for i, record in enumerate(data_csv):
                    batch.put_item(Item={'uid': dataset_uid,
                                         'row': i + 1,
                                         'col': record})
            flag = True
            break
        if flag is False:
            response_body = {
                "status": "error",
                "message": message
            }
        else:
            response_body = {
                "status": "success",
                "message": message
            }
    except Exception as e:
        response_body = {
            "status": "error",
            "message": str(e)
        }
    print(response_body)
    return {
        'statusCode': 200,
        'body': json.dumps(response_body),
        'headers': {
            'Access-Control-Allow-Origin': '*'
        }
    }


if __name__ == '__main__':
    with open('demo.csv', 'r') as f:
        token = 'eyJraWQiOiJVZ0VBeGNJTmlvQktPbWVubjJhN3FOd1pzZWVVdzVScDd0MFZXTU9PV0xzPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzYmJjNmVkOC03MWUxLTQyZTktYTNiNi0xNjM0N2I1NWNmZTQiLCJhdWQiOiJqMWF2MzhnNDRtZ3BtOG41NGp2cm1xYTZnIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImV2ZW50X2lkIjoiMjc1Y2EyOWYtZmViOC0xMWU4LWFlMTAtZGRlYmE4Yjg2ZjEwIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1NDQ2OTI3NTIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1ub3J0aGVhc3QtMS5hbWF6b25hd3MuY29tXC9hcC1ub3J0aGVhc3QtMV9jNXcwb1BQRUQiLCJjb2duaXRvOnVzZXJuYW1lIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIiwiZXhwIjoxNTQ0NzU4NTUyLCJpYXQiOjE1NDQ3NTQ5NTIsImVtYWlsIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIn0.UrNMIxTo6fi0y4g5YlNbE6BfW-t5AldYFwnWJG029xz75CXuC4ouEOyQc2FHKXK7_TElIGsYXdQo006IWoJbvplZAT7sS1ub7TjfleUSPw06lljTqe0Wr3lDTsahyaQ6sj6fro4CI40Kl0p2XGdD8_yqCGfjlIVZdSwk9blom5UZfWZF0Q3lsBw2HRJDQzPAN28G4d2_5F347ay-spG4scpwITQ_-PNjcECoUWAqPl2RwlwSkp9ENhTad7pq8ouU5prBWQIvDpvJKKya27FOoEp_Jszce3p9iCR_7zHAtLQghzDRodx-KUXi-trwtNGNZeq6YmvteZ9cQYHzq6mSMQ'
        event = {
            "headers": {
                "Authorization": token,
                'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryu0mdLExLQgJNolBt',
            },
            "body": '------WebKitFormBoundaryu0mdLExLQgJNolBt\r\nContent-Disposition: form-data; name="data"; filename="demo.csv"\r\nContent-Type: application/vnd.ms-excel\r\n\r\n23,",","""",2,\'\'\'\'\r\n5228,������,����ı,8,������ץס��������ı�����Ļ��ᣬ\r\n492,˹�ٷҡ�����,����������,1,˹�ٷҡ�����\u0378��״����������Լ��ա�������Ӳ���\r\n4779,������,����,8,�������ͺ������������Ϸ����������������壬\r\n\r\n------WebKitFormBoundaryu0mdLExLQgJNolBt\r\nContent-Disposition: form-data; name="name"\r\n\r\nbbb\r\n------WebKitFormBoundaryu0mdLExLQgJNolBt--\r\n',
            "isBase64Encoded": True}
    handler(event, None)
