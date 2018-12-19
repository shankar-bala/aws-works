#!/bin/python

import boto3, time, json, sys

###-------Variable section------ ####

BASE_ACCT_ACCESS_KEY=""  ## enter base account  aws access key ##
BASE_ACCT_SECRET_KEY=""  ## enter base account aws secret key ##
BASE_ACCT_ID="" ## base account id that has trust to the new account
AGGR_ACCT_ID=""    ## AWS org account id under which new account gets created ##
AGGR_ACCT_ROLE_ARN="arn:aws:iam::<AGGR_ACCT_ID>:role/Admins"   ## aggregate account role arn ##
AGGR_ACCT_SESSION_NAME="aggr-acct-session"  ## aggregate account session name ##
NEW_ACCOUNT_EMAIL=""     ## enter email contact for new aws account ex: 'abc+alias@xyz.com' " ##
NEW_ACCOUNT_NAME=""      ## enter new aws account name ##
NEW_ACCOUNT_ALIASNAME=""  ## enter new aws account alias name ex: 'autotesting' ###
defaultRoleName="OrganizationAccountAccessRole"    ## default org role name..dont change this ##
NEW_ACCOUNT_GROUP_NAME=""   ## enter group name that allow users to switch to new account ##
NEW_ACCOUNT_USER_LIST=[""]  ## enter list of comma separated usernames that gets added to the above group ##
NEW_ACCOUNT_SESSION_NAME="new-acct-session"  ## new account session name ##
NEW_GROUP_POLICY_NAME=""  ## enter new group policy name ex: '<new accountname>-assume-role-admins-allow' ###

####-------End of variable section------------ ###

###-------IAM policy section----------------- ###
admins_policy={                             ## admin policy gets created on new account that establish trust with base account
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ""
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}

group_policy={                   ## group policy template that allow switching role to new account from base account
  "Version": "2012-10-17",
  "Statement": {
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Resource": ""
  }
}

####----------End of policies section-----------####

## Create base login session
base_session=boto3.Session(aws_access_key_id=BASE_ACCT_ACCESS_KEY, aws_secret_access_key=BASE_ACCT_SECRET_KEY)

## Function to switch IAM role and return access credentials

def switch_iam_role(aws_session, **args):
  role_client=aws_session.client('sts')
  response=role_client.assume_role(**args)
  return(response.get('Credentials').get('AccessKeyId'), response.get('Credentials').get('SecretAccessKey'), response.get('Credentials').get('SessionToken'))

## get credentials after switching to aggregate account and creates new aws account ##
aggre_creds=switch_iam_role(base_session, RoleArn=AGGR_ACCT_ROLE_ARN, RoleSessionName=AGGR_ACCT_SESSION_NAME)

if len(aggre_creds) == 3:     ## True , if role switched successfully
    aggr_session=boto3.Session(aws_access_key_id=aggre_creds[0], aws_secret_access_key=aggre_creds[1], aws_session_token=aggre_creds[2])
    new_acct_client=aggr_session.client('organizations')
    new_acct_response=new_acct_client.create_account(Email=NEW_ACCOUNT_EMAIL, AccountName=NEW_ACCOUNT_NAME)

new_account_status = "IN_PROGRESS"
while new_account_status == 'IN_PROGRESS':
    new_acct_status_response = new_acct_client.describe_create_account_status(CreateAccountRequestId=new_acct_response.get('CreateAccountStatus').get('Id'))
    print("New account creation status is " + str(new_acct_status_response) + "pls wait...")
    time.sleep(2)
    new_account_status = new_acct_status_response.get('CreateAccountStatus').get('State')

if new_account_status == 'SUCCEEDED':
    new_account_id_str = int(new_acct_status_response.get('CreateAccountStatus').get('AccountId'))
    new_account_id = int(new_account_id_str)
    print("\n\n\nNew AWS account id is %s\n\n\n" % new_account_id)
elif new_account_status == 'FAILED':
    print("Account creation failed: " + new_acct_status_response.get('CreateAccountStatus').get('FailureReason'))
    sys.exit(1)


print("Sleeping for 30 secs to finish account creation process...")
time.sleep(30)

## At this stage new account has been created under aws org account org ##
new_account_roleARN="arn:aws:iam::{}:role/{}".format(new_account_id, defaultRoleName)

## Assume the IAM role  of newly created account
new_account_creds=switch_iam_role(aggr_session, RoleArn=new_account_roleARN, RoleSessionName=NEW_ACCOUNT_SESSION_NAME)

## update group policy on base account to include new account id ##
group_policy_resource_arn="arn:aws:iam::{}:role/Admins".format(new_account_id)
group_policy['Statement']['Resource']=group_policy_resource_arn

## update admin policy to include base account id #
admins_policy_resource_urn="arn:aws:iam::{}:root".format(BASE_ACCT_ID)
admins_policy['Statement']['Principal']['AWS']=admins_policy_resource_urn

## create admin role on new account
if len(new_account_creds) == 3:     ## True , if role switched successfully
    new_acct_session=boto3.Session(aws_access_key_id=new_account_creds[0], aws_secret_access_key=new_account_creds[1], aws_session_token=new_account_creds[2])
    new_acct_iam_client=new_acct_session.client('iam')
    response_1 = new_acct_iam_client.create_role(RoleName='Admins',AssumeRolePolicyDocument=json.dumps(admins_policy))
    response_2 = new_acct_iam_client.attach_role_policy(RoleName='Admins', PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')

## set account alias for the new account

new_acct_iam_client.create_account_alias(AccountAlias=NEW_ACCOUNT_ALIASNAME)

## create group , attach policy and add users to the group under base account ##
base_acct_iam_client=base_session.client('iam')
response_3=base_acct_iam_client.create_group(GroupName=NEW_ACCOUNT_GROUP_NAME)
response_4=base_acct_iam_client.put_group_policy(GroupName=NEW_ACCOUNT_GROUP_NAME,PolicyDocument=json.dumps(group_policy), PolicyName=NEW_GROUP_POLICY_NAME)
for user in NEW_ACCOUNT_USER_LIST:
    response_5=base_acct_iam_client.add_user_to_group(GroupName=NEW_ACCOUNT_GROUP_NAME, UserName='%s' % user)


## Delete the default org role and policy on the new account

new_acct_iam_client.detach_role_policy(PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess', RoleName=defaultRoleName)
new_acct_iam_client.delete_role(RoleName=defaultRoleName)




