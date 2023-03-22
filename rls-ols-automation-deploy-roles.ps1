# Fill in parameters
$WorkspaceName = "R&D"  

# Base variables
$PbiBaseConnection = "powerbi://api.powerbi.com/v1.0/myorg/"
$XmlaEndpoint = $PbiBaseConnection + $WorkspaceName

# Check whether the SQL Server module is installed. If not, it will be installed.
# Install Module (Admin permissions might be required) 
$moduleName = Get-Module -ListAvailable -Verbose:$false | Where-Object { $_.Name -eq "SqlServer" } | Select-Object -ExpandProperty Name;
if ([string]::IsNullOrEmpty($moduleName)) {
    Write-Host -ForegroundColor White "==============================================================================";
    Write-Host -ForegroundColor White  "Install module SqlServer...";
    Install-Module SqlServer -RequiredVersion 22.0.20-preview -AllowPrerelease -Scope CurrentUser -SkipPublisherCheck -AllowClobber -Force
    # Check for the latest version this documentation: https://www.powershellgallery.com/packages/SqlServer/
    # If you're using PowerShell 7, make sure to install the preview version as other versions do not support Invoke-ASCmd function for PowerShell 7
    # https://learn.microsoft.com/en-us/powershell/module/sqlserver/invoke-ascmd?view=sqlserver-ps#description
    Write-Host -ForegroundColor White "==============================================================================";
}

# read TMSL scripts from "./Roles" directory into an array
$jsonFiles = Get-ChildItem "Roles" -filter *.json
$tmslScripts = foreach ($jsonFile in $jsonFiles)
{
  $role = get-content $jsonFile.FullName
  @{Name=$role}  
}

# Execution all TMSL scripts
$tmslScripts | ForEach-Object {
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