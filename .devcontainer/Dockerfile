FROM continuumio/miniconda3:24.9.2-0

USER root

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000
ENV USERNAME=${USERNAME}
ENV USER_UID=${USER_UID}
ENV USER_GID=${USER_GID}

RUN apt-get update -q \
    && apt-get install -q -y --no-install-recommends \
        build-essential \
        ripgrep \
        pandoc \
        adduser \
        git \
        grep \
        curl \
        wget \
        vim

RUN conda install -y python=3.9 \
    && pip install --no-cache-dir pipx \
    && pipx reinstall-all
    
RUN conda install -c conda-forge gh jupyterlab

COPY requirements.txt /requirements.txt

RUN python3 -m pip install -r requirements.txt

RUN python3 -m pip install --upgrade flake8-pytest-importorskip click==8.0.4 black==24.4.2 flake8==4.0.1 mypy==1.13.0

RUN groupadd -g ${USER_GID} ${USERNAME} && \
    adduser --disabled-password --uid ${USER_UID} --gid ${USER_GID} --gecos "" ${USERNAME} && \
    echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers
    
USER $USERNAME
 