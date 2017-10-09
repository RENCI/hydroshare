# xDCIShare _(xDCIShare)_

### Nightly Build Status (develop branch)

| Workflow | Clean | Build/Deploy | Unit Tests | Flake8
| :----- | :--- | :--- | :-------- | :------------ | :----------- |
| [![Build Status](http://ci.xdcishare.renci.org:8080/job/nightly-build-workflow/badge/icon?style=plastic)](http://ci.xdcishare.renci.org:8080/job/nightly-build-workflow/) | [![Build Status](http://ci.xdcishare.renci.org:8080/job/nightly-build-clean/badge/icon?style=plastic)](http://ci.xdcishare.renci.org:8080/job/nightly-build-clean/) | [![Build Status](http://ci.xdcishare.renci.org:8080/job/nightly-build-deploy/badge/icon?style=plastic)](http://ci.xdcishare.renci.org:8080/job/nightly-build-deploy/) | [![Build Status](http://ci.xdcishare.renci.org:8080/job/nightly-build-test/badge/icon?style=plastic)](http://ci.xdcishare.renci.org:8080/job/nightly-build-test/) | [![Build Status](http://ci.xdcishare.renci.org:8080/job/nightly-build-flake8/badge/icon?style=plastic)](http://ci.xdcishare.renci.org:8080/job/nightly-build-flake8/) |

Build generate by [Jenkins CI](http://ci.xdcishare.renci.org:8080)

### requires.io
[![Requirements Status](https://requires.io/github/RENCI/xDCIShare/hs_docker_base/requirements.svg?branch=develop)](https://requires.io/github/RENCI/xDCIShare/hs_docker_base/requirements/?branch=master)

xDCIShare
============

xDCIShare is a collaborative website being developed for better access to data and models of scientific domains. xDCIShare is derived directly from the NSF-funded 3-clause BSD [HydroShare open source codebase](https://github.com/hydroshare/hydroshare), NSF awards [1148453](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1148453) and [1148090](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1148090). xDCIShare provides the sustainable technology infrastructure needed to address critical issues related to scientific research. xDCIShare expands data sharing capability by broadening the classes of data accommodated, expanding capability to include the sharing of models and model components, and taking advantage of emerging social media functionality to enhance information about and collaboration around scientific data and models.

If you want to contribute to xDCIShare, please see the [xDCIShare Wiki](https://github.com/RENCI/xDCIShare/wiki/).

More information can be found in the [xDCIShare Wiki](https://github.com/RENCI/xDCIShare/wiki/).

## Install

This README file is for developers interested in working on the Hydroshare code itself, or for developers or researchers learning about how the application works at a deeper level. If you simply want to _use_ the application, go to http://hydroshare.org and register an account.

If you want to install and run the source code of application locally and/or contribute to development, read on.

### [VirtualBox](https://www.virtualbox.org/wiki/Downloads) development environment

To quickly get started developing we offer a preconfigured development environment encapsulated within a virtual box Virtual Machine (VM). This includes the appropriate version of Ubuntu, Python, Docker, and other key dependencies and development tools.

### Simplified Installation Instructions
1. Download the [latest OVA file here](http://distribution.hydroshare.org/public_html/)
2. Open the .OVA file with VirtualBox, this will create a guest VM
3. Follow the instructions here to share a local hydroshare folder with your guest VM
4. Start the guest VM
5. Log into the guest VM with either ssh or the GUI. The default username/password is hydro:hydro
6. From the root directory `/home/hydro`, clone this repository into the hydroshare folder
7. `cd` into the hydroshare folder and run `./hsctl rebuild --db` to build the application and run it
8. If all goes well, your local version of Hydroshare should be running at http://192.168.56.101:8000

For more detailed installation, please see this document: [Getting Started with HydroShare](https://github.com/hydroshare/hydroshare/wiki/getting_started)

## Usage

For all intents and purposes, Hydroshare is a large Python/Django application with some extra features and technologies added on:
- SOLR for searching
- Redis for caching
- RabbitMQ for concurrency and serialization
- iRODS for a federated file system
- PostgreSQL for the database backend

#### The `hsctl` Script

The `hsctl` script is your primary tool in interacting with and running tasks against your Hydroshare install. It has the syntax `./hsccl [command]` where `[command]` is one of:

- `loaddb`: Deletes existing database and reloads the database specified in the `hydroshare-config.yaml` file.
- `managepy [args]`: Executes a `python manage.py [args]` call on the running hydroshare container.
- `maint_off`: Removes the maintenance page from view (only if NGINX is being used).
- `maint_on`: Displays the maintenance page in the browser (only if NGINX is being used).
- `rebuild`: Stops, removes and deletes only the hydroshare docker containers and images while retaining the database contents on the subsequent build as defined in the `hydroshare-config.yaml` file
- `rebuild --db`: Fully stops, removes and deletes any prior hydroshare docker containers, images and database contents prior to installing a clean copy of the hydroshare codebase as defined in the `hydroshare-config.yaml` file.
- `rebuild_index`: Rebuilds the solr/haystack index in a non-interactive way.
- `restart`: Restarts the django server only (and nginx if applicable).
- `start`: Starts all containers as defined in the `docker-compose.yml` file (and nginx if applicable).
- `stop`: Stops all containers as defined in the `docker-compose.yml` file.
- `update_index`: Updates the solr/haystack index in a non-interactive way.

## Testing and Debugging

### Testing

Tests are run via normal Django tools and conventions. However, you should use the `hsctl` script mentioned abouve with the `managepy` command. For example: `./hsctl managepy test hs_core.tests.api.rest.test_resmap --keepdb`.

There are currently over 600 tests in the system, so it is highly recommended that you run the test suites separately from one another.

### Debugging

You can debug via PyCharm by following the instructions [here](https://github.com/hydroshare/hydroshare/wiki/pycharm-configuration).

## Other Configuration Options

### Local iRODS

Local iRODS is _not_ required for development unless you are specifically working on the iRODS integration. However,if you want to work with iRODS or you simply want to learn about it, you can enable it locally.

### Local HTTPS

To enable HTTPS locally:
1. edit `config/hydroshare-config.template` and change the two values under `### Deployment Options ###` to `true` like so:
```
### Deployment Options ###
USE_NGINX: true
USE_SSL: true
```
2. Run `./hsctl rebuild`

## Contribute

There are many ways to contribute to Hydroshare.

1. Submit Pull Requests with code changes for review
2. Open Issues for any bugs you find or suggestions you may have

## License

Hydroshare is released under the BSD 3-Clause License. This means that [you can do what you want, so long as you don't mess with the trademark, and as long as you keep the license with the source code](https://tldrlegal.com/license/bsd-3-clause-license-(revised)).

©2017 CUAHSI. This material is based upon work supported by the National Science Foundation (NSF) under awards 1148453 and 1148090. Any opinions, findings, conclusions, or recommendations expressed in this material are those of the authors and do not necessarily reflect the views of the NSF.
