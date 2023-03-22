import json
import os

import pandas as pd
import pyodbc
from dotenv import find_dotenv, load_dotenv


def createTablePermissions(tableName, roleRestrictions):
    """Given table name and security matrix for a particular role, will generate a dictionary
    containing all the necessary restrictions for the particular table.

    Args:
        tableName (str): name of the restricted table
        roleRestrictions (dataframe): security matrix for passed role
    """
    columnPermissions = []

    # filtered combined df for and single table
    tableRestrictions = roleRestrictions[roleRestrictions['RestrictedTable'] == tableName]

    columnNames = set(tableRestrictions['RestrictedColumn'])

    if columnNames != set([None]):
        # if there's a column for which this role should be restricted

        tablePermission = {
            'name': tableName,
            'metadataPermission': 'read'
        }

        # filtered combined df for a single role and single table for only columns/tables where there's restrictions
        securityCombined_restricted = tableRestrictions.dropna(subset=['RestrictedColumn'])

        # OLS
        olsColumns = securityCombined_restricted[securityCombined_restricted['RestrictedData'].isnull()]

        columnPermissions = []

        for columnName in olsColumns['RestrictedColumn']:

            columnPermission = {
                'name': columnName,
                'metadataPermission': 'none'
            }

            columnPermissions.append(columnPermission)

        # RLS
        rlsColumns = securityCombined_restricted[securityCombined_restricted['RestrictedData'].notnull()]

        filterExpression = None
        for idx, columnName in enumerate(rlsColumns['RestrictedColumn']):
            singleRow = rlsColumns[rlsColumns['RestrictedColumn'] == columnName]

            # RLS
            filterColumnExpression = '['+columnName+']'+' == \"'+singleRow['RestrictedData'].item()+'\"'
            if idx == 0:
                filterExpression = filterColumnExpression
            else:
                filterExpression = filterExpression+' && '+filterColumnExpression

        if bool(columnPermissions):
            tablePermission['columnPermissions'] = columnPermissions
        if filterExpression is not None:
            tablePermission['filterExpression'] = filterExpression

    else:
        # otherwise role sees the whole table
        tablePermission = {
            'name': tableName,
            'metadataPermission': 'none'
        }

    return tablePermission


def main():

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

    # get data
    with pyodbc.connect('DRIVER='+DRIVER+';SERVER='+SERVER_NAME+';DATABASE='+DATABASE_NAME+';Trusted_Connection=yes') as conn:
        securityRoles = pd.read_sql('SELECT * FROM '+TABLE_SECURITY_ROLES_NAME, conn)

    # create directory for role json files
    if not os.path.exists('Roles'):
        os.makedirs('Roles')

    # unique role names
    roleNames = set(securityRoles['SecurityRole'])

    for roleName in roleNames:

        # filtered combined df for a single role
        securityCombined_oneRole = securityRoles[securityRoles['SecurityRole'] == roleName]

        tablePermissions = []

        # unique table names for this role
        tableNames = set(securityCombined_oneRole['RestrictedTable'])

        # for each unique table name, create permissions
        for tableName in tableNames:

            if tableName is None:
                continue

            # create permisions per table
            tablePermission = createTablePermissions(tableName, securityCombined_oneRole)

            # append permissions to a list
            tablePermissions.append(tablePermission)

        rolePermission = {
            'name': roleName,
            'modelPermission': 'read'
        }

        if bool(tablePermissions):
            rolePermission['tablePermissions'] = tablePermissions

        rolePermission['annotations'] = [{
                'name': 'created_by',
                'value': 'python_script'
            }]

        deploymentScript = {
            'createOrReplace': {
                'object': {
                    'database': POWERBI_DATASET_NAME,
                    'role': roleName
                },
                'role': rolePermission
            }
        }

        with open('Roles/Role_'+roleName+'.json', 'w') as outfile:
            json.dump(deploymentScript, outfile, indent=4)


if __name__ == "__main__":
    main()
