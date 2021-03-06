import decimal

import requests
import json
import time
import csv
from jose import jwk, jwt
from jose.utils import base64url_decode
import boto3
import base64
from boto3.dynamodb.conditions import Key, Attr

region = 'ap-northeast-1'
userpool_id = 'ap-northeast-1_c5w0oPPED'
app_client_id = 'j1av38g44mgpm8n54jvrmqa6g'
keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(region, userpool_id)

response = requests.get(keys_url)
keys = response.json()['keys']

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
table = dynamodb.Table('ZBDataset')


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


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
            print(event)
            json_body = json.loads(event['body'], encoding="utf8")
            dataset_id = json_body['id']
            partner_id = json_body['partner']
            if dataset_id is None or partner_id is None:
                message = "Missing parameter"
                break
            if dataset_id.split("#")[0] != username:
                message = "You don't have permission to do this"
                break
            # TODO: check partner_id valid
            response = table.get_item(
                Key={
                    'uid': dataset_id,
                    'row': 0
                }
            )
            if response is None or 'Item' not in response:
                message = "Dataset does not exist"
                break
            item = response['Item']
            newitem = item['partner'].copy()
            if partner_id in newitem:
                message = "Partner already exists"
                break
            newitem.append(partner_id)
            response = table.update_item(
                Key={
                    'uid': dataset_id,
                    'row': 0
                },
                UpdateExpression="set partner = :p",
                ExpressionAttributeValues={
                    ':p': newitem,
                },
                ReturnValues="UPDATED_NEW"
            )
            flag = True
            break
        response_body = {
            "status": "success" if flag else "error",
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
        'body': json.dumps(response_body, cls=DecimalEncoder),
        'headers': {
            'Access-Control-Allow-Origin': '*'
        }
    }


if __name__ == '__main__':
    token = 'eyJraWQiOiJVZ0VBeGNJTmlvQktPbWVubjJhN3FOd1pzZWVVdzVScDd0MFZXTU9PV0xzPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzYmJjNmVkOC03MWUxLTQyZTktYTNiNi0xNjM0N2I1NWNmZTQiLCJhdWQiOiJqMWF2MzhnNDRtZ3BtOG41NGp2cm1xYTZnIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImV2ZW50X2lkIjoiMjk0NDc4YmMtMDFhNy0xMWU5LWE4OWYtNjcwODBmZjdjOTM2IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1NDUwMTUzMDcsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1ub3J0aGVhc3QtMS5hbWF6b25hd3MuY29tXC9hcC1ub3J0aGVhc3QtMV9jNXcwb1BQRUQiLCJjb2duaXRvOnVzZXJuYW1lIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIiwiZXhwIjoxNTQ1MDQwMDU1LCJpYXQiOjE1NDUwMzY0NTUsImVtYWlsIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIn0.TBYtAdUfPIAvkC_9HERHuKWOYQwYNJjYWvR3Ri-mVzicvWCsmsA6DjRyrIubTnkul6wD-KjpI01P2OSpmYqg7nttwDDK9OK_Z-nuXv4A_h9NWMGykP62-JUnbxkaNRcLz1CxFUgB-x9qUZ9ryGpxadrqxFAPsLIZMIDvycrnn_raaoCAEg2CZxHTvxJZWV4Rs5TIQczAvteGdStONUkO4Vm4eCxCzdkxEk8qsXv56Ob6LsUfy6lPv3JsSbb_YAMWDuC48Fym1PC5QLF7aFmyKbeSjIkhMuBp1CgbvGK53p5Ft9qvEc3rTISLmheMTtgAp2POMHU6VkMBHquSPKR2JA'
    event = {
        'headers': {
            'Authorization': token
        },
        'queryStringParameters': None,
        'body': '{"id": "lvyilin48@foxmail.com#test.csv","partner":"lvyilin1" }',
        'isBase64Encoded': False}
    handler(event, None)
