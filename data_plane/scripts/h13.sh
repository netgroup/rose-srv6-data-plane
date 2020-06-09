source /root/venv/bin/activate

cd /opt/lmg/traffic-generator
python tg.py -6 -B fd00:0:13::2 -M 1000 -c fd00:0:83::2 -b 10M -t 3000 --measure-id 10 --generator-id 200
