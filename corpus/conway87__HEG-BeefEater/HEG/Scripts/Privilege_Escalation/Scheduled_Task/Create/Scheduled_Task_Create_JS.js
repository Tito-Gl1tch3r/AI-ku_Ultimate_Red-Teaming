function findMainDir(startPath) {
    var fso = new ActiveXObject("Scripting.FileSystemObject");
    var currentPath = startPath;
    while (true) {
        var mainDir = fso.BuildPath(currentPath, "HEG");
        if (fso.FolderExists(mainDir)) {
            return mainDir;
        }
        var parentPath = fso.GetParentFolderName(currentPath);
        if (parentPath == currentPath) {
            return null;
        }
        currentPath = parentPath;
    }
}

var shell = new ActiveXObject("WScript.Shell");
var fso = new ActiveXObject("Scripting.FileSystemObject");
var scriptPath = shell.CurrentDirectory;
var mainDir = findMainDir(scriptPath);

if (mainDir) {
    var exePath = fso.BuildPath(mainDir, "Tools\\Legacy_Tooling.exe");

    if (fso.FileExists(exePath)) {
        var service = new ActiveXObject("Schedule.Service");
        service.Connect();
        var rootFolder = service.GetFolder("\\"); // Root folder
        var taskDef = service.NewTask(0);
        var taskSettings = taskDef.Settings;
        taskSettings.Enabled = true;
        taskSettings.StartWhenAvailable = true;
        var execAction = taskDef.Actions.Create(0); // 0 = Execute
        execAction.Path = exePath;
        rootFolder.RegisterTaskDefinition("HEG_Scheduled-Task-JS", taskDef, 6, null, null, 3, null);
    } else {
        WScript.Echo("Executable not found: " + exePath);
    }
} else {
    WScript.Echo("Main directory not found.");
}
