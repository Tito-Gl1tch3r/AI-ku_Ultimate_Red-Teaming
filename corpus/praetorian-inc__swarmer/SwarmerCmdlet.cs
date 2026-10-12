using System;
using System.IO;
using System.Linq;
using System.Management.Automation;

namespace Swarmer
{
    [Cmdlet(VerbsData.Convert, "RegToHive")]
    [OutputType(typeof(bool))]
    public class SwarmerCmdlet : PSCmdlet
    {
        [Parameter(
            Mandatory = true,
            Position = 0,
            ValueFromPipeline = true,
            ValueFromPipelineByPropertyName = true)]
        [ValidateNotNullOrEmpty]
        public string InputPath { get; set; }

        [Parameter(
            Mandatory = true,
            Position = 1,
            ValueFromPipelineByPropertyName = true)]
        [ValidateNotNullOrEmpty]
        public string OutputPath { get; set; }

        protected override void ProcessRecord()
        {
            try
            {
                // Resolve file paths
                string inputPath = GetResolvedPath(InputPath);
                string outputPath = GetResolvedPath(OutputPath, false);

                // Check if the input file exists
                if (!File.Exists(inputPath))
                {
                    ThrowTerminatingError(new ErrorRecord(
                        new FileNotFoundException($"File not found: {inputPath}"),
                        "FileNotFound",
                        ErrorCategory.ObjectNotFound,
                        inputPath));
                    return;
                }

                // Parse the .reg file
                RegistryParser parser = new RegistryParser();
                RegistryKeyInfo rootKey = parser.ParseRegFile(inputPath);

                // Create and populate the hive
                HiveWriter writer = new HiveWriter();
                bool success = writer.CreateAndPopulateHive(rootKey, outputPath);

                if (success)
                {
                    WriteObject(true);
                }
                else
                {
                    WriteObject(false);
                    ThrowTerminatingError(new ErrorRecord(
                        new Exception("Failed to create hive file"),
                        "HiveCreationFailed",
                        ErrorCategory.OperationStopped,
                        inputPath));
                }
            }
            catch (Exception ex)
            {
                ThrowTerminatingError(new ErrorRecord(
                    ex,
                    "ConvertRegToHiveError",
                    ErrorCategory.OperationStopped,
                    null));
            }
        }


        private string GetResolvedPath(string path, bool mustExist = true)
        {
            string resolvedPath = SessionState.Path.GetUnresolvedProviderPathFromPSPath(path);
            
            if (mustExist && !File.Exists(resolvedPath) && !Directory.Exists(resolvedPath))
            {
                ThrowTerminatingError(new ErrorRecord(
                    new ItemNotFoundException($"Cannot find path '{path}' because it does not exist."),
                    "ConvertRegToHiveError",
                    ErrorCategory.ObjectNotFound,
                    path));
            }
            
            return resolvedPath;
        }
    }
}