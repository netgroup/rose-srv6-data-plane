source /root/venv/bin/activate
#export PYTHONPATH=/root/lmg/grpc-services/protos/gen-py:/opt/xdp_experiments/srv6-pfplm
export PYTHONPATH=/opt/lmg/grpc-services/protos/gen-py:/opt/srv6-pm-xdp-ebpf/srv6-pfplm
cd /opt/lmg
python ./twamp/twamp_demon.py :: 50052 d
