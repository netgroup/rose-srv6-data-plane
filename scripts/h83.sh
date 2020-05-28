source /root/venv/bin/activate

cd /opt/lmg/traffic-generator
python tg.py -s -B fd00:0:83::2 --measure-id 10 --generator-id 200
