<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
<h2 align="center">Power BI: Row & Object Level Security Automation</h2>

  <p align="center">
    Automating security role and security rules generation in Power BI datasets using PowerShell and Python.
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li>
      <a href="#prerequisites">Prerequisites</a>
      <ul>
        <li><a href="#power-bi-premium">Power BI Premium</a></li>
        <li><a href="#database">Database</a></li>
        <li><a href="#python">Python</a></li>
        <li><a href="#powershell">PowerShell</a></li>
      </ul>
    </li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

Project aims to automate a manual process of creating and deploying [Row level security](https://learn.microsoft.com/en-us/power-bi/enterprise/service-admin-rls) (RLS) and [Object level security](https://learn.microsoft.com/en-us/power-bi/enterprise/service-admin-ols?tabs=table) (OLS).

RLS is a common security implementation in Power BI solutions, RLS lets you restrict some data for certain individuals or groups. OLS lets you restrict, as the name suggests, an object, which could be a table, column or measure.  
RLS can be added using a simple and intuitive Power BI Desktop’s UI, OLS, on the other hand, can only be added editing tabular model directly, e.g. with Tabular Editor, which requires additional knowledge of the tool. As of this blog writing, OLS cannot be added using only Power BI Desktop.  
This is a manual process and depending on the number of roles and restrictions, could be a cumbersome process.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- PREREQUISITES -->
## Prerequisites

To make the automation work, you'll need several things in place:
* Power BI Premium
* Database
* Python
* Powershell

### Power BI Premium 

Roles can only be deployed directly to Power BI dataset in service if the workspace is in Premium capacity.  
Capacity [XMLA-Read/Write](https://learn.microsoft.com/en-us/power-bi/enterprise/service-premium-connect-tools#to-enable-read-write-for-a-premium-capacity) permissions have to be enabled:  
![Enabling permissions on XMLA endpoint](/Images/xmla-endpoint-enable.png?raw=true "Enabling permissions on XMLA endpoint")

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Database  
Central location where security matrix is placed and maintained. In our example, security matrix was made as part of the “AdventureWorksDW2019” local SQL database:
![Security matrix as part of AdventureWorksDW2019 database](/Images/security-matrix-in-db.png?raw=true "Security matrix")

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Python  

Python (or any other of your preferred scripting language) is used to actually generate the TMSL script for roles. The main idea is to read the security matrix shown above, process it and output [TMSL role script](https://learn.microsoft.com/en-us/analysis-services/tmsl/roles-object-tmsl?view=asallproducts-allversions) which can be used to deploy the roles directly to Power BI dataset through XMLA endpoint.  
An example below shows the security matrix (on the left) with 1 role highlighted (having 3 rows, 1 for RLS and 2 for OLS). Out of those 3 highlighted rows, a TMSL script (on the right) has been generated to create a role with such rules in our Power BI dataset.  
![From security matrix to TMSL script using Python](/Images/Python%20To%20TMSL.png?raw=true "From security matrix to TMSL script using Python")  
In this example, for each role we generate a separate JSON TMSL script.  

Before executing [rls-ols-automation.py](rls-ols-automation.py) python script, you need to set up environment variables. This can be done by creating an txt file named ".env" with:
```
# database parameters
SERVER_NAME='' # example value 'PC100'
DATABASE_NAME='' # example value 'AdventureWorksDW2019'
DATABASE_USERNAME=''
DATABASE_PASSWORD=''   
DRIVER='{}' #example value '{ODBC Driver 17 for SQL Server}'

# security roles table name
TABLE_SECURITY_ROLES_NAME='' # example value 'SecurityRoles'

# Power BI dataset name
POWERBI_DATASET_NAME='' # example value 'rls-ols-automation'
```

In python script, we make use of `dotenv` python library to read those environment variables:
```python
env_file = find_dotenv(".env")
load_dotenv(env_file)

# import credentials from .env file
SERVER_NAME = os.environ.get('SERVER_NAME')
DATABASE_NAME = os.environ.get('DATABASE_NAME')
# DATABASE_USERNAME = os.environ.get('DATABASE_USERNAME') # if needed
# ATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD') # if needed
DRIVER = os.environ.get('DRIVER')

# security roles table name
TABLE_SECURITY_ROLES_NAME = os.environ.get('TABLE_SECURITY_ROLES_NAME')

# power bi dataset name (string)
POWERBI_DATASET_NAME = os.environ.get('POWERBI_DATASET_NAME')
```
Because our security matrix is a part of SQL database, we use `pyodbc` library to read the data:
```python
# get data
with pyodbc.connect('DRIVER='+DRIVER+';SERVER='+SERVER_NAME+';DATABASE='+DATABASE_NAME+';Trusted_Connection=yes') as conn:
    securityRoles = pd.read_sql('SELECT * FROM '+TABLE_SECURITY_ROLES_NAME, conn)

```
If your data source is different, this part needs to be adjusted.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### PowerShell 

PowerShell is used to deploy the TMSL scripts to Power BI dataset using XMLA endpoint.  
Once we have our TMSL role files generated by Python, we can use a PowerShell script to read our saved roles .json files into an array:
```shell
# read TMSL scripts from "./Roles" directory into an array
$jsonFiles = Get-ChildItem "Roles" -filter *.json
$tmslScripts = foreach ($jsonFile in $jsonFiles)
{
  $role = get-content $jsonFile.FullName
  @{Name=$role}  
}
```
Then we simply loop through each role and deploy it to our dataset using [Invoke-ASCmd](https://learn.microsoft.com/en-us/powershell/module/sqlserver/invoke-ascmd?view=sqlserver-ps) function:  
```shell
# Execution all TMSL scripts
$tmslScripts | ForEach-Object {
    # Get single role TMSL script
    [String]$roleObject = $_.Name
    # Execute operation
    Try {
        Invoke-ASCmd -Query $roleObject -Server: $XmlaEndpoint
    }
    Catch{
        # Write message if error
        Write-Host "An error occured" -ForegroundColor Red
    }
  }
```
Note, that `$XmlaEndpoint` is the link to your workspace in a format:  
```
powerbi://api.powerbi.com/v1.0/myorg/Your Workspace Name
```
This solution can be found in [rls-ols-automation-deploy-roles.ps1](rls-ols-automation-deploy-roles.ps1) PowerShell script.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
