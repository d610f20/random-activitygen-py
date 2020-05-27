FROM python:3

WORKDIR /usr/src
RUN git clone --depth 1 --branch v1_5_0 https://github.com/eclipse/sumo.git sumo
ENV SUMO_HOME /usr/src/sumo

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT python ./randomActivityGen.py
