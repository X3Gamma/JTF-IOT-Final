import boto3, botocore
from boto3.dynamodb.conditions import Key, Attr
import sys, json, numpy, datetime, decimal


class GenericEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.generic):
            return numpy.asscalar(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def data_to_json(data):
    json_data = json.dumps(data, cls=GenericEncoder)
    return json_data


def retrieve_from_dynamodb():
    try:
        dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        table = dynamodb.Table('CA2-iot')
        deviceID = 1

        response = table.query(
            KeyConditionExpression = Key('deviceid').eq(deviceID),
                                     #& Key('datetime').begins_with(startdate),
            ScanIndexForward = False
        )

        items = response['Items']
        n = 10  # limit to last 10 items
        data = items[:n]
        data_reversed = data[::-1]

        return data_reversed

    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])


if __name__ == "__main__":
    retrieve_from_dynamodb()
