FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

RUN pip install --no-cache-dir \
    impedance==1.7.1 \
    numpy==1.26.4 \
    scipy==1.12.0 \
    pandas==2.2.3 \
    matplotlib==3.8.4 \
    altair==5.5.0 \
    pillow==10.4.0

COPY data/ /app/data/
RUN mkdir -p /app/output

CMD ["bash"]
