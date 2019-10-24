# Use an official Python runtime as a parent image
FROM continuumio/miniconda3

RUN apt-get update
RUN apt-get install -y build-essential 

RUN mkdir /tmp/ndexgenehancerloader
COPY ./ /tmp/ndexgenehancerloader/
RUN pip install /tmp/ndexgenehancerloader

RUN rm -rf /tmp/ndexgenehancerloader

RUN mkdir /ndexgenehancerloader
WORKDIR /ndexgenehancerloader

CMD /bin/echo "To use run: ndexloadgenehancer.py"
