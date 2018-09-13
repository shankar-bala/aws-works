
Python script to create AWS account under specific organization


# Pre-requistics
  - python 3.x and boto3 module

### Purpose
   Script to create AWS accounts under organization. 
   This script works under the below scenario
   - You have AWS console access belonging to a specific aws account(called "base" account)
   - From the base account, you have roles that can switch to a different "billing" aws account belonging to an organization under which you create new account
   - Script creates new aws account after switching roles to billing account from base account and also establish IAM roles with specific policies and add base account as a trusted account
   - After the script successfully ran, you may be able to switch roles to new account from your base account

### Usage

After the python modules are installed.,
   - Update the variable section with appropriate AWS keys (having account creation IAM permissions) and account names
   - run the script as "python aws_subaccounts_setup_template.py"

### Output

If all the tasks are complete, you wont see any error and the new account gets provisioned. You may consider logging into the new account and setup MFA manually on the new account as recommended by AWS. 

If any errors running the script, we have to deal them accordingly and probably need resource cleanup before retrying again

### Thoughts

This script may not fullfil everyone needs..but some may came across this situation...if yes, give a try and leave a feedback for any improvements..give it a shot !!!