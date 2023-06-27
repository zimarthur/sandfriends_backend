# syntax=docker/dockerfile:1

#Buildar o container (sem rodar)
#docker build -t sandfriends_flask:latest .

#Manter na versão 3.8
#Tentei na 3.11, mas da problema com uma dependência no python
FROM python:3.8-slim-buster

WORKDIR /sandfriends

RUN pip3 install --upgrade pip

RUN apt-get update
#Precisa destes programas para a dependência do mysql do python
RUN apt-get install gcc curl wget gnupg tzdata -y

#Seta o fuso horário para Brasília
#ARG TZ
ENV TZ=America/Sao_Paulo

#Adiciona a chave do link abaixo
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 467B942D3A79BD29

#Adiciona uma dependência do mysql do python - libmysqlclient-dev, que não está disponível na versão slim da imagem do python
#https://github.com/PyMySQL/mysqlclient/issues/442
RUN apt-get update \
    && apt-get -y install lsb-release \
    && curl -sLo mysql.deb https://dev.mysql.com/get/mysql-apt-config_0.8.19-1_all.deb \
    && DEBIAN_FRONTEND=noninteractive dpkg -i mysql.deb \
    && rm mysql.deb \
    && apt-get update --allow-unauthenticated\
    && apt-get -y install libmysqlclient-dev

#Instala os requirements do Python
COPY ./requirements.txt requirements.txt
RUN pip3 --no-cache-dir install -r requirements.txt

#Copia todos os arquivos da pasta do backend
COPY ./config.json /etc/config.json
COPY ./ ./sandfriends_backend

#Variáveis do flask para poder rodar o app
#Na linha de comando: export FLASK_APP=sandfriends_backend
ENV FLASK_APP=sandfriends_backend
ENV FLASK_ENV=development

#Porta que ficará exposta para o mundo externo
EXPOSE 8000

#Comando que será rodado ao inicializar o container
#Para o servidor do Flask - debug
#CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]

#Para o servidor do Gunicorn - produção
CMD [ "gunicorn", "-w", "3", "sandfriends_backend:create_app()", "--bind", "0.0.0.0:8000"]