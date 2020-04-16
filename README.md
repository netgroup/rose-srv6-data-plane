# Loss Monitoring gRPC

## Prerequisites

gRPC Python is supported for use with Python 2.7 or Python 3.4 or higher.
For the project pourpose we will use Python >= 3.4

- Python >= 3.4
- pip (python-pip) [https://pip.pypa.io/en/stable/quickstart/]

### Install virtualenv

    $ pip install virtualenv

for more details regarding `virtualenv` ['https://virtualenv.pypa.io/en/latest/']

### Create Virtual enviroment

    $ virtualenv venv

### Activate Virtual enviroment already created

    $ source venv/bin/activate

this command must be executed every time, just before start to work with the project

### Install requirements (gRPC and gRPC tools)

As soon the virtualenv is active you can install all the dependencies with the command below

    $ pip install -r requirements.txt

## Generate gRPC code

From the base directory of the project

    $ python -m grpc_tools.protoc -I proto/ --python_out=srv6pm_grpc --grpc_python_out=srv6pm_grpc proto/*
