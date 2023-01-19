- [Overview](#overview)
  - [install](#install)
  - [remove](#remove)
  - [module](#module)
  - [su](#su)
  - [magiskhide](#magiskhide)
  - [zygisk](#zygisk)
- [Modules](#modules)
- [Magisk Hide](#magisk-hide)
- [Su](#su-1)
- [Zygisk](#zygisk-1)


# Overview

## install

* Install Magisk Delta in Waydroid
```
usage: waydroid_magisk install [-h] [-u] [-c] [-d] [-t [TMPDIR]]

options:
  -h, --help            show this help message and exit
  -u, --update          Update Magisk Delta
  -c, --canary          Install Magisk Delta canary channel (default canary)
  -d, --debug           Install Magisk Delta debug channel (default canary)
  -t [TMPDIR], --tmpdir [TMPDIR]
                        Custom path to use as an temporary directory
```

## remove
* Remove Magisk Delta from Waydroid
```
usage: waydroid_magisk remove [-h]

options:
  -h, --help  show this help message and exit
```

##  module
* Manage modules in Magisk Delta
```
usage: waydroid_magisk module [-h] {install,remove,list} ...

positional arguments:
  {install,remove,list}
    install             Install magisk module
    remove              Remove magisk module
    list                List all installed magisk modules

options:
  -h, --help            show this help message and exit
```

## su
* Manage su in Magisk Delta
```
usage: waydroid_magisk su [-h] {shell,list,allow,deny} ...

positional arguments:
  {shell,list,allow,deny}
    shell               Opens the magisk su shell
    list                Return apps status in su database
    allow               Allow su access to app
    deny                Deny su access to app

options:
  -h, --help            show this help message and exit
```

## magiskhide
* Execute magisk hide commands
```
usage: waydroid_magisk magiskhide [-h] {status,sulist,enable,disable,add,rm,ls} ...

positional arguments:
  {status,sulist,enable,disable,add,rm,ls}
    status              Return the MagiskHide status
    sulist              Return the SuList status
    enable              Enable MagiskHide
    disable             Disable MagiskHide
    add                 Add a new target to the hidelist (sulist)
    rm                  Remove target(s) from the hidelist (sulist)
    ls                  Print the current hidelist (sulist)

options:
  -h, --help            show this help message and exit
```

## zygisk
* Execute zygisk commands
```
usage: waydroid_magisk zygisk [-h] {status,enable,disable} ...

positional arguments:
  {status,enable,disable}
    status              Return the zygisk status
    enable              Enable zygisk (requires waydroid restart)
    disable             Disable zygisk (requires waydroid restart)

options:
  -h, --help            show this help message and exit
```


# Modules
* `waydroid_magisk module list` - lists all the installed magisk modules
* `waydroid_magisk module install {/path/to/module}` - installs a magisk module
* `waydroid_magisj module remove {module_name}` - removes a magisk module

# Magisk Hide
* `waydroid_magisk magiskhide status` - returns magisk hide status
* `waydroid_magisk magiskhide enable` - enables magisk hide
* `waydroid_magisk magiskhide disable` - disables magisk hide
* `waydroid_magisk magiskhide add {package_name or proc_name}` - adds a new package or process to the hidelist (sulist)
* `waydroid_magisk magiskhide rm {package_names or proc_names}` - remvoes a new package or process from the hidelist (sulist)
* `waydroid_magisk magiskhide ls` - prints the magisk hide list

# Su
* `waydroid_magisk su shell` - opens su magisk inside waydroid
* `waydroid_magisk su list` - lists apps in the su list and whatever if they have su access or not
* `waydroid_magisk su allow {package_name}` - allows su access to a package (app)
* `waydroid_magisk su deny {package_name}` - denies su access to a package (app)

# Zygisk
* `waydroid_magisk zygisk status` - returns magisk zygisk status
* `waydroid_magisk zygisk enable` - enables magisk zygisk
* `waydroid_magisk zygisk disable` - disables magisk zygisk