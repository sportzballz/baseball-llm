import boto3
from  common.util import *

# Create SQS client
sqs = boto3.client('sqs', region_name='us-east-1')

queue_url = 'https://sqs.us-east-1.amazonaws.com/716418748259/baseball-backtest'

year = '2024'
teams = get_teams_list()

for team in teams:

    # Send message to SQS queue180
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'year': {
                'DataType': 'String',
                'StringValue': year
            },
            'team_name': {
                'DataType': 'String',
                'StringValue': team.name
            },
            'team_id': {
                'DataType': 'String',
                'StringValue': str(team.id)
            }
        },
        MessageBody=(team.name + year)
    )
    print(response['MessageId'])
