#FROM python:3.11
#
## RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
##
## RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
#
#RUN apt-get -y update
#
#RUN apt-get install -y libnss3 libgconf-2-4
#
##RUN sudo apt-get install ./google-chrome-stable_114.0.5735.198-1_amd64.deb
#
#RUN apt-get install -yqq unzip
#
##RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE_114`/chromedriver_linux64.zip
#
#RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
#
#RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/dr
#RUN chmod +x /usr/local/bin/dr/chromedriver
#ENV DISPLAY=:99
#
#COPY . /2gis_docker
#
#WORKDIR /2gis_docker
#
#RUN pip install --upgrade pip
#
#RUN pip install -r requirements.txt

FROM joyzoursky/python-chromedriver:3.8

COPY . /2gis_docker

WORKDIR /2gis_docker

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

