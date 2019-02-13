import boto3, datetime, re, sys

## script to get running ec2/rds instances within all regions from a specific AWS account

aws_account_name = sys.argv[1]
aws_service_name = sys.argv[2]

aws_profile_name = aws_account_name
session = boto3.Session(profile_name=aws_account_name)

def get_instname_tags(tag_list, getinstname):
    for i in tag_list:
        if i.get('Key') == getinstname:
            return i.get('Value')


client = boto3.client('ec2', region_name="us-west-2")
get_regions = client.describe_regions()
get_region_names = [region_name.get('RegionName') for region_name in get_regions.get('Regions')]


def getEC2details(regions):
    for region in regions:
        ec2_resource = session.resource(aws_service_name, region_name=region)
        running_instances = ec2_resource.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        for instance in running_instances:
            launchtime = instance.launch_time
            regex_launchtime = re.findall(r'[\d\-\s\:]+', str(launchtime))
            get_launchtime = datetime.datetime.strptime(regex_launchtime[0], '%Y-%m-%d %H:%M:%S')
            if instance.tags:
                instancename = get_instname_tags(instance.tags, 'Name')
                if instancename:
                    print(instance.id + ':' + instance.instance_type + ':' + region + ':' + instancename + ':' + str(get_launchtime))
                else:
                    print(instance.id + ':' + instance.instance_type + ':' + region + ':' + str(get_launchtime))

def getRDSdetails(regions):
    for region in regions:
        rds = session.client(aws_service_name, region_name=region)
        rds_identifier = rds.describe_db_instances()
        if rds_identifier.get('DBInstances'):
            dbcluster = rds_identifier.get('DBInstances')
            for dbs in dbcluster:
                dbident = dbs.get('DBInstanceIdentifier')
                db_name = dbs.get('DBName')
                db_class = dbs.get('DBInstanceClass')
                print(dbident, db_class, db_name, region)


if aws_service_name == "ec2":
    getEC2details(get_region_names)
elif aws_service_name == "rds":
    getRDSdetails(get_region_names)
