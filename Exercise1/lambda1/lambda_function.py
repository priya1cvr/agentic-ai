import boto3, uuid

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("orders")

def lambda_handler(event, context):
    for record in event["Records"]:
        print("Received record:", record)
        payload = record["body"]
        print("Payload:", str(payload))
        table.put_item(
            Item={
                "orderID": str(uuid.uuid4()),
                "order": payload
            }
        )