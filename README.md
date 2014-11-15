fsch auto compile
=================

This is a python program to automate compilation for Flex projects using fcsh (Flex Compiler SHell). This program provides the following:

  - Faster compilation using fcsh
  - Automatic compilation when sources files are changed
  - Concurrent builds

This is accomplished by running fcsh as background process(es), monitoring source paths for changes and invoking the compilation whenever
changes are detected. Compilation of projects are configurable through a YAML and properties file.


Credits to the developer of flexcompile: https://code.google.com/p/flexcompile for a script to invoke fcsh as a daemon process. The original script was forked and modified to support Windows platforms, configuration, ability to kill the daemon process, as well as specifying
additional fcsh instances running on different ports.  

Requirements
------------
- Python 2.7.8
- Flex SDK
- Add `<FLEX_HOME>/bin` to your PATH environment variable.

Usage
-----
Before running, configure your projects using the config.yaml and config.properties as a template.

To run:
```
python app.py
```

To run with the with a specified config and property file:
```
python app.py --config <yaml_config_path> --properties <property_file_path>
```

Troubleshooting
---------------
On Windows, there appears to be a shortcoming with fcsh, where paths including a space cause the compilation command to be misinterpreted. If this occurs, you can create symbolic links to create an alternate path location without spaces.

For example:
```
mklink /J "C:\flex\4.6.0" "C:\Program Files\Adobe\Adobe Flash Builder 4.6\sdks\4.6.0"
```

Resources
---------
- fcsh - http://help.adobe.com/en_US/flex/using/WS2db454920e96a9e51e63e3d11c0bf67670-7fcd.html
- flexcompile - https://code.google.com/p/flexcompile
