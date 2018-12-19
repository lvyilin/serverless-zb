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
from io import StringIO
from urllib.parse import quote_plus

region = 'ap-northeast-1'
userpool_id = 'ap-northeast-1_c5w0oPPED'
app_client_id = 'j1av38g44mgpm8n54jvrmqa6g'
keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(region, userpool_id)

response = requests.get(keys_url)
keys = response.json()['keys']

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
table = dynamodb.Table('ZBDataset')

s3 = boto3.client('s3', region_name='ap-northeast-1')
bucket_name = 'serverless-zb-data'
bucket_url = 'https://s3-ap-northeast-1.amazonaws.com/serverless-zb-data/'


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
        link = ""
        while True:
            if status is False:
                message = chaims
                break
            username = chaims["cognito:username"]
            query_params = event['queryStringParameters']
            dataset_id = query_params['id']
            if dataset_id is None:
                message = "Missing parameter"
                break
            # Check dataset
            response = table.get_item(
                Key={
                    'uid': dataset_id,
                    'row': 0
                }
            )
            if response is None or 'Item' not in response:
                message = "Dataset dose not exists"
                break
            if response['Item']['owner'] != username and username not in response['Item']['partner']:
                message = "You don't have permission to do this"
                break
            response = table.query(
                ProjectionExpression="col, tag",
                # ProjectionExpression="#r, col, tag",
                # ExpressionAttributeNames={"#r": "row"},
                KeyConditionExpression=Key('uid').eq(dataset_id),
            )
            if response is None or 'Items' not in response:
                message = "No data"
                break
            results = []
            for item in response['Items']:
                if 'tag' not in item:
                    results.append(item['col'])
                else:
                    results.append(item['col'] + item['tag'])
            s3_path = username + "/" + dataset_id + ".csv"
            f = StringIO()
            writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for rec in results:
                writer.writerow(rec)
            s3.put_object(Bucket=bucket_name, Key=s3_path, Body=f.getvalue())
            link = bucket_url + s3_path
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
                "message": message,
                "data": {
                    "link": quote_plus(link,safe=":/")
                }
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
    token = 'eyJraWQiOiJVZ0VBeGNJTmlvQktPbWVubjJhN3FOd1pzZWVVdzVScDd0MFZXTU9PV0xzPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzYmJjNmVkOC03MWUxLTQyZTktYTNiNi0xNjM0N2I1NWNmZTQiLCJhdWQiOiJqMWF2MzhnNDRtZ3BtOG41NGp2cm1xYTZnIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImV2ZW50X2lkIjoiNGVlZGZmN2ItMDNhOC0xMWU5LWJiMmUtMzcwMGNmOGFhODE4IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1NDUyMzU3MDIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1ub3J0aGVhc3QtMS5hbWF6b25hd3MuY29tXC9hcC1ub3J0aGVhc3QtMV9jNXcwb1BQRUQiLCJjb2duaXRvOnVzZXJuYW1lIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIiwiZXhwIjoxNTQ1MjM5MzAyLCJpYXQiOjE1NDUyMzU3MDIsImVtYWlsIjoibHZ5aWxpbjQ4QGZveG1haWwuY29tIn0.nWCDKgLXV-W5amrTD9Y4lifxGrfq_IU-nKbq_ZS8f7LUbAqe2PyR5X3oT0HLDzNOvTPEYhnEw56skrPBUkKdvxdecozQgIZoHqotYr3P3920dXvME4WUVd5N-VFyCC9iEufdQ2zDAavAHF5zlkPMCV-1hxx0nLhDw-NNWZFFyeHSzfdkSCjvqjNeLwO2DHSdR6l-4zRZXmcEFCUToCKIlTRqDqpoctsNxHGmWvz3LtVeX9jF7JIxnEZRd8zBXgdK3Hycph3hHV08GW41Gn4axFFi73Lib2f3s0eKYqnuwC9Mn4doExAOCbqNYUdIhHpa1ofKOnzBRu54amiWdE-qIA'
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
             'queryStringParameters': {"id": "lvyilin48@foxmail.com#NER"},
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
             'isBase64Encoded': False}
    handler(event, None)

