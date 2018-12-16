import decimal
import json
import time
import csv
import requests
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
        results = None
        while True:
            if status is False:
                message = chaims
                break
            username = chaims["cognito:username"]
            json_body = json.loads(event['body'], encoding="utf8")
            dataset_id = json_body['id']
            offset = json_body['offset']
            limit = json_body['limit']
            if dataset_id is None or offset is None or limit is None:
                message = "Missing parameter"
                break
            # Check offset and limit
            if  offset < 0 or limit <= 0:
                message = "The offset must >=0, the limit must be >0"
                break
            offset += 1  # skip header
            # Check dataset
            response = table.get_item(
                Key={
                    'uid': dataset_id,
                    'row': 0
                }
                # FilterExpression=Attr('owner').eq(username) | Attr('partner').contains(username)
            )
            if response is None or 'Item' not in response:
                message = "Dataset dose not exists"
                break
            if response['Item']['owner'] != username and username not in response['Item']['partner']:
                message = "You don't have permission to do this"
                break
            header = response['Item']['col']
            response = table.query(
                KeyConditionExpression=Key('uid').eq(dataset_id) & Key('row').between(offset, offset + limit),
            )
            if response is None or 'Items' not in response:
                message = "No data"
                break
            items = response['Items']
            results = {'header': header}
            records = []
            for item in items:
                records.append({"id": item['row'], "values": item['col']})
            results['records'] = records
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
                "data": results,
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
    token = "eyJraWQiOiJVZ0VBeGNJTmlvQktPbWVubjJhN3FOd1pzZWVVdzVScDd0MFZXTU9PV0xzPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzYmJjNmVkOC03MWUxLTQyZTktYTNiNi0xNjM0N2I1NWNmZTQiLCJhdWQiOiJqMWF2MzhnNDRtZ3BtOG41NGp2cm1xYTZnIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImV2ZW50X2lkIjoiMjc1Y2EyOWYtZmViOC0xMWU4LWFlMTAtZGRlYmE4Yjg2ZjEwIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1NDQ2OTI3NTIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1ub3J0aGVhc3QtMS5hbWF6b25hd3MuY29tXC9hcC1ub3J0aGVhc3QtMV9jNXcwb1BQRUQiLCJjb2duaXRvOnVzZXJuYW1lIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIiwiZXhwIjoxNTQ0NzYyNDQwLCJpYXQiOjE1NDQ3NTg4NDAsImVtYWlsIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIn0.eI6NyHg8PlcgfI12w4ZT7OryNzD-_fCwn623YtJRzlHq-tzHoqGTTF16Vo8Tvrd5gNykqy7hpioxtvo_FqAMJEAJRdud4QoxrXYrPy4bv_rrS786Z-VkAC8Dww5_6ZtiQMRCHuY_oAGigGXakrI0reBKi-jU9Uz0zZpAHWRJdfXRW_myCBT1vxQu97pvFqZpxI8MgEyRI5Cr6iGJy3aVF1kdj-f4p7ufzs9my9f7gGf8Rd-0E489DDj2VnBSRYq_wZi4xHheT8cJC-7AJr0VU2ZIBYZkJDL_Lo5kID9QCgMpgrzNc87QdrRUkh-zudJ1EkfruDFxZ99b27A7sYNe1w"
    event = {'resource': '/api/test', 'path': '/api/test', 'httpMethod': 'POST',
             'headers': {'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate, br',
                         'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.7',
                         'Authorization': token,
                         'CloudFront-Forwarded-Proto': 'https', 'CloudFront-Is-Desktop-Viewer': 'true',
                         'CloudFront-Is-Mobile-Viewer': 'false', 'CloudFront-Is-SmartTV-Viewer': 'false',
                         'CloudFront-Is-Tablet-Viewer': 'false', 'CloudFront-Viewer-Country': 'JP',
                         'content-type': 'application/json', 'dnt': '1',
                         'Host': 'jd8mxu2ri4.execute-api.ap-northeast-1.amazonaws.com',
                         'origin': 'https://s3-ap-northeast-1.amazonaws.com',
                         'Referer': 'https://s3-ap-northeast-1.amazonaws.com/serverless-zb/user.html',
                         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
                         'Via': '2.0 e49884ec57e6715e61e8e8791a944877.cloudfront.net (CloudFront)',
                         'X-Amz-Cf-Id': 'QiAu1CZcpGIK2RyAjebj_uc1cXTAtq2qMNVOHh2RLe60-_PoyG808w==',
                         'X-Amzn-Trace-Id': 'Root=1-5c120e80-a53212fcce6cbe3cf7a7ce4a',
                         'X-Forwarded-For': '193.38.139.82, 70.132.40.89', 'X-Forwarded-Port': '443',
                         'X-Forwarded-Proto': 'https'},
             'multiValueHeaders': {'Accept': ['*/*'], 'Accept-Encoding': ['gzip, deflate, br'],
                                   'Accept-Language': ['zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.7'],
                                   'Authorization': [token],
                                   'CloudFront-Forwarded-Proto': ['https'],
                                   'CloudFront-Is-Desktop-Viewer': ['true'],
                                   'CloudFront-Is-Mobile-Viewer': ['false'],
                                   'CloudFront-Is-SmartTV-Viewer': ['false'],
                                   'CloudFront-Is-Tablet-Viewer': ['false'], 'CloudFront-Viewer-Country': ['JP'],
                                   'content-type': ['application/json'], 'dnt': ['1'],
                                   'Host': ['jd8mxu2ri4.execute-api.ap-northeast-1.amazonaws.com'],
                                   'origin': ['https://s3-ap-northeast-1.amazonaws.com'],
                                   'Referer': ['https://s3-ap-northeast-1.amazonaws.com/serverless-zb/user.html'],
                                   'User-Agent': [
                                       'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'],
                                   'Via': ['2.0 e49884ec57e6715e61e8e8791a944877.cloudfront.net (CloudFront)'],
                                   'X-Amz-Cf-Id': ['QiAu1CZcpGIK2RyAjebj_uc1cXTAtq2qMNVOHh2RLe60-_PoyG808w=='],
                                   'X-Amzn-Trace-Id': ['Root=1-5c120e80-a53212fcce6cbe3cf7a7ce4a'],
                                   'X-Forwarded-For': ['193.38.139.82, 70.132.40.89'], 'X-Forwarded-Port': ['443'],
                                   'X-Forwarded-Proto': ['https']},
             'queryStringParameters': None,
             'multiValueQueryStringParameters': None, 'pathParameters': None, 'stageVariables': None,
             'requestContext': {'resourceId': 'tybalc', 'resourcePath': '/api/test', 'httpMethod': 'POST',
                                'extendedRequestId': 'R1c0IFSEtjMFVnA=',
                                'requestTime': '13/Dec/2018:07:47:12 +0000',
                                'path': '/beta/api/test', 'accountId': '802192806509', 'protocol': 'HTTP/1.1',
                                'stage': 'beta', 'domainPrefix': 'jd8mxu2ri4', 'requestTimeEpoch': 2504687232892,
                                'requestId': '4d8f9c17-feab-11e8-9afd-5deefcc4d066',
                                'identity': {'cognitoIdentityPoolId': None, 'accountId': None,
                                             'cognitoIdentityId': None, 'caller': None, 'sourceIp': '193.38.139.82',
                                             'accessKey': None, 'cognitoAuthenticationType': None,
                                             'cognitoAuthenticationProvider': None, 'userArn': None,
                                             'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
                                             'user': None},
                                'domainName': 'jd8mxu2ri4.execute-api.ap-northeast-1.amazonaws.com',
                                'apiId': 'jd8mxu2ri4'},
             'body': "{\"id\": \"lvyilin48@foxmail.com#test.csv\",\"offset\":0, \"limit\":10 }",
             'isBase64Encoded': False}
    handler(event, None)
