FROM ubuntu:20.04

RUN apt-get update -y
RUN apt-get install python3.8 -y
RUN apt-get install python3-pip -y
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /sandbox

RUN pip3 install requests python-magic numpy

CMD echo 127.0.0.1 example1.ge >> /etc/hosts \
& echo 127.0.0.1 example2.ge >> /etc/hosts \
& echo 127.0.0.1 example3.ge >> /etc/hosts \
& /bin/bash
