function Component()
{
    //default constructor
}

Component.prototype.createOperations = function()
{
    // call default implementation
    component.createOperations();
    // ... add custom operations
    if (installer.value("os") === "win") {
          component.addOperation("CreateShortcut", "@TargetDir@/misli.exe", "@StartMenuDir@/Misli.lnk");
    } 
}

