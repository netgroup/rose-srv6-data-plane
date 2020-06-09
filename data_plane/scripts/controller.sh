source /root/venv/bin/activate
export PYTHONPATH=/opt/lmg/grpc-services/protos/gen-py
cd /opt/lmg
python ./srv6_controller/test_srv6_controller.py
